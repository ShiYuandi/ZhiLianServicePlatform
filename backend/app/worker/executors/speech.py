from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.frontend_ai_service import FrontendAIService, FrontendAIServiceSpeechBinding
from app.models.speech_model import SpeechRecognitionModel
from app.services.audio_conversion import to_pcm
from app.services.media_validation import validate_audio
from app.services.object_storage import get_object_storage
from app.providers.asr.factory import create_provider


async def execute(task, db, settings, worker_id: str) -> None:
    service = await db.scalar(select(FrontendAIService).options(selectinload(FrontendAIService.speech_binding).selectinload(FrontendAIServiceSpeechBinding.model).selectinload(SpeechRecognitionModel.baidu_config), selectinload(FrontendAIService.speech_binding).selectinload(FrontendAIServiceSpeechBinding.model).selectinload(SpeechRecognitionModel.volcengine_config)).where(FrontendAIService.id == task.service_id))
    if not service or not service.speech_binding or not service.speech_binding.model:
        raise AppError("SPEECH_NOT_CONFIGURED", "语音识别模型未配置", 409)
    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
    data, content_type, _ = await storage.get(task.input_object_key)
    validate_audio(data, content_type)
    pcm = await to_pcm(data, settings.max_ai_audio_seconds)
    result = await create_provider(service.speech_binding.model, settings).recognize(pcm)
    await storage.delete(task.input_object_key)
    from app.services.ai_task_service import succeed_task
    await succeed_task(db, task.id, worker_id, text=result.text)
