from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "智联服务台"
    app_env: Literal["test", "development", "production"] = "development"
    app_secret_key: str = "development-only-change-me-please-32chars"
    model_credential_encryption_key: str = "development-model-credential-key-change-me"
    model_credential_previous_encryption_key: str = ""
    service_api_key_pepper: str = "development-service-api-key-pepper-change-me"
    result_download_signing_key: str = "development-result-download-key-change-me"
    log_level: str = "INFO"
    cors_origins: str = "*"

    database_url: str | None = None
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "digital_human_service_platform"
    db_user: str = "root"
    db_password: str = ""

    xiaozhi_api_url: str = ""
    xiaozhi_token: str = ""
    xiaozhi_jsessionid: str = ""
    xiaozhi_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    admin_initial_username: str = "admin"
    admin_initial_password: str = ""
    auth_cookie_name: str = "xz_admin_session"
    auth_cookie_ttl_minutes: int = Field(default=480, ge=10, le=10080)
    # 默认在生产环境启用 Secure Cookie；如果生产环境暂时通过 HTTP/IP
    # 访问，可显式设为 false，切换 HTTPS 后应改回 true。
    auth_cookie_secure: bool | None = None
    max_excel_bytes: int = 10 * 1024 * 1024
    max_excel_rows: int = 10_000
    minio_endpoint: str = "127.0.0.1:30900"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "digital-human-service-platform-development"
    minio_secure: bool = False
    max_xiaozhi_service_asset_bytes: int = 10 * 1024 * 1024
    max_xiaozhi_service_video_bytes: int = 200 * 1024 * 1024

    # 前端 AI 服务、媒体与持久任务
    max_ai_audio_bytes: int = Field(
        default=20 * 1024 * 1024, ge=1024, le=200 * 1024 * 1024
    )
    max_ai_image_bytes: int = Field(
        default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024
    )
    max_ai_prompt_chars: int = Field(default=4000, ge=1, le=50_000)
    max_ai_audio_seconds: int = Field(default=60, ge=1, le=3600)
    ai_task_input_prefix: str = "tasks/input"
    ai_task_result_prefix: str = "tasks/result"
    ai_task_input_retention_hours: int = Field(default=24, ge=1, le=168)
    ai_result_retention_days: int = Field(default=7, ge=1, le=30)
    ai_result_download_ttl_seconds: int = Field(default=600, ge=30, le=3600)

    worker_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)
    worker_lease_seconds: int = Field(default=120, ge=30, le=3600)
    worker_lease_renew_seconds: int = Field(default=30, ge=5, le=1800)
    worker_max_attempts: int = Field(default=3, ge=1, le=10)
    worker_batch_size: int = Field(default=4, ge=1, le=100)
    worker_max_concurrency: int = Field(default=4, ge=1, le=100)

    # OpenAI 兼容大模型代理
    llm_proxy_api_key: str = ""
    upstream_llm_base_url: str = ""
    upstream_llm_api_key: str = ""
    upstream_llm_model: str = ""
    upstream_llm_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    llm_proxy_fallback_text: str = "抱歉，服务暂时不可用，请稍后再试。"
    llm_proxy_stream_interruption_text: str = "抱歉，回答生成被中断，请稍后再试。"
    llm_proxy_max_messages: int = Field(default=50, ge=1, le=200)
    llm_proxy_max_message_chars: int = Field(default=8000, ge=1, le=50000)
    llm_proxy_max_total_chars: int = Field(default=30000, ge=1, le=200000)
    external_proxy_timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    @field_validator("app_secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 32:
            raise ValueError("APP_SECRET_KEY 必须至少为 32 字节")
        return value

    @field_validator(
        "model_credential_encryption_key",
        "model_credential_previous_encryption_key",
        "service_api_key_pepper",
        "result_download_signing_key",
    )
    @classmethod
    def validate_dedicated_secret(cls, value: str) -> str:
        if not value:
            return value
        if len(value.encode("utf-8")) < 32:
            raise ValueError("安全密钥必须至少为 32 字节")
        return value

    @field_validator("ai_task_input_prefix", "ai_task_result_prefix")
    @classmethod
    def normalize_object_prefix(cls, value: str) -> str:
        normalized = value.strip().strip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValueError("MinIO 对象前缀不合法")
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def normalize_origins(cls, value: str) -> str:
        return value.strip() or "*"

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.worker_lease_renew_seconds >= self.worker_lease_seconds:
            raise ValueError("WORKER_LEASE_RENEW_SECONDS 必须小于 WORKER_LEASE_SECONDS")
        if self.app_env == "production":
            missing = []
            if self.app_secret_key.startswith(
                ("development-only", "generate-a-", "replace-with-")
            ):
                missing.append("APP_SECRET_KEY")
            if (
                not self.db_password or self.db_password.startswith("replace-with-")
            ) and not self.database_url:
                missing.append("DB_PASSWORD")
            if (
                not self.xiaozhi_api_url
                or "replace-with-" in self.xiaozhi_api_url
                or "your-" in self.xiaozhi_api_url
            ):
                missing.append("XIAOZHI_API_URL")
            if not self.xiaozhi_token or self.xiaozhi_token.startswith("replace-with-"):
                missing.append("XIAOZHI_TOKEN")
            if not self.xiaozhi_jsessionid or self.xiaozhi_jsessionid.startswith(
                "replace-with-"
            ):
                missing.append("XIAOZHI_JSESSIONID")
            if not self.minio_endpoint or self.minio_endpoint.startswith(
                "replace-with-"
            ):
                missing.append("MINIO_ENDPOINT")
            if not self.minio_access_key or self.minio_access_key.startswith(
                "replace-with-"
            ):
                missing.append("MINIO_ACCESS_KEY")
            if not self.minio_secret_key or self.minio_secret_key.startswith(
                "replace-with-"
            ):
                missing.append("MINIO_SECRET_KEY")
            if not self.minio_bucket or self.minio_bucket.startswith("replace-with-"):
                missing.append("MINIO_BUCKET")
            if not self.llm_proxy_api_key or self.llm_proxy_api_key.startswith(
                "replace-with-"
            ):
                missing.append("LLM_PROXY_API_KEY")
            for name, value in (
                (
                    "MODEL_CREDENTIAL_ENCRYPTION_KEY",
                    self.model_credential_encryption_key,
                ),
                ("SERVICE_API_KEY_PEPPER", self.service_api_key_pepper),
                ("RESULT_DOWNLOAD_SIGNING_KEY", self.result_download_signing_key),
            ):
                if value.startswith(("development-", "generate-a-", "replace-with-")):
                    missing.append(name)
            if missing:
                raise ValueError("生产环境缺少必填配置: " + ", ".join(missing))
        return self

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            "mysql+asyncmy",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def alembic_url(self) -> str:
        url = self.sqlalchemy_url
        if isinstance(url, URL):
            return url.render_as_string(hide_password=False)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
