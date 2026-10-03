from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.image_model import ImageGenerationModel, VolcengineImageConfig
from app.models.speech_model import (
    BaiduASRConfig,
    SpeechRecognitionModel,
    VolcengineASRConfig,
)


async def seed() -> int:
    """写入 Unity 参考项目对应的无密钥模型模板，重复执行安全。"""

    inserted = 0
    async with get_session_factory()() as db:
        templates = [
            SpeechRecognitionModel(
                model_name="百度短语音识别（Unity）",
                model_code="baidu-short-asr",
                provider="baidu",
                sort_order=10,
                remark="对齐 Unity BaiduSpeechService：16kHz、16bit、单声道 PCM。请在后台填写 AppID、API Key 和 Secret Key。",
                baidu_config=BaiduASRConfig(dev_pid=1537),
            ),
            SpeechRecognitionModel(
                model_name="火山豆包 ASR v2",
                model_code="volcengine-doubao-asr",
                provider="volcengine",
                sort_order=20,
                remark="兼容小智服务豆包 ASR v2 非流式协议。请在后台填写 AppID、Access Token 和资源 ID。",
                volcengine_config=VolcengineASRConfig(
                    resource_id="volc.bigasr.sauc.duration",
                    language="zh-CN",
                ),
            ),
            ImageGenerationModel(
                model_name="火山 Seedream 4.0（Unity）",
                model_code="seedream-4-0",
                provider="volcengine",
                sort_order=10,
                remark="同一配置支持文生图和单图图生图；参考 Unity VolcImageService。",
                volcengine_config=VolcengineImageConfig(
                    api_url="https://ark.cn-beijing.volces.com/api/v3/images/generations",
                    upstream_model="doubao-seedream-4-0-250828",
                    default_width=932,
                    default_height=582,
                ),
            ),
        ]
        for template in templates:
            model_type = (
                SpeechRecognitionModel
                if isinstance(template, SpeechRecognitionModel)
                else ImageGenerationModel
            )
            exists = await db.scalar(
                select(model_type.id).where(model_type.model_code == template.model_code)
            )
            if exists:
                continue
            db.add(template)
            inserted += 1
        await db.commit()
    return inserted


if __name__ == "__main__":
    count = asyncio.run(seed())
    print(f"seeded {count} Unity AI model templates")
