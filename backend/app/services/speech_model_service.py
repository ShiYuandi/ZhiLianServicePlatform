from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import encrypt_model_credential
from app.models.speech_model import (
    BaiduASRConfig,
    SpeechRecognitionModel,
    VolcengineASRConfig,
)
from app.schemas.speech_model import (
    SpeechBaiduOut,
    SpeechBaiduPayload,
    SpeechModelOut,
    SpeechModelPayload,
    SpeechVolcengineOut,
)
from app.services.model_admin_common import (
    apply_common,
    commit_model,
    common_out,
    list_models as list_common_models,
    masked_credential,
)


async def list_models(db, page, page_size, keyword, provider, enabled):
    return await list_common_models(
        db, SpeechRecognitionModel, page, page_size, keyword, provider, enabled
    )


async def get_model(db: AsyncSession, model_id: int) -> SpeechRecognitionModel:
    model = await db.scalar(
        select(SpeechRecognitionModel)
        .options(
            selectinload(SpeechRecognitionModel.baidu_config),
            selectinload(SpeechRecognitionModel.volcengine_config),
            selectinload(SpeechRecognitionModel.frontend_service_bindings),
        )
        .where(
            SpeechRecognitionModel.id == model_id,
            SpeechRecognitionModel.archived_at.is_(None),
        )
    )
    if not model:
        raise AppError("SPEECH_MODEL_NOT_FOUND", "语音识别模型不存在", 404)
    return model


def model_out(model: SpeechRecognitionModel, settings: Settings) -> SpeechModelOut:
    values = common_out(model)
    if model.provider == "baidu":
        config = model.baidu_config
        api_key = config.api_key_encrypted if config else None
        secret_key = config.secret_key_encrypted if config else None
        return SpeechBaiduOut(
            **values,
            provider="baidu",
            app_id=config.app_id if config else None,
            api_key_masked=masked_credential(api_key, settings),
            secret_key_masked=masked_credential(secret_key, settings),
            credential_configured=bool(api_key and secret_key),
            dev_pid=config.dev_pid if config else 1537,
        )
    config = model.volcengine_config
    token = config.access_token_encrypted if config else None
    return SpeechVolcengineOut(
        **values,
        provider="volcengine",
        app_id=config.app_id if config else None,
        access_token_masked=masked_credential(token, settings),
        credential_configured=bool(token),
        resource_id=config.resource_id if config else None,
        language=config.language if config else None,
        boosting_table_name=config.boosting_table_name if config else None,
        correct_table_name=config.correct_table_name if config else None,
    )


def _baidu_config(payload, settings, api_key=None, secret_key=None):
    return BaiduASRConfig(
        app_id=payload.app_id,
        api_key_encrypted=(
            encrypt_model_credential(payload.api_key, settings)
            if payload.api_key
            else api_key
        ),
        secret_key_encrypted=(
            encrypt_model_credential(payload.secret_key, settings)
            if payload.secret_key
            else secret_key
        ),
        dev_pid=payload.dev_pid,
    )


def _volc_config(payload, settings, access_token=None):
    return VolcengineASRConfig(
        app_id=payload.app_id,
        access_token_encrypted=(
            encrypt_model_credential(payload.access_token, settings)
            if payload.access_token
            else access_token
        ),
        resource_id=payload.resource_id,
        language=payload.language,
        boosting_table_name=payload.boosting_table_name,
        correct_table_name=payload.correct_table_name,
    )


async def create_model(db, payload: SpeechModelPayload, settings):
    model = SpeechRecognitionModel()
    apply_common(model, payload)
    if isinstance(payload, SpeechBaiduPayload):
        model.baidu_config = _baidu_config(payload, settings)
    else:
        model.volcengine_config = _volc_config(payload, settings)
    db.add(model)
    await commit_model(db, "语音识别模型编码已存在")
    return await get_model(db, model.id)


async def update_model(db, model_id, payload: SpeechModelPayload, settings):
    model = await get_model(db, model_id)
    same_provider = model.provider == payload.provider
    if isinstance(payload, SpeechBaiduPayload):
        old_api = (
            model.baidu_config.api_key_encrypted
            if same_provider and model.baidu_config
            else None
        )
        old_secret = (
            model.baidu_config.secret_key_encrypted
            if same_provider and model.baidu_config
            else None
        )
        if model.volcengine_config:
            await db.delete(model.volcengine_config)
            model.volcengine_config = None
            await db.flush()
        replacement = _baidu_config(payload, settings, old_api, old_secret)
        if model.baidu_config:
            for field in (
                "app_id",
                "api_key_encrypted",
                "secret_key_encrypted",
                "dev_pid",
            ):
                setattr(model.baidu_config, field, getattr(replacement, field))
        else:
            model.baidu_config = replacement
    else:
        old_token = (
            model.volcengine_config.access_token_encrypted
            if same_provider and model.volcengine_config
            else None
        )
        if model.baidu_config:
            await db.delete(model.baidu_config)
            model.baidu_config = None
            await db.flush()
        replacement = _volc_config(payload, settings, old_token)
        if model.volcengine_config:
            for field in (
                "app_id",
                "access_token_encrypted",
                "resource_id",
                "language",
                "boosting_table_name",
                "correct_table_name",
            ):
                setattr(model.volcengine_config, field, getattr(replacement, field))
        else:
            model.volcengine_config = replacement
    apply_common(model, payload)
    await commit_model(db, "语音识别模型编码已存在")
    return await get_model(db, model_id)


async def set_enabled(db, model_id, enabled):
    model = await get_model(db, model_id)
    affected = len(model.frontend_service_bindings)
    model.enabled = enabled
    await db.commit()
    return model, affected


async def archive_model(db, model_id):
    model = await get_model(db, model_id)
    if model.frontend_service_bindings:
        raise AppError(
            "SPEECH_MODEL_IN_USE", "语音识别模型已被前端 AI 服务绑定，不能归档", 409
        )
    model.enabled = False
    model.archived_at = datetime.now(timezone.utc)
    await db.commit()
