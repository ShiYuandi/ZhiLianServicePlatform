from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    generate_service_api_key,
    hash_service_api_key,
    service_api_key_hint,
)
from app.models.frontend_ai_service import (
    FrontendAIService,
    FrontendAIServiceImageBinding,
    FrontendAIServiceSpeechBinding,
)
from app.models.image_model import ImageGenerationModel
from app.models.speech_model import SpeechRecognitionModel
from app.schemas.frontend_ai_service import (
    FrontendAIServiceCreate,
    FrontendAIServiceUpdate,
)
from app.services import image_model_service, speech_model_service


def _load_options():
    speech = selectinload(FrontendAIService.speech_binding).selectinload(
        FrontendAIServiceSpeechBinding.model
    )
    image = selectinload(FrontendAIService.image_binding).selectinload(
        FrontendAIServiceImageBinding.model
    )
    return (
        speech.selectinload(SpeechRecognitionModel.baidu_config),
        speech.selectinload(SpeechRecognitionModel.volcengine_config),
        image.selectinload(ImageGenerationModel.volcengine_config),
    )


async def get_service(db: AsyncSession, service_id: int) -> FrontendAIService:
    service = await db.scalar(
        select(FrontendAIService)
        .options(*_load_options())
        .where(
            FrontendAIService.id == service_id,
            FrontendAIService.archived_at.is_(None),
        )
    )
    if not service:
        raise AppError("FRONTEND_AI_SERVICE_NOT_FOUND", "前端 AI 服务不存在", 404)
    return service


async def list_services(
    db: AsyncSession,
    page: int,
    page_size: int,
    keyword: str | None,
    enabled: bool | None,
) -> tuple[list[FrontendAIService], int]:
    filters = [FrontendAIService.archived_at.is_(None)]
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        filters.append(
            or_(
                FrontendAIService.service_name.like(term),
                FrontendAIService.service_code.like(term),
            )
        )
    if enabled is not None:
        filters.append(FrontendAIService.enabled == enabled)
    total = int(
        await db.scalar(select(func.count(FrontendAIService.id)).where(*filters)) or 0
    )
    statement = (
        select(FrontendAIService)
        .options(*_load_options())
        .where(*filters)
        .order_by(FrontendAIService.updated_at.desc(), FrontendAIService.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list((await db.scalars(statement)).all()), total


def speech_model_configured(model: SpeechRecognitionModel) -> bool:
    if model.provider == "baidu":
        config = model.baidu_config
        return bool(config and config.api_key_encrypted and config.secret_key_encrypted)
    config = model.volcengine_config
    return bool(config and config.access_token_encrypted)


def image_model_configured(model: ImageGenerationModel) -> bool:
    config = model.volcengine_config
    return bool(config and config.api_key_encrypted)


def validate_enabled(service: FrontendAIService) -> None:
    if not service.enabled:
        return
    if service.speech_binding:
        model = service.speech_binding.model
        if not model.enabled:
            raise AppError(
                "SPEECH_MODEL_DISABLED", "绑定的语音识别模型已停用，不能启用服务", 409
            )
        if not speech_model_configured(model):
            raise AppError(
                "SPEECH_MODEL_NOT_CONFIGURED",
                "绑定的语音识别模型凭据未完整配置，不能启用服务",
                409,
            )
    if service.image_binding:
        model = service.image_binding.model
        if not model.enabled:
            raise AppError(
                "IMAGE_MODEL_DISABLED", "绑定的图像生成模型已停用，不能启用服务", 409
            )
        if not image_model_configured(model):
            raise AppError(
                "IMAGE_MODEL_NOT_CONFIGURED",
                "绑定的图像生成模型凭据未完整配置，不能启用服务",
                409,
            )


def _apply_fields(
    service: FrontendAIService,
    payload: FrontendAIServiceCreate | FrontendAIServiceUpdate,
) -> None:
    service.service_name = payload.service_name
    service.enabled = payload.enabled
    service.remark = payload.remark
    service.rate_limit_per_minute = payload.rate_limit_per_minute
    service.max_inflight_tasks = payload.max_inflight_tasks
    service.allowed_origins = payload.allowed_origins


async def _apply_bindings(
    db: AsyncSession,
    service: FrontendAIService,
    speech_model_id: int | None,
    image_model_id: int | None,
) -> None:
    if speech_model_id is None:
        service.speech_binding = None
    else:
        speech_model = await speech_model_service.get_model(db, speech_model_id)
        if service.speech_binding:
            service.speech_binding.model = speech_model
        else:
            service.speech_binding = FrontendAIServiceSpeechBinding(model=speech_model)

    if image_model_id is None:
        service.image_binding = None
    else:
        image_model = await image_model_service.get_model(db, image_model_id)
        if service.image_binding:
            service.image_binding.model = image_model
        else:
            service.image_binding = FrontendAIServiceImageBinding(model=image_model)


async def _commit(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(
            "FRONTEND_AI_SERVICE_CODE_EXISTS", "前端 AI 服务编码已存在", 409
        ) from exc


async def create_service(
    db: AsyncSession, payload: FrontendAIServiceCreate, settings: Settings
) -> tuple[FrontendAIService, str]:
    api_key = generate_service_api_key()
    hint = service_api_key_hint(api_key)
    service = FrontendAIService(
        service_code=f"svc-{uuid.uuid4().hex}",
        api_key_hash=hash_service_api_key(api_key, settings),
        api_key_prefix=hint[:8],
        api_key_suffix=hint[-4:],
        api_key_version=1,
    )
    _apply_fields(service, payload)
    db.add(service)
    await _apply_bindings(db, service, payload.speech_model_id, payload.image_model_id)
    validate_enabled(service)
    await _commit(db)
    return await get_service(db, service.id), api_key


async def update_service(
    db: AsyncSession, service_id: int, payload: FrontendAIServiceUpdate
) -> FrontendAIService:
    service = await get_service(db, service_id)
    _apply_fields(service, payload)
    await _apply_bindings(db, service, payload.speech_model_id, payload.image_model_id)
    validate_enabled(service)
    await _commit(db)
    return await get_service(db, service_id)


async def rotate_api_key(
    db: AsyncSession, service_id: int, settings: Settings
) -> tuple[str, str, int]:
    service = await get_service(db, service_id)
    api_key = generate_service_api_key()
    hint = service_api_key_hint(api_key)
    service.api_key_hash = hash_service_api_key(api_key, settings)
    service.api_key_prefix = hint[:8]
    service.api_key_suffix = hint[-4:]
    service.api_key_version += 1
    await db.commit()
    return api_key, hint, service.api_key_version


async def archive_service(db: AsyncSession, service_id: int) -> None:
    service = await get_service(db, service_id)
    service.enabled = False
    service.speech_binding = None
    service.image_binding = None
    service.archived_at = datetime.now(timezone.utc)
    await db.commit()


def api_key_hint(service: FrontendAIService) -> str:
    return f"{service.api_key_prefix}…{service.api_key_suffix}"
