from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import encrypt_model_credential
from app.db.session import get_session_factory
from app.models.image_model import ImageGenerationModel
from app.models.speech_model import SpeechRecognitionModel


def _component(text: str, guid: str) -> str:
    for match in re.finditer(r"--- !u!\d+.*?(?=\n--- !u!|\Z)", text, re.S):
        block = match.group(0)
        if f"guid: {guid}" in block:
            return block
    raise ValueError(f"Unity 场景中找不到组件 {guid}")


def _field(block: str, name: str) -> str:
    match = re.search(rf"^\s*{re.escape(name)}:\s*(.+)$", block, re.M)
    if not match or not match.group(1).strip():
        raise ValueError(f"Unity 场景中的 {name} 为空")
    return match.group(1).strip()


async def import_credentials(scene_path: Path) -> None:
    text = scene_path.read_text(encoding="utf-8")
    baidu = _component(text, "c3222600bc80fe948b2beb8a1d2e9c3d")
    seedream = _component(text, "2a382dd607df26f4d91fc4469303dc0d")
    baidu_key = _field(baidu, "apiKey")
    baidu_secret = _field(baidu, "secretKey")
    seedream_key = _field(seedream, "apiKey")

    settings = get_settings()
    async with get_session_factory()() as db:
        speech = await db.scalar(
            select(SpeechRecognitionModel)
            .options(selectinload(SpeechRecognitionModel.baidu_config))
            .where(SpeechRecognitionModel.model_code == "baidu-short-asr")
        )
        image = await db.scalar(
            select(ImageGenerationModel)
            .options(selectinload(ImageGenerationModel.volcengine_config))
            .where(ImageGenerationModel.model_code == "seedream-4-0")
        )
        if not speech or not speech.baidu_config:
            raise ValueError("请先执行 seed_ai_models 创建百度模型模板")
        if not image or not image.volcengine_config:
            raise ValueError("请先执行 seed_ai_models 创建 Seedream 模型模板")
        speech.baidu_config.api_key_encrypted = encrypt_model_credential(
            baidu_key, settings
        )
        speech.baidu_config.secret_key_encrypted = encrypt_model_credential(
            baidu_secret, settings
        )
        image.volcengine_config.api_key_encrypted = encrypt_model_credential(
            seedream_key, settings
        )
        await db.commit()
    print("已导入百度短语音识别和 Seedream 凭据（仅输出状态，不输出密钥）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 Unity 场景导入 AI 模型凭据")
    parser.add_argument("scene", type=Path, help="SampleScene.unity 的绝对路径")
    args = parser.parse_args()
    asyncio.run(import_credentials(args.scene))
