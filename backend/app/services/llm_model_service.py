from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import encrypt_model_credential
from app.models.llm_model import LLMDifyConfig, LLMModel, LLMOpenAIConfig
from app.schemas.llm_model import (
    LLMDifyOut,
    LLMDifyPayload,
    LLMModelOut,
    LLMModelPayload,
    LLMOpenAIOut,
    LLMOpenAIPayload,
)
from app.services.model_admin_common import (
    apply_common,
    commit_model,
    common_out,
    list_models as list_common_models,
    masked_credential,
)
from app.services.llm_upstream import UpstreamLLMError
from app.services.llm_dify import DifyLLMClient, DifyLLMError


async def list_models(
    db: AsyncSession,
    page: int,
    page_size: int,
    keyword: str | None,
    provider: str | None,
    enabled: bool | None,
):
    return await list_common_models(
        db, LLMModel, page, page_size, keyword, provider, enabled
    )


async def get_model(db: AsyncSession, model_id: int) -> LLMModel:
    model = await db.scalar(
        select(LLMModel)
        .options(
            selectinload(LLMModel.openai_config),
            selectinload(LLMModel.dify_config),
            selectinload(LLMModel.xiaozhi_services),
        )
        .where(LLMModel.id == model_id, LLMModel.archived_at.is_(None))
    )
    if not model:
        raise AppError("LLM_MODEL_NOT_FOUND", "大语言模型不存在", 404)
    return model


def model_out(model: LLMModel, settings: Settings) -> LLMModelOut:
    values = common_out(model)
    if model.provider == "openai":
        config = model.openai_config
        encrypted = config.api_key_encrypted if config else None
        return LLMOpenAIOut(
            **values,
            provider="openai",
            base_url=config.base_url if config else None,
            upstream_model=config.upstream_model if config else None,
            api_key_masked=masked_credential(encrypted, settings),
            credential_configured=bool(encrypted),
            timeout_seconds=config.timeout_seconds if config else 30.0,
        )
    config = model.dify_config
    encrypted = config.api_key_encrypted if config else None
    return LLMDifyOut(
        **values,
        provider="dify",
        base_url=config.base_url if config else None,
        mode=config.mode if config else None,
        api_key_masked=masked_credential(encrypted, settings),
        credential_configured=bool(encrypted),
        timeout_seconds=config.timeout_seconds if config else 30.0,
    )


def _openai_config(
    payload: LLMOpenAIPayload,
    settings: Settings,
    existing_secret: str | None = None,
) -> LLMOpenAIConfig:
    return LLMOpenAIConfig(
        base_url=payload.base_url,
        upstream_model=payload.upstream_model,
        api_key_encrypted=(
            encrypt_model_credential(payload.api_key, settings)
            if payload.api_key
            else existing_secret
        ),
        timeout_seconds=payload.timeout_seconds,
    )


def _dify_config(
    payload: LLMDifyPayload,
    settings: Settings,
    existing_secret: str | None = None,
) -> LLMDifyConfig:
    return LLMDifyConfig(
        base_url=payload.base_url,
        mode=payload.mode,
        api_key_encrypted=(
            encrypt_model_credential(payload.api_key, settings)
            if payload.api_key
            else existing_secret
        ),
        timeout_seconds=payload.timeout_seconds,
    )


async def create_model(
    db: AsyncSession, payload: LLMModelPayload, settings: Settings
) -> LLMModel:
    model = LLMModel()
    apply_common(model, payload)
    if isinstance(payload, LLMOpenAIPayload):
        model.openai_config = _openai_config(payload, settings)
    else:
        model.dify_config = _dify_config(payload, settings)
    db.add(model)
    await commit_model(db, "大语言模型编码已存在")
    return await get_model(db, model.id)


async def update_model(
    db: AsyncSession,
    model_id: int,
    payload: LLMModelPayload,
    settings: Settings,
) -> LLMModel:
    model = await get_model(db, model_id)
    same_provider = model.provider == payload.provider
    if isinstance(payload, LLMOpenAIPayload):
        existing = (
            model.openai_config.api_key_encrypted
            if same_provider and model.openai_config
            else None
        )
        if model.dify_config:
            await db.delete(model.dify_config)
            model.dify_config = None
            await db.flush()
        if model.openai_config:
            config = model.openai_config
            replacement = _openai_config(payload, settings, existing)
            config.base_url = replacement.base_url
            config.upstream_model = replacement.upstream_model
            config.api_key_encrypted = replacement.api_key_encrypted
            config.timeout_seconds = replacement.timeout_seconds
        else:
            model.openai_config = _openai_config(payload, settings, existing)
    else:
        existing = (
            model.dify_config.api_key_encrypted
            if same_provider and model.dify_config
            else None
        )
        if model.openai_config:
            await db.delete(model.openai_config)
            model.openai_config = None
            await db.flush()
        if model.dify_config:
            config = model.dify_config
            replacement = _dify_config(payload, settings, existing)
            config.base_url = replacement.base_url
            config.mode = replacement.mode
            config.api_key_encrypted = replacement.api_key_encrypted
            config.timeout_seconds = replacement.timeout_seconds
        else:
            model.dify_config = _dify_config(payload, settings, existing)
    apply_common(model, payload)
    await commit_model(db, "大语言模型编码已存在")
    return await get_model(db, model_id)


async def set_enabled(
    db: AsyncSession, model_id: int, enabled: bool
) -> tuple[LLMModel, int]:
    model = await get_model(db, model_id)
    affected = len(model.xiaozhi_services)
    model.enabled = enabled
    await db.commit()
    return model, affected


async def archive_model(db: AsyncSession, model_id: int) -> None:
    model = await get_model(db, model_id)
    if model.xiaozhi_services:
        raise AppError(
            "LLM_MODEL_IN_USE", "大语言模型已被小智中间件服务绑定，不能归档", 409
        )
    model.enabled = False
    model.archived_at = datetime.now(timezone.utc)
    await db.commit()


async def test_connection(db: AsyncSession, model_id: int, settings: Settings) -> None:
    """发送最小请求验证配置、密钥和供应器连通性。"""
    model = await get_model(db, model_id)
    if not model.enabled:
        raise AppError("LLM_MODEL_DISABLED", "模型已停用，无法测试连接", 409)
    from app.services.llm_proxy_service import service_llm_client

    # 复用代理中的统一客户端构造逻辑，避免两套密钥解密和 URL 拼接规则。
    class _Service:
        llm_model_config = model

    try:
        client = service_llm_client(_Service(), settings)
        if isinstance(client, DifyLLMClient):
            await client.complete("请仅回复：连接成功", "connection-test")
        else:
            await client.complete({"messages": [{"role": "user", "content": "请仅回复：连接成功"}], "max_tokens": 8, "temperature": 0})
    except (UpstreamLLMError, DifyLLMError) as exc:
        raise AppError("LLM_CONNECTION_FAILED", "模型连接失败，请检查基础 URL、模型名称和 API Key", 502) from exc
