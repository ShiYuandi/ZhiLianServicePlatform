from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.frontend_ai_service import FrontendAIService, FrontendAIServiceImageBinding
from app.models.image_model import ImageGenerationModel
from app.providers.image.factory import create_provider
from app.services.object_storage import get_object_storage
from app.services.media_validation import validate_image


async def execute(task, db, settings, worker_id: str) -> None:
    service = await db.scalar(select(FrontendAIService).options(selectinload(FrontendAIService.image_binding).selectinload(FrontendAIServiceImageBinding.model).selectinload(ImageGenerationModel.volcengine_config)).where(FrontendAIService.id == task.service_id))
    if not service or not service.image_binding or not service.image_binding.model:
        raise AppError("IMAGE_NOT_CONFIGURED", "图像生成模型未配置", 409)
    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
    image_bytes = None
    if task.input_object_key:
        image_bytes, content_type, _ = await storage.get(task.input_object_key)
        validate_image(image_bytes)
    opts = task.options or {}
    result = await create_provider(service.image_binding.model, settings).generate(task.prompt or "", image_bytes=image_bytes, width=opts.get("width"), height=opts.get("height"))
    result_key = f"{settings.ai_task_result_prefix}/{service.id}/{task.id}.png"
    await storage.put(result_key, result.png_bytes, "image/png")
    if task.input_object_key:
        await storage.delete(task.input_object_key)
    from app.services.ai_task_service import succeed_task
    await succeed_task(db, task.id, worker_id, result_object_key=result_key, result_expires_at=datetime.now(timezone.utc) + timedelta(days=settings.ai_result_retention_days))
