from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    NOT_FOUND_ERROR,
    SPEECH_MODEL_TAG,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.schemas.model_common import (
    ModelArchiveResponse,
    ModelConnectionTestResponse,
    ModelListResponse,
    ModelStatusResponse,
    ModelStatusUpdate,
)
from app.schemas.speech_model import SpeechModelOut, SpeechModelPayload
from app.services import speech_model_service
from app.core.security import decrypt_model_credential
from app.providers.asr import BaiduASRProvider, VolcengineASRProvider


router = APIRouter(
    prefix="/api/admin/ai-models/speech-recognition",
    tags=[SPEECH_MODEL_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


@router.get(
    "",
    summary="分页查询语音识别模型",
    response_model=ModelListResponse,
    response_description="语音识别模型分页结果",
)
async def list_models(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页最多 100 条"),
    keyword: str | None = Query(default=None, description="搜索模型名称或模型编码"),
    provider: Literal["baidu", "volcengine"] | None = Query(
        default=None, description="按供应器筛选"
    ),
    enabled: bool | None = Query(default=None, description="按启用状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """分页读取未归档的语音识别模型，不返回任何调用密钥。"""
    items, total = await speech_model_service.list_models(
        db, page, page_size, keyword, provider, enabled
    )
    return ModelListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post(
    "",
    summary="新建语音识别模型",
    response_model=SpeechModelOut,
    response_description="创建后的语音识别模型安全详情",
    status_code=201,
    responses={403: CSRF_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_model(
    payload: SpeechModelPayload = Body(description="按供应器填写的语音识别模型配置"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """创建百度或火山语音识别模型，所有调用密钥均加密保存。"""
    return speech_model_service.model_out(
        await speech_model_service.create_model(db, payload, settings), settings
    )


@router.get(
    "/{model_id}",
    summary="读取语音识别模型详情",
    response_model=SpeechModelOut,
    response_description="包含脱敏密钥状态的模型详情",
    responses={404: NOT_FOUND_ERROR},
)
async def get_model(
    model_id: int = Path(description="语音识别模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """读取语音识别模型详情；API Key、Secret Key 和 Token 仅返回掩码。"""
    return speech_model_service.model_out(
        await speech_model_service.get_model(db, model_id), settings
    )


@router.put(
    "/{model_id}",
    summary="修改语音识别模型",
    response_model=SpeechModelOut,
    response_description="更新后的语音识别模型安全详情",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_model(
    payload: SpeechModelPayload = Body(description="完整的语音识别模型配置"),
    model_id: int = Path(description="语音识别模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """修改模型及其供应器配置；同一供应器的敏感字段留空保持原值。"""
    return speech_model_service.model_out(
        await speech_model_service.update_model(db, model_id, payload, settings),
        settings,
    )


@router.put(
    "/{model_id}/status",
    summary="启用或停用语音识别模型",
    response_model=ModelStatusResponse,
    response_description="启停结果和受影响服务数量",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def set_status(
    payload: ModelStatusUpdate,
    model_id: int = Path(description="语音识别模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改模型启用状态，并返回受影响的前端 AI 服务数量。"""
    _, affected = await speech_model_service.set_enabled(db, model_id, payload.enabled)
    action = "启用" if payload.enabled else "停用"
    return ModelStatusResponse(
        message=f"语音识别模型已{action}",
        enabled=payload.enabled,
        affected_service_count=affected,
    )


@router.delete(
    "/{model_id}",
    summary="归档语音识别模型",
    response_model=ModelArchiveResponse,
    response_description="模型归档结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def archive_model(
    model_id: int = Path(description="语音识别模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """归档未被前端 AI 服务绑定的语音识别模型。"""
    await speech_model_service.archive_model(db, model_id)
    return ModelArchiveResponse(message="语音识别模型已归档")


@router.post(
    "/{model_id}/test-connection",
    summary="测试语音识别模型连接",
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
    model_id: int = Path(description="语音识别模型编号", ge=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """验证当前模型凭据并执行供应器轻量连接测试，不提交音频任务。"""
    model = await speech_model_service.get_model(db, model_id)
    if model.provider == "baidu":
        config = model.baidu_config
        if not config or not config.api_key_encrypted or not config.secret_key_encrypted:
            raise AppError("MODEL_CREDENTIAL_MISSING", "百度 API Key / Secret Key 未完整配置", 409)
        provider = BaiduASRProvider(
            app_id=config.app_id,
            api_key=decrypt_model_credential(config.api_key_encrypted, settings),
            secret_key=decrypt_model_credential(config.secret_key_encrypted, settings),
            dev_pid=config.dev_pid,
        )
    else:
        config = model.volcengine_config
        if not config or not config.access_token_encrypted:
            raise AppError("MODEL_CREDENTIAL_MISSING", "火山 ASR Access Token 未配置", 409)
        provider = VolcengineASRProvider(
            app_id=config.app_id,
            access_token=decrypt_model_credential(config.access_token_encrypted, settings),
            resource_id=config.resource_id or "volc.bigasr.sauc.duration",
            language=config.language or "zh-CN",
            boosting_table_name=config.boosting_table_name,
            correct_table_name=config.correct_table_name,
        )
    try:
        await provider.test_connection()
    except Exception as exc:
        if isinstance(exc, AppError):
            raise
        raise AppError("MODEL_CONNECTION_FAILED", str(exc), 502) from exc
    return ModelConnectionTestResponse(success=True, message="模型凭据和供应器连接正常")
