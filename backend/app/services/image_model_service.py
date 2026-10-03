from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import encrypt_model_credential
from app.models.image_model import ImageGenerationModel, VolcengineImageConfig
from app.schemas.image_model import (
    ImageModelOut,
    ImageVolcengineOut,
    ImageVolcenginePayload,
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
        db, ImageGenerationModel, page, page_size, keyword, provider, enabled
    )


async def get_model(db: AsyncSession, model_id: int) -> ImageGenerationModel:
    model = await db.scalar(
        select(ImageGenerationModel)
        .options(
            selectinload(ImageGenerationModel.volcengine_config),
            selectinload(ImageGenerationModel.frontend_service_bindings),
        )
        .where(
            ImageGenerationModel.id == model_id,
            ImageGenerationModel.archived_at.is_(None),
        )
    )
    if not model:
        raise AppError("IMAGE_MODEL_NOT_FOUND", "图像生成模型不存在", 404)
    return model


def model_out(model: ImageGenerationModel, settings: Settings) -> ImageModelOut:
    config = model.volcengine_config
    encrypted = config.api_key_encrypted if config else None
    return ImageVolcengineOut(
        **common_out(model),
        provider="volcengine",
        api_url=(
            config.api_url
            if config
            else "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        ),
        api_key_masked=masked_credential(encrypted, settings),
        credential_configured=bool(encrypted),
        upstream_model=config.upstream_model if config else None,
        default_width=config.default_width if config else 1024,
        default_height=config.default_height if config else 1024,
        timeout_seconds=config.timeout_seconds if config else 120.0,
        watermark=config.watermark if config else False,
    )


def _config(payload, settings, api_key=None):
    return VolcengineImageConfig(
        api_url=payload.api_url,
        api_key_encrypted=(
            encrypt_model_credential(payload.api_key, settings)
            if payload.api_key
            else api_key
        ),
        upstream_model=payload.upstream_model,
        default_width=payload.default_width,
        default_height=payload.default_height,
        timeout_seconds=payload.timeout_seconds,
        watermark=payload.watermark,
    )


async def create_model(
    db: AsyncSession, payload: ImageVolcenginePayload, settings: Settings
) -> ImageGenerationModel:
    model = ImageGenerationModel()
    apply_common(model, payload)
    model.volcengine_config = _config(payload, settings)
    db.add(model)
    await commit_model(db, "图像生成模型编码已存在")
    return await get_model(db, model.id)


async def update_model(db, model_id, payload, settings):
    model = await get_model(db, model_id)
    old_key = (
        model.volcengine_config.api_key_encrypted if model.volcengine_config else None
    )
    replacement = _config(payload, settings, old_key)
    if model.volcengine_config:
        for field in (
            "api_url",
            "api_key_encrypted",
            "upstream_model",
            "default_width",
            "default_height",
            "timeout_seconds",
            "watermark",
        ):
            setattr(model.volcengine_config, field, getattr(replacement, field))
    else:
        model.volcengine_config = replacement
    apply_common(model, payload)
    await commit_model(db, "图像生成模型编码已存在")
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
            "IMAGE_MODEL_IN_USE", "图像生成模型已被前端 AI 服务绑定，不能归档", 409
        )
    model.enabled = False
    model.archived_at = datetime.now(timezone.utc)
    await db.commit()
