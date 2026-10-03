from app.core.config import Settings
from app.core.security import decrypt_model_credential
from app.models.speech_model import SpeechRecognitionModel
from app.providers.asr.baidu import BaiduASRProvider
from app.providers.asr.volcengine import VolcengineASRProvider


def create_provider(model: SpeechRecognitionModel, settings: Settings):
    if model.provider == "baidu" and model.baidu_config:
        return BaiduASRProvider(app_id=model.baidu_config.app_id, api_key=decrypt_model_credential(model.baidu_config.api_key_encrypted, settings), secret_key=decrypt_model_credential(model.baidu_config.secret_key_encrypted, settings), dev_pid=model.baidu_config.dev_pid)
    if model.provider == "volcengine" and model.volcengine_config:
        c = model.volcengine_config
        return VolcengineASRProvider(app_id=c.app_id, access_token=decrypt_model_credential(c.access_token_encrypted, settings), resource_id=c.resource_id or "volc.bigasr.sauc.duration", language=c.language or "zh-CN", boosting_table_name=c.boosting_table_name, correct_table_name=c.correct_table_name)
    raise ValueError("语音模型凭据未配置")
