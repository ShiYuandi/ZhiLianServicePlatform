from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.errors import AppError


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_session_token(
    admin_id: int, session_version: int, settings: Settings
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "sv": session_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_cookie_ttl_minutes),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_session_token(token: str, settings: Settings) -> tuple[int, int]:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        return int(payload["sub"]), int(payload["sv"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError("UNAUTHORIZED", "登录已失效，请重新登录", 401) from exc


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _secret_cipher(secret_key: str) -> Fernet:
    derived = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_secret(value: str, settings: Settings) -> str:
    return (
        _secret_cipher(settings.app_secret_key)
        .encrypt(value.encode("utf-8"))
        .decode("ascii")
    )


def decrypt_secret(value: str, settings: Settings) -> str:
    try:
        return (
            _secret_cipher(settings.app_secret_key)
            .decrypt(value.encode("ascii"))
            .decode("utf-8")
        )
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise AppError(
            "LLM_CONFIG_INVALID", "旧版服务 API 密钥无法解密，请重新配置", 500
        ) from exc


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * max(4, len(value))
    return f"{value[:4]}{'*' * min(24, max(8, len(value) - 8))}{value[-4:]}"


def encrypt_model_credential(value: str, settings: Settings) -> str:
    """使用独立主密钥加密供应器凭据，并写入可轮换的版本前缀。"""

    token = _secret_cipher(settings.model_credential_encryption_key).encrypt(
        value.encode("utf-8")
    )
    return "v1:" + token.decode("ascii")


def decrypt_model_credential(value: str, settings: Settings) -> str:
    """解密版本化供应器凭据；未知版本和错误密钥统一返回安全错误。"""

    try:
        version, token = value.split(":", 1)
        if version != "v1" or not token:
            raise ValueError("unsupported credential version")
        keys = [settings.model_credential_encryption_key]
        if settings.model_credential_previous_encryption_key:
            keys.append(settings.model_credential_previous_encryption_key)
        for key in keys:
            try:
                return (
                    _secret_cipher(key).decrypt(token.encode("ascii")).decode("utf-8")
                )
            except (InvalidToken, UnicodeDecodeError, ValueError):
                continue
        raise InvalidToken
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise AppError(
            "MODEL_CREDENTIAL_INVALID", "模型调用密钥无法解密，请重新配置", 500
        ) from exc


def generate_service_api_key() -> str:
    """生成只展示一次的高熵前端 AI 服务访问密钥。"""

    return "dhs_" + secrets.token_urlsafe(36)


def hash_service_api_key(value: str, settings: Settings) -> str:
    return hmac.new(
        settings.service_api_key_pepper.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_service_api_key(value: str, digest: str, settings: Settings) -> bool:
    return hmac.compare_digest(hash_service_api_key(value, settings), digest)


def service_api_key_hint(value: str) -> str:
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:8]}…{value[-4:]}"


def create_result_download_token(
    task_id: str,
    object_key: str,
    result_expires_at: datetime,
    settings: Settings,
) -> str:
    """创建短期图片下载令牌，且绝不超过结果对象自身过期时间。"""

    now = datetime.now(timezone.utc)
    if result_expires_at.tzinfo is None:
        result_expires_at = result_expires_at.replace(tzinfo=timezone.utc)
    link_expires_at = min(
        result_expires_at,
        now + timedelta(seconds=settings.ai_result_download_ttl_seconds),
    )
    payload = {
        "tid": task_id,
        "key": object_key,
        "iat": now,
        "exp": link_expires_at,
        "aud": "ai-result",
    }
    return jwt.encode(payload, settings.result_download_signing_key, algorithm="HS256")


def decode_result_download_token(token: str, settings: Settings) -> tuple[str, str]:
    try:
        payload = jwt.decode(
            token,
            settings.result_download_signing_key,
            algorithms=["HS256"],
            audience="ai-result",
        )
        task_id = str(payload["tid"])
        object_key = str(payload["key"])
        if not task_id or not object_key:
            raise ValueError("empty result token claim")
        return task_id, object_key
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError("RESULT_LINK_INVALID", "图片访问链接无效或已过期", 401) from exc
