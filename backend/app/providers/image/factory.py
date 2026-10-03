from app.core.config import Settings
from app.core.security import decrypt_model_credential
from app.models.image_model import ImageGenerationModel
from app.providers.image.volcengine import VolcengineImageProvider


def create_provider(model: ImageGenerationModel, settings: Settings):
    if model.provider == "volcengine" and model.volcengine_config:
        c = model.volcengine_config
        return VolcengineImageProvider(api_url=c.api_url, api_key=decrypt_model_credential(c.api_key_encrypted, settings), upstream_model=c.upstream_model or "", default_width=c.default_width, default_height=c.default_height, timeout_seconds=c.timeout_seconds, watermark=c.watermark)
    raise ValueError("图像模型凭据未配置")
