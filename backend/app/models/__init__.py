from app.models.admin_user import AdminUser
from app.models.device_mapping import DeviceMapping
from app.models.frontend_ai_service import (
    FrontendAIService,
    FrontendAIServiceImageBinding,
    FrontendAIServiceSpeechBinding,
)
from app.models.image_model import ImageGenerationModel, VolcengineImageConfig
from app.models.llm_model import LLMDifyConfig, LLMModel, LLMOpenAIConfig
from app.models.qa import QaItem, QaTable
from app.models.xiaozhi_service import XiaozhiMiddlewareService
from app.models.xiaozhi_service_asset import XiaozhiServiceAsset
from app.models.speech_model import (
    BaiduASRConfig,
    SpeechRecognitionModel,
    VolcengineASRConfig,
)
from app.models.ai_task import AITask
from app.models.external_api_proxy import ExternalApiProxy

__all__ = [
    "AdminUser",
    "DeviceMapping",
    "FrontendAIService",
    "FrontendAIServiceSpeechBinding",
    "FrontendAIServiceImageBinding",
    "ImageGenerationModel",
    "VolcengineImageConfig",
    "LLMModel",
    "LLMOpenAIConfig",
    "LLMDifyConfig",
    "SpeechRecognitionModel",
    "BaiduASRConfig",
    "VolcengineASRConfig",
    "XiaozhiMiddlewareService",
    "XiaozhiServiceAsset",
    "QaItem",
    "QaTable",
    "AITask",
    "ExternalApiProxy",
]
