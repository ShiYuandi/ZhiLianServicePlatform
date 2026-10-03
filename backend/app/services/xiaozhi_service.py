from __future__ import annotations

import uuid
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import decrypt_model_credential
from app.models.device_mapping import DeviceMapping
from app.models.llm_model import LLMModel
from app.models.qa import QaTable
from app.models.xiaozhi_service import XiaozhiMiddlewareService
from app.models.xiaozhi_service_asset import XiaozhiServiceAsset
from app.schemas.xiaozhi_service import XiaozhiServiceCreate, XiaozhiServiceUpdate
from app.services.object_storage import ObjectStorage, ObjectStorageError


def service_query():
    return select(XiaozhiMiddlewareService).options(
        selectinload(XiaozhiMiddlewareService.device_mapping),
        selectinload(XiaozhiMiddlewareService.assets),
        selectinload(XiaozhiMiddlewareService.qa_table),
        selectinload(XiaozhiMiddlewareService.llm_model_config).selectinload(
            LLMModel.openai_config
        ),
        selectinload(XiaozhiMiddlewareService.llm_model_config).selectinload(
            LLMModel.dify_config
        ),
    )


def llm_configured(service: XiaozhiMiddlewareService) -> bool:
    model = service.llm_model_config
    if not model or model.archived_at is not None:
        return False
    if model.provider == "openai":
        config = model.openai_config
        return bool(
            config
            and config.base_url
            and config.upstream_model
            and config.api_key_encrypted
        )
    if model.provider == "dify":
        config = model.dify_config
        return bool(
            config
            and config.base_url
            and config.mode in {"chat-messages", "workflows/run"}
            and config.api_key_encrypted
        )
    return False


def completeness(service: XiaozhiMiddlewareService) -> int:
    checks: list[bool] = [
        bool(service.service_name.strip()),
        bool(service.title.strip()),
        service.device_mapping is not None,
        bool(service.device_mapping and service.device_mapping.name.strip()),
        bool(service.device_mapping and service.device_mapping.agent_id),
    ]
    if service.ai_reply_enabled:
        checks.extend(
            [
                bool(service.llm_model_config and service.llm_model_config.enabled),
                llm_configured(service),
            ]
        )
    else:
        checks.append(bool(service.default_reply_text and service.default_reply_text.strip()))
    if service.voice_wakeup_enabled:
        checks.extend(
            [
                bool(service.wake_word and service.wake_word.strip()),
                bool(service.wake_listening_texts),
            ]
        )
    return round(sum(checks) * 100 / len(checks))


def validate_publishable(service: XiaozhiMiddlewareService, settings: Settings) -> None:
    missing: list[str] = []
    if not service.service_name.strip():
        missing.append("服务名称")
    if not service.title.strip():
        missing.append("标题")
    mapping = service.device_mapping
    if not mapping:
        missing.append("设备映射")
    else:
        if not mapping.name.strip():
            missing.append("设备名称")
        if not mapping.agent_id:
            missing.append("agentId")
        if not mapping.enabled:
            missing.append("启用设备映射")
    if not service.ai_reply_enabled:
        if not (service.default_reply_text and service.default_reply_text.strip()):
            missing.append("默认回复词")
    model = service.llm_model_config
    if service.ai_reply_enabled:
        if not model:
            missing.append("大语言模型")
        elif model.archived_at is not None:
            missing.append("未归档的大语言模型")
        elif not model.enabled:
            missing.append("已启用的大语言模型")
        elif not llm_configured(service):
            missing.append("完整的大语言模型调用配置")
        else:
            config = (
                model.openai_config if model.provider == "openai" else model.dify_config
            )
            decrypt_model_credential(config.api_key_encrypted, settings)
    if service.voice_wakeup_enabled:
        if not service.wake_word:
            missing.append("唤醒词")
        if not service.wake_listening_texts:
            missing.append("唤醒词监听文字")
    if missing:
        raise AppError(
            "XIAOZHI_SERVICE_INCOMPLETE",
            "小智中间件服务配置不完整：" + "、".join(missing),
            409,
        )


async def validate_bindings(
    db: AsyncSession, qa_table_id: int | None, llm_model_id: int | None
) -> None:
    if qa_table_id is not None and not await db.get(QaTable, qa_table_id):
        raise AppError("QA_TABLE_NOT_FOUND", "绑定的问答表不存在", 404)
    if llm_model_id is not None:
        model = await db.get(LLMModel, llm_model_id)
        if not model or model.archived_at is not None:
            raise AppError("LLM_MODEL_NOT_FOUND", "绑定的大语言模型不存在", 404)


def apply_service_values(
    service: XiaozhiMiddlewareService,
    payload: XiaozhiServiceCreate | XiaozhiServiceUpdate,
) -> None:
    service.service_name = payload.service_name
    service.digital_human_name = payload.digital_human_name
    service.title = payload.title
    service.subtitle = payload.subtitle
    service.questions = payload.questions
    service.voice_wakeup_enabled = payload.voice_wakeup_enabled
    service.wake_word = payload.wake_word
    service.wake_listening_texts = payload.wake_listening_texts
    service.wake_requirement_count = payload.wake_requirement_count
    service.qa_table_id = payload.qa_table_id
    service.ai_reply_enabled = payload.ai_reply_enabled
    service.default_reply_text = payload.default_reply_text
    service.llm_model_id = payload.llm_model_id


def apply_mapping_values(
    mapping: DeviceMapping,
    payload: XiaozhiServiceCreate | XiaozhiServiceUpdate,
) -> None:
    mapping.name = payload.device_name
    mapping.agent_id = payload.agent_id
    mapping.enabled = payload.device_enabled


async def get_service(db: AsyncSession, service_id: int) -> XiaozhiMiddlewareService:
    service = await db.scalar(
        service_query().where(XiaozhiMiddlewareService.id == service_id)
    )
    if not service:
        raise AppError("XIAOZHI_SERVICE_NOT_FOUND", "小智中间件服务不存在", 404)
    return service


async def get_published_service(
    db: AsyncSession, service_code: str
) -> XiaozhiMiddlewareService:
    service = await db.scalar(
        service_query().where(
            XiaozhiMiddlewareService.service_code == service_code,
            XiaozhiMiddlewareService.published.is_(True),
        )
    )
    if not service:
        raise AppError(
            "XIAOZHI_SERVICE_NOT_FOUND",
            "小智中间件服务不存在或未发布",
            404,
        )
    return service


async def get_published_service_by_name(
    db: AsyncSession, service_name: str
) -> XiaozhiMiddlewareService:
    """按前端显示名称读取已发布服务；名称匹配忽略首尾空格和大小写。"""

    normalized = service_name.strip().casefold()
    if not normalized:
        raise AppError("XIAOZHI_SERVICE_NOT_FOUND", "小智中间件服务不存在或未发布", 404)
    result = await db.scalars(
        service_query().where(
            XiaozhiMiddlewareService.published.is_(True),
            func.lower(XiaozhiMiddlewareService.service_name) == normalized,
        )
    )
    services = list(result.all())
    if not services:
        raise AppError("XIAOZHI_SERVICE_NOT_FOUND", "小智中间件服务不存在或未发布", 404)
    if len(services) > 1:
        raise AppError(
            "XIAOZHI_SERVICE_NAME_AMBIGUOUS",
            "服务名称对应多个已发布服务，请联系管理员处理",
            409,
        )
    return services[0]


async def list_published_service_names(db: AsyncSession) -> list[str]:
    """返回已发布服务名称，并按忽略大小写规则去重。"""

    result = await db.scalars(
        select(XiaozhiMiddlewareService.service_name)
        .where(XiaozhiMiddlewareService.published.is_(True))
        .order_by(XiaozhiMiddlewareService.service_name.asc())
    )
    names: list[str] = []
    seen: set[str] = set()
    for name in result.all():
        key = name.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            names.append(name)
    return names


async def list_services(
    db: AsyncSession,
    page: int,
    page_size: int,
    keyword: str | None = None,
    published: bool | None = None,
) -> tuple[list[XiaozhiMiddlewareService], int]:
    filters = []
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        filters.append(
            (XiaozhiMiddlewareService.service_name.like(term))
            | (XiaozhiMiddlewareService.service_code.like(term))
        )
    if published is not None:
        filters.append(XiaozhiMiddlewareService.published.is_(published))
    total = int(
        await db.scalar(select(func.count(XiaozhiMiddlewareService.id)).where(*filters))
        or 0
    )
    result = await db.scalars(
        service_query()
        .where(*filters)
        .order_by(
            XiaozhiMiddlewareService.updated_at.desc(),
            XiaozhiMiddlewareService.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.all()), total


async def create_service(
    db: AsyncSession, payload: XiaozhiServiceCreate
) -> XiaozhiMiddlewareService:
    await validate_bindings(db, payload.qa_table_id, payload.llm_model_id)
    service = XiaozhiMiddlewareService(
        service_code=payload.service_code or f"svc-{uuid.uuid4().hex}",
        published=False,
    )
    apply_service_values(service, payload)
    service.device_mapping = DeviceMapping()
    apply_mapping_values(service.device_mapping, payload)
    db.add(service)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(
            "XIAOZHI_SERVICE_CONFLICT", "服务编码或设备名称已存在", 409
        ) from exc
    return await get_service(db, service.id)


async def update_service(
    db: AsyncSession, service_id: int, payload: XiaozhiServiceUpdate
) -> XiaozhiMiddlewareService:
    service = await get_service(db, service_id)
    if service.published:
        raise AppError("XIAOZHI_SERVICE_PUBLISHED", "已发布服务请先停止发布再修改", 409)
    await validate_bindings(db, payload.qa_table_id, payload.llm_model_id)
    apply_service_values(service, payload)
    if not service.device_mapping:
        service.device_mapping = DeviceMapping()
    apply_mapping_values(service.device_mapping, payload)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(
            "XIAOZHI_SERVICE_CONFLICT", "设备名称已被其他服务使用", 409
        ) from exc
    return await get_service(db, service.id)


async def delete_service(
    db: AsyncSession, service_id: int, storage: ObjectStorage
) -> None:
    service = await get_service(db, service_id)
    if service.published:
        raise AppError("XIAOZHI_SERVICE_PUBLISHED", "已发布服务请先停止发布再删除", 409)
    object_keys = [asset.object_key for asset in service.assets]
    await db.delete(service)
    await db.commit()
    for object_key in object_keys:
        try:
            await storage.delete(object_key)
        except ObjectStorageError:
            continue


async def publish_service(
    db: AsyncSession, service_id: int, settings: Settings
) -> XiaozhiMiddlewareService:
    service = await get_service(db, service_id)
    validate_publishable(service, settings)
    service.published = True
    await db.commit()
    return await get_service(db, service.id)


async def unpublish_service(
    db: AsyncSession, service_id: int
) -> XiaozhiMiddlewareService:
    service = await get_service(db, service_id)
    service.published = False
    await db.commit()
    return await get_service(db, service.id)


async def upsert_asset(
    db: AsyncSession,
    service_id: int,
    slot: str,
    object_key: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    etag: str,
) -> tuple[XiaozhiServiceAsset, str | None]:
    service = await get_service(db, service_id)
    if service.published:
        raise AppError(
            "XIAOZHI_SERVICE_PUBLISHED",
            "已发布服务请先停止发布再上传媒体",
            409,
        )
    old = next((asset for asset in service.assets if asset.slot == slot), None)
    old_key = old.object_key if old else None
    if old:
        old.object_key = object_key
        old.original_filename = original_filename
        old.content_type = content_type
        old.size_bytes = size_bytes
        old.etag = etag
        asset = old
    else:
        asset = XiaozhiServiceAsset(
            service_id=service_id,
            slot=slot,
            object_key=object_key,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            etag=etag,
        )
        db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset, old_key


async def delete_asset(
    db: AsyncSession, service_id: int, slot: str, storage: ObjectStorage
) -> None:
    service = await get_service(db, service_id)
    if service.published:
        raise AppError(
            "XIAOZHI_SERVICE_PUBLISHED",
            "已发布服务请先停止发布再删除媒体",
            409,
        )
    asset = next((item for item in service.assets if item.slot == slot), None)
    if not asset:
        raise AppError("XIAOZHI_SERVICE_ASSET_NOT_FOUND", "媒体资产不存在", 404)
    object_key = asset.object_key
    await db.delete(asset)
    await db.commit()
    try:
        await storage.delete(object_key)
    except ObjectStorageError:
        pass
