from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import NOT_FOUND_ERROR, PUBLIC_RESPONSES, PUBLIC_TAG
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.xiaozhi_service import (
    PublicXiaozhiServiceConfig,
    PublicXiaozhiServiceNameList,
    XIAOZHI_SERVICE_ASSET_SLOTS,
)
from app.services import xiaozhi_service
from app.services.object_storage import (
    ObjectStorageError,
    get_object_storage,
)


router = APIRouter(prefix="/api", tags=[PUBLIC_TAG], responses=PUBLIC_RESPONSES)


def storage_from_settings(settings: Settings):
    return get_object_storage(
        settings.app_env,
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_bucket,
        settings.minio_secure,
    )


@router.get(
    "/xiaozhi-services",
    summary="获取已发布小智中间件服务名称",
    response_model=PublicXiaozhiServiceNameList,
    response_description="已发布服务名称列表",
)
async def list_xiaozhi_service_names(
    db: AsyncSession = Depends(get_db),
):
    """返回前端可选择的已发布服务名称，不暴露内部服务编码。"""

    return PublicXiaozhiServiceNameList(
        serviceNames=await xiaozhi_service.list_published_service_names(db)
    )


def _public_config(request: Request, service) -> PublicXiaozhiServiceConfig:
    assets = service.asset_map()
    urls: dict[str, str | None] = {}
    for slot in XIAOZHI_SERVICE_ASSET_SLOTS:
        asset = assets.get(slot)
        if not asset:
            urls[slot] = None
            continue
        urls[slot] = str(
            request.url_for("get_xiaozhi_service_asset", asset_id=asset.id)
        )
        urls[slot] += "?" + urlencode({"v": asset.etag})
    mapping = service.device_mapping
    if not mapping:
        raise AppError("XIAOZHI_SERVICE_NOT_FOUND", "小智中间件服务不存在或未发布", 404)
    return PublicXiaozhiServiceConfig(
        service_name=service.service_name,
        digital_human_name=service.digital_human_name,
        title=service.title,
        subtitle=service.subtitle,
        questions=service.questions,
        background_icon_url=urls["background_icon"],
        wake_icon_url=urls["wake_icon"],
        menu_background_url=urls["menu_background"],
        keyboard_icon_url=urls["keyboard_icon"],
        voice_icon_url=urls["voice_icon"],
        home_icon_url=urls["home_icon"],
        hold_to_talk_background_url=urls["hold_to_talk_background"],
        send_icon_url=urls["send_icon"],
        standing_video_url=urls["standing_video"],
        thinking_video_url=urls["thinking_video"],
        speaking_video_url=urls["speaking_video"],
        voice_wakeup_enabled=service.voice_wakeup_enabled,
        wake_word=service.wake_word,
        wake_listening_texts=service.wake_listening_texts,
        wake_requirement_count=service.wake_requirement_count,
        agent_id=mapping.agent_id,
        agent_name=mapping.name,
    )


@router.get(
    "/xiaozhi-services/config",
    summary="按服务名称读取小智中间件服务配置",
    response_model=PublicXiaozhiServiceConfig,
    response_description="前端数字人完整配置（不包含内部服务编码）",
    responses={404: NOT_FOUND_ERROR, 409: {"description": "服务名称不唯一"}},
)
async def get_xiaozhi_service_config(
    request: Request,
    service_name: str = Query(
        alias="serviceName", min_length=1, max_length=128, description="前端服务名称"
    ),
    db: AsyncSession = Depends(get_db),
):
    """按服务名称读取已发布配置；草稿或停止发布的服务不会公开。"""

    service = await xiaozhi_service.get_published_service_by_name(db, service_name)
    return _public_config(request, service)


@router.get(
    "/xiaozhi-service-assets/{asset_id}",
    name="get_xiaozhi_service_asset",
    summary="读取小智中间件服务媒体",
    response_class=Response,
    response_description="图片或视频二进制内容",
    responses={
        200: {"description": "图片或视频二进制内容"},
        404: NOT_FOUND_ERROR,
        503: {"description": "媒体存储暂时不可用"},
    },
)
async def get_xiaozhi_service_asset(
    asset_id: int = Path(description="媒体资产编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """通过中间件读取私有 MinIO 图片或视频，并返回 ETag 和长期缓存头。"""

    asset = await db.get(XiaozhiServiceAsset, asset_id)
    if not asset:
        raise AppError("XIAOZHI_SERVICE_ASSET_NOT_FOUND", "媒体资产不存在", 404)
    storage = storage_from_settings(settings)
    try:
        data, content_type, etag = await storage.get(asset.object_key)
    except ObjectStorageError as exc:
        raise AppError("OBJECT_STORAGE_UNAVAILABLE", "媒体存储暂时不可用", 503) from exc
    return Response(
        data,
        media_type=content_type,
        headers={
            "ETag": f'"{etag or asset.etag}"',
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )


from app.models.xiaozhi_service_asset import XiaozhiServiceAsset  # noqa: E402  # isort:skip
