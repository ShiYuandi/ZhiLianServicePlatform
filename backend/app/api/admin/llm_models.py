from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    LLM_MODEL_TAG,
    NOT_FOUND_ERROR,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.schemas.llm_model import LLMModelOut, LLMModelPayload
from app.schemas.model_common import (
    ModelArchiveResponse,
    ModelConnectionTestResponse,
    ModelListResponse,
    ModelStatusResponse,
    ModelStatusUpdate,
)
from app.services import llm_model_service


router = APIRouter(
    prefix="/api/admin/ai-models/llm",
    tags=[LLM_MODEL_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


@router.get(
    "",
    summary="分页查询大语言模型",
    response_model=ModelListResponse,
    response_description="大语言模型分页结果",
)
async def list_models(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页最多 100 条"),
    keyword: str | None = Query(default=None, description="搜索模型名称或模型编码"),
    provider: Literal["openai", "dify"] | None = Query(
        default=None, description="按供应器筛选"
    ),
    enabled: bool | None = Query(default=None, description="按启用状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """分页读取未归档的大语言模型，不返回任何调用密钥。"""
    items, total = await llm_model_service.list_models(
        db, page, page_size, keyword, provider, enabled
    )
    return ModelListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post(
    "",
    summary="新建大语言模型",
    response_model=LLMModelOut,
    response_description="创建后的大语言模型安全详情",
    status_code=201,
    responses={403: CSRF_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_model(
    payload: LLMModelPayload = Body(description="按供应器填写的大语言模型配置"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """创建 OpenAI 或 Dify 模型；调用密钥加密保存且不会返回明文。"""
    model = await llm_model_service.create_model(db, payload, settings)
    return llm_model_service.model_out(model, settings)


@router.get(
    "/{model_id}",
    summary="读取大语言模型详情",
    response_model=LLMModelOut,
    response_description="包含脱敏密钥状态的模型详情",
    responses={404: NOT_FOUND_ERROR},
)
async def get_model(
    model_id: int = Path(description="大语言模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """读取大语言模型和供应器调用信息；敏感字段仅返回掩码。"""
    return llm_model_service.model_out(
        await llm_model_service.get_model(db, model_id), settings
    )


@router.put(
    "/{model_id}",
    summary="修改大语言模型",
    response_model=LLMModelOut,
    response_description="更新后的大语言模型安全详情",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_model(
    payload: LLMModelPayload = Body(description="完整的大语言模型配置"),
    model_id: int = Path(description="大语言模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """修改模型和供应器；密钥留空时保留同一供应器的原值。"""
    model = await llm_model_service.update_model(db, model_id, payload, settings)
    return llm_model_service.model_out(model, settings)


@router.put(
    "/{model_id}/status",
    summary="启用或停用大语言模型",
    response_model=ModelStatusResponse,
    response_description="启停结果和受影响服务数量",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def set_status(
    payload: ModelStatusUpdate,
    model_id: int = Path(description="大语言模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改模型启用状态，并返回已绑定的小智中间件服务数量。"""
    _, affected = await llm_model_service.set_enabled(db, model_id, payload.enabled)
    action = "启用" if payload.enabled else "停用"
    return ModelStatusResponse(
        message=f"大语言模型已{action}",
        enabled=payload.enabled,
        affected_service_count=affected,
    )


@router.delete(
    "/{model_id}",
    summary="归档大语言模型",
    response_model=ModelArchiveResponse,
    response_description="模型归档结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def archive_model(
    model_id: int = Path(description="大语言模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """归档未被服务绑定的模型；归档后不再出现在列表和详情中。"""
    await llm_model_service.archive_model(db, model_id)
    return ModelArchiveResponse(message="大语言模型已归档")


@router.post(
    "/{model_id}/test-connection",
    summary="测试大语言模型连接",
    response_model=ModelConnectionTestResponse,
    response_description="供应器连接测试结果",
    responses={
        403: CSRF_ERROR,
        404: NOT_FOUND_ERROR,
        502: {"description": "供应器连接失败或上游服务不可用"},
    },
    dependencies=[Depends(require_csrf)],
)
async def test_connection(
    model_id: int = Path(description="大语言模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """发送最小测试请求验证供应器地址、模型名称和 API Key。"""
    await llm_model_service.test_connection(db, model_id, settings)
    return ModelConnectionTestResponse(success=True, message="模型连接测试成功")
