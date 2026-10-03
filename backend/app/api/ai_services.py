from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, Header, Path, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import PUBLIC_TAG, PUBLIC_RESPONSES, UNAUTHORIZED_ERROR
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import create_result_download_token, decode_result_download_token
from app.db.session import get_db
from app.dependencies.service_auth import (
    get_frontend_ai_service,
    get_frontend_ai_service_public,
)
from app.models.frontend_ai_service import (
    FrontendAIService,
)
from app.schemas.ai_task import AITaskOut, ServiceConfigOut
from app.services import ai_task_service
from app.services.object_storage import ObjectStorageError, get_object_storage
from app.services.media_validation import validate_audio, validate_image

router = APIRouter(prefix="/api/v1/ai-services", tags=[PUBLIC_TAG])


def _task_out(task, settings: Settings, service_code: str | None = None) -> AITaskOut:
    result_url = None
    if task.result_object_key and task.status == "succeeded":
        token = create_result_download_token(task.id, task.result_object_key, task.result_expires_at, settings)
        result_url = f"/api/v1/ai-services/{service_code or task.service_id}/image-results/{task.id}?token={token}"
    result = None
    if task.status == "succeeded":
        result = {"text": task.result_text} if task.task_type == "speech_recognition" else {"imageUrl": result_url, "expiresAt": task.result_expires_at}
    return AITaskOut(taskId=task.id, taskType=task.task_type, status=task.status, text=task.result_text, resultUrl=result_url, result=result, errorCode=task.error_code, errorMessage=task.error_message, createdAt=task.created_at, completedAt=task.completed_at, resultExpiresAt=task.result_expires_at)


def _check_enabled(service: FrontendAIService) -> None:
    if not service.enabled:
        raise AppError("SERVICE_DISABLED", "服务当前未启用", 403)


async def _read_upload(upload: UploadFile, max_bytes: int) -> bytes:
    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AppError("MEDIA_TOO_LARGE", "上传文件超过大小限制", 413)
    if not data:
        raise AppError("MEDIA_EMPTY", "上传文件不能为空", 422)
    return data


@router.get("/{service_code}", response_model=ServiceConfigOut, summary="读取前端 AI 服务配置", response_description="服务能力和接口版本", responses={**PUBLIC_RESPONSES, 401: UNAUTHORIZED_ERROR})
async def service_config(service_code: str = Path(description="服务编码"), service: FrontendAIService = Depends(get_frontend_ai_service)):
    """返回服务启用状态、接口版本和已绑定能力，不暴露供应器详情。"""
    capabilities = []
    if service.speech_binding:
        capabilities.append("speech_recognition")
    if service.image_binding:
        capabilities.append("image_generation")
    return ServiceConfigOut(serviceName=service.service_name, serviceCode=service.service_code, enabled=service.enabled, capabilities=capabilities, apiVersion="v1")


@router.post("/{service_code}/speech-tasks", response_model=AITaskOut, status_code=202, summary="异步提交语音识别任务", response_description="已创建的持久化语音任务", responses={**PUBLIC_RESPONSES, 401: UNAUTHORIZED_ERROR})
async def create_speech_task(
    upload: UploadFile = File(description="WAV、MP3、M4A、OGG 或 WebM 音频文件"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128, description="可选幂等键，重复提交返回同一任务"),
    service_code: str = Path(description="服务编码"), service: FrontendAIService = Depends(get_frontend_ai_service),
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings),
):
    """接收音频并写入 MinIO 与 MySQL，任务由独立 Worker 异步处理。"""
    _check_enabled(service)
    binding = service.speech_binding
    if not binding or not binding.model:
        raise AppError("SPEECH_NOT_CONFIGURED", "服务未绑定语音识别模型", 409)
    model = binding.model
    if not model.enabled or model.archived_at is not None:
        raise AppError("SPEECH_MODEL_DISABLED", "绑定的语音识别模型不可用", 409)
    existing = await ai_task_service.find_idempotent(db, service.id, "speech_recognition", idempotency_key)
    if existing:
        return _task_out(existing, settings, service.service_code)
    if await ai_task_service.count_inflight(db, service.id) >= service.max_inflight_tasks:
        raise AppError("INFLIGHT_LIMIT_EXCEEDED", "当前在途任务数已达上限", 429)
    from datetime import datetime, timezone
    if await ai_task_service.count_recent(db, service.id, "speech_recognition", datetime.now(timezone.utc) - timedelta(minutes=1)) >= service.rate_limit_per_minute:
        raise AppError("RATE_LIMIT_EXCEEDED", "已超过每分钟任务上限", 429)
    data = await _read_upload(upload, settings.max_ai_audio_bytes)
    validate_audio(data, upload.content_type)
    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
    object_key = f"{settings.ai_task_input_prefix}/{service.id}/speech/{uuid.uuid4().hex}.bin"
    await storage.put(object_key, data, upload.content_type or "application/octet-stream")
    try:
        task, _ = await ai_task_service.create_task(db, service_id=service.id, task_type="speech_recognition", model_id=model.id, model_name=model.model_name, model_code=model.model_code, provider=model.provider, model_snapshot={"name": model.model_name, "code": model.model_code, "provider": model.provider}, input_object_key=object_key, idempotency_key=idempotency_key, max_attempts=settings.worker_max_attempts)
    except Exception:
        await storage.delete(object_key)
        raise
    return _task_out(task, settings, service.service_code)


@router.post("/{service_code}/image-tasks", response_model=AITaskOut, status_code=202, summary="异步提交图像生成任务", response_description="已创建的持久化图像任务", responses={**PUBLIC_RESPONSES, 401: UNAUTHORIZED_ERROR})
async def create_image_task(
    prompt: str = Form(description="图像生成提示词"),
    image: UploadFile | None = File(default=None, description="可选单张参考图，用于图生图"),
    width: int | None = Form(default=None, ge=64, le=4096, description="目标宽度，可选"),
    height: int | None = Form(default=None, ge=64, le=4096, description="目标高度，可选"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128, description="可选幂等键，重复提交返回同一任务"),
    service_code: str = Path(description="服务编码"), service: FrontendAIService = Depends(get_frontend_ai_service), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings),
):
    """接收提示词和可选单张参考图，异步生成并保存七天的 PNG 结果。"""
    _check_enabled(service)
    binding = service.image_binding
    if not binding or not binding.model:
        raise AppError("IMAGE_NOT_CONFIGURED", "服务未绑定图像生成模型", 409)
    model = binding.model
    if not model.enabled or model.archived_at is not None:
        raise AppError("IMAGE_MODEL_DISABLED", "绑定的图像生成模型不可用", 409)
    existing = await ai_task_service.find_idempotent(db, service.id, "image_generation", idempotency_key)
    if existing:
        return _task_out(existing, settings, service.service_code)
    prompt = prompt.strip()
    if not prompt or len(prompt) > settings.max_ai_prompt_chars:
        raise AppError("PROMPT_INVALID", "提示词不能为空且不能超过长度限制", 422)
    if await ai_task_service.count_inflight(db, service.id) >= service.max_inflight_tasks:
        raise AppError("INFLIGHT_LIMIT_EXCEEDED", "当前在途任务数已达上限", 429)
    data = None
    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
    object_key = None
    if image is not None:
        data = await _read_upload(image, settings.max_ai_image_bytes)
        validate_image(data)
        object_key = f"{settings.ai_task_input_prefix}/{service.id}/image/{uuid.uuid4().hex}.bin"
        await storage.put(object_key, data, image.content_type or "application/octet-stream")
    try:
        task, _ = await ai_task_service.create_task(db, service_id=service.id, task_type="image_generation", model_id=model.id, model_name=model.model_name, model_code=model.model_code, provider=model.provider, model_snapshot={"name": model.model_name, "code": model.model_code, "provider": model.provider}, input_object_key=object_key, prompt=prompt, options={"width": width, "height": height}, idempotency_key=idempotency_key, max_attempts=settings.worker_max_attempts)
    except Exception:
        if object_key:
            await storage.delete(object_key)
        raise
    return _task_out(task, settings, service.service_code)


@router.get("/{service_code}/tasks/{task_id}", response_model=AITaskOut, summary="查询前端 AI 任务", response_description="任务当前状态和结果", responses={**PUBLIC_RESPONSES, 401: UNAUTHORIZED_ERROR})
async def task_status(service_code: str = Path(description="服务编码"), task_id: str = Path(min_length=36, max_length=36, description="任务编号"), service: FrontendAIService = Depends(get_frontend_ai_service), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)):
    """查询任务状态；停用服务仍可查询此前创建的任务。"""
    return _task_out(await ai_task_service.get_task(db, task_id, service.id), settings, service.service_code)


@router.get("/{service_code}/image-results/{task_id}", summary="下载图像任务结果", response_description="图像二进制内容", responses={**PUBLIC_RESPONSES, 401: UNAUTHORIZED_ERROR})
async def image_result(service_code: str = Path(description="服务编码"), task_id: str = Path(description="任务编号"), token: str = Query(description="短期结果签名"), service: FrontendAIService = Depends(get_frontend_ai_service_public), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)):
    """校验平台签名令牌后返回私有 MinIO 图片对象。

    该端点不要求 Bearer 服务密钥：URL 中的签名令牌本身即访问凭证
    （含过期时间，且不超过结果保留期），便于二维码等无法附加请求头的场景直接访问。
    """
    signed_task, object_key = decode_result_download_token(token, settings)
    if signed_task != task_id:
        raise AppError("RESULT_LINK_INVALID", "图片访问链接无效或已过期", 401)
    task = await ai_task_service.get_task(db, task_id, service.id)
    if task.status != "succeeded" or task.result_object_key != object_key or not task.result_expires_at:
        raise AppError("RESULT_NOT_AVAILABLE", "图片结果不存在或已过期", 404)
    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
    try:
        data, content_type, _ = await storage.get(object_key)
    except ObjectStorageError as exc:
        raise AppError("RESULT_NOT_AVAILABLE", "图片结果不存在或已过期", 404) from exc
    return StreamingResponse(iter([data]), media_type=content_type or "image/png")
