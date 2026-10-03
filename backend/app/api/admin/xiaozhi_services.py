from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    NOT_FOUND_ERROR,
    XIAOZHI_SERVICE_TAG,
)
from app.api.xiaozhi_services import storage_from_settings
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.models.xiaozhi_service import XiaozhiMiddlewareService
from app.schemas.xiaozhi_service import (
    XIAOZHI_SERVICE_ASSET_SLOTS,
    XIAOZHI_SERVICE_VIDEO_SLOTS,
    XiaozhiServiceAssetOut,
    XiaozhiServiceAssetUploadResponse,
    XiaozhiServiceCreate,
    XiaozhiServiceListItem,
    XiaozhiServiceListResponse,
    XiaozhiServiceOut,
    XiaozhiServiceUpdate,
)
from app.services import xiaozhi_service
from app.services.object_storage import ObjectStorageError, create_object_key


router = APIRouter(
    prefix="/api/admin/xiaozhi-services",
    tags=[XIAOZHI_SERVICE_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


def asset_out(asset, request: Request) -> XiaozhiServiceAssetOut:
    url = str(request.url_for("get_xiaozhi_service_asset", asset_id=asset.id))
    return XiaozhiServiceAssetOut(
        id=asset.id,
        slot=asset.slot,
        original_filename=asset.original_filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        etag=asset.etag,
        url=url + "?" + urlencode({"v": asset.etag}),
    )


def service_out(
    service: XiaozhiMiddlewareService, request: Request
) -> XiaozhiServiceOut:
    mapping = service.device_mapping
    if not mapping:
        raise AppError("XIAOZHI_SERVICE_MAPPING_MISSING", "服务缺少设备映射", 500)
    llm = service.llm_model_config
    return XiaozhiServiceOut(
        id=service.id,
        service_code=service.service_code,
        service_name=service.service_name,
        digital_human_name=service.digital_human_name,
        title=service.title,
        subtitle=service.subtitle,
        questions=service.questions,
        voice_wakeup_enabled=service.voice_wakeup_enabled,
        wake_word=service.wake_word,
        wake_listening_texts=service.wake_listening_texts,
        wake_requirement_count=service.wake_requirement_count,
        device_name=mapping.name,
        agent_id=mapping.agent_id,
        device_enabled=mapping.enabled,
        published=service.published,
        completeness=xiaozhi_service.completeness(service),
        assets=[asset_out(asset, request) for asset in service.assets],
        created_at=service.created_at,
        updated_at=service.updated_at,
        qa_table_id=service.qa_table_id,
        qa_table_name=service.qa_table.name if service.qa_table else None,
        ai_reply_enabled=service.ai_reply_enabled,
        default_reply_text=service.default_reply_text,
        llm_model_id=service.llm_model_id,
        llm_model_name=llm.model_name if llm else None,
        llm_provider=llm.provider if llm else None,
        llm_enabled=llm.enabled if llm else None,
        llm_configured=xiaozhi_service.llm_configured(service),
    )


@router.get(
    "",
    summary="分页查询小智中间件服务",
    response_model=XiaozhiServiceListResponse,
    response_description="服务列表和配置完整度",
)
async def list_services(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页最多 100 个服务"),
    keyword: str | None = Query(default=None, description="搜索服务编码或服务名称"),
    published: bool | None = Query(default=None, description="按发布状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """分页查询小智中间件服务，并返回设备、问答表和大模型状态。"""
    items, total = await xiaozhi_service.list_services(
        db, page, page_size, keyword, published
    )
    result = []
    for service in items:
        mapping = service.device_mapping
        if not mapping:
            continue
        llm = service.llm_model_config
        result.append(
            XiaozhiServiceListItem(
                id=service.id,
                service_code=service.service_code,
                service_name=service.service_name,
                digital_human_name=service.digital_human_name,
                device_name=mapping.name,
                agent_id=mapping.agent_id,
                device_enabled=mapping.enabled,
                published=service.published,
                completeness=xiaozhi_service.completeness(service),
                updated_at=service.updated_at,
                qa_table_id=service.qa_table_id,
                qa_table_name=service.qa_table.name if service.qa_table else None,
                ai_reply_enabled=service.ai_reply_enabled,
                default_reply_text=service.default_reply_text,
                llm_model_id=service.llm_model_id,
                llm_model_name=llm.model_name if llm else None,
                llm_provider=llm.provider if llm else None,
                llm_configured=xiaozhi_service.llm_configured(service),
            )
        )
    return XiaozhiServiceListResponse(
        items=result, page=page, page_size=page_size, total=total
    )


@router.post(
    "",
    summary="创建小智中间件服务",
    response_model=XiaozhiServiceOut,
    status_code=201,
    response_description="创建后的服务草稿",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_service(
    payload: XiaozhiServiceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """在一个事务中创建服务草稿、设备映射并绑定问答表和大语言模型。"""
    return service_out(await xiaozhi_service.create_service(db, payload), request)


@router.get(
    "/{service_id}",
    summary="读取小智中间件服务详情",
    response_model=XiaozhiServiceOut,
    response_description="完整服务配置和媒体资产",
    responses={404: NOT_FOUND_ERROR},
)
async def get_service(
    request: Request,
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """读取后台编辑器使用的完整小智中间件服务配置。"""
    return service_out(await xiaozhi_service.get_service(db, service_id), request)


@router.put(
    "/{service_id}",
    summary="修改小智中间件服务",
    response_model=XiaozhiServiceOut,
    response_description="更新后的服务草稿",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_service(
    payload: XiaozhiServiceUpdate,
    request: Request,
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改服务、设备映射、问答表和大模型绑定；已发布服务必须先停止发布。"""
    service = await xiaozhi_service.update_service(db, service_id, payload)
    return service_out(service, request)


@router.delete(
    "/{service_id}",
    summary="删除小智中间件服务",
    response_description="服务、设备映射和媒体删除结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def delete_service(
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """删除服务、关联设备映射和媒体资产；已发布服务必须先停止发布。"""
    await xiaozhi_service.delete_service(
        db, service_id, storage_from_settings(settings)
    )
    return {"message": "小智中间件服务、设备映射和媒体已删除"}


@router.post(
    "/{service_id}/publish",
    summary="发布小智中间件服务",
    response_model=XiaozhiServiceOut,
    response_description="发布后的服务配置",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def publish_service(
    request: Request,
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """校验设备、问答表及已启用的大语言模型后发布服务；媒体均为选填。"""
    return service_out(
        await xiaozhi_service.publish_service(db, service_id, settings), request
    )


@router.post(
    "/{service_id}/unpublish",
    summary="停止发布小智中间件服务",
    response_model=XiaozhiServiceOut,
    response_description="停止发布后的服务配置",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def unpublish_service(
    request: Request,
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """停止公开读取服务配置，但保留全部草稿数据。"""
    return service_out(await xiaozhi_service.unpublish_service(db, service_id), request)


@router.post(
    "/{service_id}/assets/{slot}",
    summary="上传或替换小智中间件服务媒体",
    response_model=XiaozhiServiceAssetUploadResponse,
    response_description="上传后的媒体资产",
    responses={
        403: CSRF_ERROR,
        404: NOT_FOUND_ERROR,
        409: CONFLICT_ERROR,
        413: {"description": "图片超过 10 MiB 或视频超过 200 MiB"},
        415: {"description": "不支持的图片或视频格式"},
        503: {"description": "媒体存储暂时不可用"},
    },
    dependencies=[Depends(require_csrf)],
)
async def upload_asset(
    request: Request,
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    slot: str = Path(description="图片或视频位置编码"),
    file: UploadFile = File(
        ...,
        description="PNG/JPEG/WebP 图片（最大 10 MiB）或 MP4/WebM/MOV 视频（最大 200 MiB）",
    ),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """验证媒体真实内容后写入 MinIO，并替换服务对应媒体位置。"""
    if slot not in XIAOZHI_SERVICE_ASSET_SLOTS:
        raise AppError("INVALID_XIAOZHI_SERVICE_ASSET_SLOT", "媒体位置不合法", 422)
    is_video = slot in XIAOZHI_SERVICE_VIDEO_SLOTS
    max_bytes = (
        settings.max_xiaozhi_service_video_bytes
        if is_video
        else settings.max_xiaozhi_service_asset_bytes
    )
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        message = "视频不能超过 200 MiB" if is_video else "图片不能超过 10 MiB"
        raise AppError("XIAOZHI_SERVICE_ASSET_TOO_LARGE", message, 413)
    content_type, extension = (
        detect_video(data, file.content_type or "")
        if is_video
        else detect_image(data, file.content_type or "")
    )
    storage = storage_from_settings(settings)
    object_key = create_object_key(service_id, slot, extension)
    try:
        stored = await storage.put(object_key, data, content_type)
    except ObjectStorageError as exc:
        raise AppError("OBJECT_STORAGE_UNAVAILABLE", "媒体存储暂时不可用", 503) from exc
    try:
        asset, old_key = await xiaozhi_service.upsert_asset(
            db,
            service_id,
            slot,
            stored.object_key,
            file.filename or f"{slot}.{extension}",
            content_type,
            len(data),
            stored.etag,
        )
    except Exception:
        try:
            await storage.delete(stored.object_key)
        except ObjectStorageError:
            pass
        raise
    if old_key and old_key != stored.object_key:
        try:
            await storage.delete(old_key)
        except ObjectStorageError:
            pass
    return XiaozhiServiceAssetUploadResponse(asset=asset_out(asset, request))


@router.delete(
    "/{service_id}/assets/{slot}",
    summary="删除小智中间件服务媒体",
    response_description="媒体删除结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def delete_asset(
    service_id: int = Path(description="小智中间件服务编号", ge=1),
    slot: str = Path(description="图片或视频位置编码"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """删除服务指定位置的图片或视频；已发布服务必须先停止发布。"""
    if slot not in XIAOZHI_SERVICE_ASSET_SLOTS:
        raise AppError("INVALID_XIAOZHI_SERVICE_ASSET_SLOT", "媒体位置不合法", 422)
    await xiaozhi_service.delete_asset(
        db, service_id, slot, storage_from_settings(settings)
    )
    return {"message": "媒体已删除"}


def detect_image(data: bytes, declared_type: str) -> tuple[str, str]:
    signatures = (
        (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
        (b"\xff\xd8\xff", "image/jpeg", "jpg"),
        (b"RIFF", "image/webp", "webp"),
    )
    for signature, content_type, extension in signatures:
        if data.startswith(signature):
            if content_type == "image/webp" and (
                len(data) < 12 or data[8:12] != b"WEBP"
            ):
                break
            if declared_type and declared_type not in {
                content_type,
                "image/jpg" if content_type == "image/jpeg" else content_type,
            }:
                raise AppError(
                    "INVALID_XIAOZHI_SERVICE_ASSET_TYPE",
                    "图片类型与文件内容不一致",
                    415,
                )
            return content_type, extension
    raise AppError(
        "INVALID_XIAOZHI_SERVICE_ASSET_TYPE",
        "只允许 PNG、JPEG 或 WebP 图片",
        415,
    )


def detect_video(data: bytes, declared_type: str) -> tuple[str, str]:
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        if declared_type and declared_type != "video/webm":
            raise AppError(
                "INVALID_XIAOZHI_SERVICE_ASSET_TYPE",
                "视频类型与文件内容不一致",
                415,
            )
        return "video/webm", "webm"

    if len(data) >= 12 and data[4:8] == b"ftyp":
        is_quicktime = data[8:12] == b"qt  "
        content_type = "video/quicktime" if is_quicktime else "video/mp4"
        extension = "mov" if is_quicktime else "mp4"
        allowed_declared = {
            content_type,
            "application/mp4" if content_type == "video/mp4" else content_type,
        }
        if declared_type and declared_type not in allowed_declared:
            raise AppError(
                "INVALID_XIAOZHI_SERVICE_ASSET_TYPE",
                "视频类型与文件内容不一致",
                415,
            )
        return content_type, extension

    raise AppError(
        "INVALID_XIAOZHI_SERVICE_ASSET_TYPE",
        "只允许 MP4、WebM 或 MOV 视频",
        415,
    )
