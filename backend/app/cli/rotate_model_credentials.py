from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import decrypt_model_credential, encrypt_model_credential
from app.db.session import get_engine


CREDENTIAL_COLUMNS = (
    ("extended_llm_openai_configs", "model_id", "api_key_encrypted"),
    ("extended_llm_dify_configs", "model_id", "api_key_encrypted"),
    ("extended_asr_baidu_configs", "model_id", "api_key_encrypted"),
    ("extended_asr_baidu_configs", "model_id", "secret_key_encrypted"),
    ("extended_asr_volcengine_configs", "model_id", "access_token_encrypted"),
    ("extended_image_volcengine_configs", "model_id", "api_key_encrypted"),
)


async def rotate() -> int:
    settings = get_settings()
    previous_key = settings.model_credential_previous_encryption_key
    if not previous_key:
        raise RuntimeError(
            "MODEL_CREDENTIAL_PREVIOUS_ENCRYPTION_KEY 未配置，拒绝执行轮换"
        )
    if previous_key == settings.model_credential_encryption_key:
        raise RuntimeError("新旧模型凭据加密密钥不能相同")

    engine = get_engine()
    rotated = 0
    async with engine.begin() as conn:
        for table, primary_key, column in CREDENTIAL_COLUMNS:
            rows = (
                await conn.execute(
                    text(
                        f"SELECT {primary_key}, {column} FROM {table} "
                        f"WHERE {column} IS NOT NULL AND {column} <> ''"
                    )
                )
            ).all()
            for row_id, encrypted in rows:
                plaintext = decrypt_model_credential(encrypted, settings)
                replacement = encrypt_model_credential(plaintext, settings)
                await conn.execute(
                    text(
                        f"UPDATE {table} SET {column} = :replacement "
                        f"WHERE {primary_key} = :row_id"
                    ),
                    {"replacement": replacement, "row_id": row_id},
                )
                rotated += 1
    await engine.dispose()
    return rotated


def main() -> None:
    rotated = asyncio.run(rotate())
    print(f"模型凭据密钥轮换完成，共更新 {rotated} 条凭据。")


if __name__ == "__main__":
    main()
