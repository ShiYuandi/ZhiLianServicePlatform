from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    IMAGE_MODEL_TAG,
    NOT_FOUND_ERROR,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.schemas.image_model import ImageModelOut, ImageVolcenginePayload
from app.schemas.model_common import (
    ModelArchiveResponse,
    ModelConnectionTestResponse,
    ModelListResponse,
    ModelStatusResponse,
    ModelStatusUpdate,
)
from app.services import image_model_service
from app.core.security import decrypt_model_credential
from app.providers.image import ImageProviderError, VolcengineImageProvider


router = APIRouter(
    prefix="/api/admin/ai-models/image-generation",
    tags=[IMAGE_MODEL_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


@router.get(
    "",
    summary="分页查询图像生成模型",
    response_model=ModelListResponse,
    response_description="图像生成模型分页结果",
)
async def list_models(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页最多 100 条"),
    keyword: str | None = Query(default=None, description="搜索模型名称或模型编码"),
    provider: Literal["volcengine"] | None = Query(
        default=None, description="按供应器筛选"
    ),
    enabled: bool | None = Query(default=None, description="按启用状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """分页读取未归档的图像生成模型，不返回供应器 API Key。"""
    items, total = await image_model_service.list_models(
        db, page, page_size, keyword, provider, enabled
    )
    return ModelListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post(
    "",
    summary="新建图像生成模型",
    response_model=ImageModelOut,
    response_description="创建后的图像生成模型安全详情",
    status_code=201,
    responses={403: CSRF_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_model(
    payload: ImageVolcenginePayload = Body(
        description="火山 Seedream 图像生成模型配置"
    ),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """创建支持文生图和单图图生图的火山 Seedream 模型。"""
    return image_model_service.model_out(
        await image_model_service.create_model(db, payload, settings), settings
    )


@router.get(
    "/{model_id}",
    summary="读取图像生成模型详情",
    response_model=ImageModelOut,
    response_description="包含脱敏密钥状态的模型详情",
    responses={404: NOT_FOUND_ERROR},
)
async def get_model(
    model_id: int = Path(description="图像生成模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """读取 Seedream 模型详情；供应器 API Key 仅返回掩码。"""
    return image_model_service.model_out(
        await image_model_service.get_model(db, model_id), settings
    )


@router.put(
    "/{model_id}",
    summary="修改图像生成模型",
    response_model=ImageModelOut,
    response_description="更新后的图像生成模型安全详情",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_model(
    payload: ImageVolcenginePayload = Body(description="完整的火山 Seedream 模型配置"),
    model_id: int = Path(description="图像生成模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """修改 Seedream 模型；API Key 留空时保持原值。"""
    return image_model_service.model_out(
        await image_model_service.update_model(db, model_id, payload, settings),
        settings,
    )


@router.put(
    "/{model_id}/status",
    summary="启用或停用图像生成模型",
    response_model=ModelStatusResponse,
    response_description="启停结果和受影响服务数量",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def set_status(
    payload: ModelStatusUpdate,
    model_id: int = Path(description="图像生成模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改模型启用状态，并返回受影响的前端 AI 服务数量。"""
    _, affected = await image_model_service.set_enabled(db, model_id, payload.enabled)
    action = "启用" if payload.enabled else "停用"
    return ModelStatusResponse(
        message=f"图像生成模型已{action}",
        enabled=payload.enabled,
        affected_service_count=affected,
    )


@router.delete(
    "/{model_id}",
    summary="归档图像生成模型",
    response_model=ModelArchiveResponse,
    response_description="模型归档结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def archive_model(
    model_id: int = Path(description="图像生成模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """归档未被前端 AI 服务绑定的图像生成模型。"""
    await image_model_service.archive_model(db, model_id)
    return ModelArchiveResponse(message="图像生成模型已归档")


@router.post(
    "/{model_id}/test-connection",
    summary="测试图像生成模型连接",
    response_model=ModelConnectionTestResponse,
    response_description="供应器连接测试结果",
    responses={
        403: CSRF_ERROR,
        404: NOT_FOUND_ERROR,
        409: {"description": "模型凭据未完整配置"},
        502: {"description": "供应器连接失败"},
    },
    dependencies=[Depends(require_csrf)],
)
async def test_connection(
    model_id: int = Path(description="图像生成模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """校验 Seedream 配置和密钥，不生成图片、不消耗额度。"""
    model = await image_model_service.get_model(db, model_id)
    config = model.volcengine_config
    if not config or not config.api_key_encrypted or not config.upstream_model:
        raise AppError("MODEL_CREDENTIAL_MISSING", "火山 Seedream API Key / 模型 ID 未完整配置", 409)
    provider = VolcengineImageProvider(
        api_url=config.api_url,
        api_key=decrypt_model_credential(config.api_key_encrypted, settings),
        upstream_model=config.upstream_model,
        default_width=config.default_width,
        default_height=config.default_height,
        timeout_seconds=config.timeout_seconds,
        watermark=config.watermark,
    )
    try:
        await provider.test_connection()
    except ImageProviderError as exc:
        raise AppError(exc.code, str(exc), 409) from exc
    return ModelConnectionTestResponse(success=True, message="Seedream 配置和供应器连接正常")
