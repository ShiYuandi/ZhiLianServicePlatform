from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    FRONTEND_AI_SERVICE_TAG,
    NOT_FOUND_ERROR,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.models.frontend_ai_service import FrontendAIService
from app.schemas.frontend_ai_service import (
    FrontendAIServiceArchiveResponse,
    FrontendAIServiceCreate,
    FrontendAIServiceCreated,
    FrontendAIServiceKeyRotated,
    FrontendAIServiceListResponse,
    FrontendAIServiceOut,
    FrontendAIServiceUpdate,
)
from app.services import frontend_ai_service


router = APIRouter(
    prefix="/api/admin/frontend-ai-services",
    tags=[FRONTEND_AI_SERVICE_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


def service_out(service: FrontendAIService) -> FrontendAIServiceOut:
    speech = service.speech_binding.model if service.speech_binding else None
    image = service.image_binding.model if service.image_binding else None
    return FrontendAIServiceOut(
        id=service.id,
        service_name=service.service_name,
        service_code=service.service_code,
        enabled=service.enabled,
        remark=service.remark,
        api_key_hint=frontend_ai_service.api_key_hint(service),
        api_key_version=service.api_key_version,
        rate_limit_per_minute=service.rate_limit_per_minute,
        max_inflight_tasks=service.max_inflight_tasks,
        allowed_origins=service.allowed_origins,
        speech_model_id=speech.id if speech else None,
        speech_model_name=speech.model_name if speech else None,
        speech_provider=speech.provider if speech else None,
        image_model_id=image.id if image else None,
        image_model_name=image.model_name if image else None,
        image_provider=image.provider if image else None,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )


@router.get(
    "",
    summary="分页查询前端 AI 服务",
    response_model=FrontendAIServiceListResponse,
    response_description="前端 AI 服务、安全策略和能力绑定分页结果",
)
async def list_services(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页最多 100 条"),
    keyword: str | None = Query(default=None, description="搜索服务名称或服务编码"),
    enabled: bool | None = Query(default=None, description="按启用状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """分页读取未归档服务；永远不返回可用的服务 API Key。"""
    items, total = await frontend_ai_service.list_services(
        db, page, page_size, keyword, enabled
    )
    return FrontendAIServiceListResponse(
        items=[service_out(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    summary="创建前端 AI 服务",
    response_model=FrontendAIServiceCreated,
    response_description="创建结果；完整 API Key 仅本次返回",
    status_code=201,
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_service(
    payload: FrontendAIServiceCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """创建服务及其类型化模型绑定，并自动生成服务编码和只展示一次的 API Key。"""
    service, api_key = await frontend_ai_service.create_service(db, payload, settings)
    return FrontendAIServiceCreated(
        **service_out(service).model_dump(), api_key=api_key
    )


@router.get(
    "/{service_id}",
    summary="读取前端 AI 服务详情",
    response_model=FrontendAIServiceOut,
    response_description="服务配置、API Key 提示和能力绑定",
    responses={404: NOT_FOUND_ERROR},
)
async def get_service(
    service_id: int = Path(description="前端 AI 服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """读取后台编辑器使用的服务详情，不返回完整 API Key 或哈希。"""
    return service_out(await frontend_ai_service.get_service(db, service_id))


@router.put(
    "/{service_id}",
    summary="修改前端 AI 服务",
    response_model=FrontendAIServiceOut,
    response_description="更新后的服务和能力绑定",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_service(
    payload: FrontendAIServiceUpdate,
    service_id: int = Path(description="前端 AI 服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改服务安全策略与模型绑定；服务编码和 API Key 不在此接口修改。"""
    return service_out(
        await frontend_ai_service.update_service(db, service_id, payload)
    )


@router.post(
    "/{service_id}/rotate-api-key",
    summary="重新生成服务 API Key",
    response_model=FrontendAIServiceKeyRotated,
    response_description="新 API Key 仅本次返回，旧 Key 立即失效",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def rotate_api_key(
    service_id: int = Path(description="前端 AI 服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """轮换不可逆服务凭据；调用方必须立即保存新 Key。"""
    api_key, hint, version = await frontend_ai_service.rotate_api_key(
        db, service_id, settings
    )
    return FrontendAIServiceKeyRotated(
        api_key=api_key, api_key_hint=hint, api_key_version=version
    )


@router.delete(
    "/{service_id}",
    summary="归档前端 AI 服务",
    response_model=FrontendAIServiceArchiveResponse,
    response_description="服务归档结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def archive_service(
    service_id: int = Path(description="前端 AI 服务编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """停用并归档服务，释放当前模型绑定，保留后续任务历史引用空间。"""
    await frontend_ai_service.archive_service(db, service_id)
    return FrontendAIServiceArchiveResponse(message="前端 AI 服务已归档")
