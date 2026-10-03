import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_platform_and_database_secrets():
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            app_secret_key="a-secure-production-secret-with-32-bytes",
            database_url=None,
            db_password="",
            xiaozhi_token="",
            xiaozhi_jsessionid="",
            admin_initial_password="",
            model_credential_encryption_key="development-model-credential-key-change-me",
            service_api_key_pepper="development-service-api-key-pepper-change-me",
            result_download_signing_key="development-result-download-key-change-me",
        )
    message = str(exc.value)
    assert "DB_PASSWORD" in message
    assert "XIAOZHI_TOKEN" in message
    assert "XIAOZHI_JSESSIONID" in message
    assert "MODEL_CREDENTIAL_ENCRYPTION_KEY" in message
    assert "SERVICE_API_KEY_PEPPER" in message
    assert "RESULT_DOWNLOAD_SIGNING_KEY" in message
    assert "ADMIN_INITIAL_PASSWORD" not in message


def test_development_and_test_are_distinct_environments():
    development = Settings(app_env="development")
    test = Settings(app_env="test")
    assert development.app_env == "development"
    assert test.app_env == "test"
    assert development.app_name == "智联服务台"
    assert development.ai_result_retention_days == 7


def test_auth_cookie_secure_can_be_overridden_for_http_production_access():
    settings = Settings(
        app_env="production",
        app_secret_key="a" * 40,
        model_credential_encryption_key="b" * 40,
        service_api_key_pepper="c" * 40,
        result_download_signing_key="d" * 40,
        database_url="sqlite+aiosqlite:///tmp/test.db",
        xiaozhi_api_url="https://xiaozhi.example.invalid/device/manual-add",
        xiaozhi_token="token",
        xiaozhi_jsessionid="session",
        minio_endpoint="minio:9000",
        minio_access_key="access",
        minio_secret_key="secret",
        minio_bucket="bucket",
        llm_proxy_api_key="proxy-key",
        auth_cookie_secure=False,
    )
    assert settings.auth_cookie_secure is False


def test_alembic_url_preserves_database_password():
    settings = Settings(
        database_url=None,
        db_host="database.example",
        db_name="example",
        db_user="root",
        db_password="password-with-%-and-@",
    )

    assert "password-with-%25-and-%40" in settings.alembic_url
    assert "***" not in settings.alembic_url


def test_production_rejects_example_placeholders():
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            app_secret_key="generate-a-random-secret-with-at-least-32-bytes",
            database_url=None,
            db_password="replace-with-database-password",
            xiaozhi_api_url="https://replace-with-environment-url/device/manual-add",
            xiaozhi_token="replace-with-environment-token",
            xiaozhi_jsessionid="replace-with-environment-session-id",
            model_credential_encryption_key="replace-with-model-key-that-is-at-least-32-bytes",
            service_api_key_pepper="replace-with-api-pepper-that-is-at-least-32-bytes",
            result_download_signing_key="replace-with-download-key-at-least-32-bytes",
        )
    message = str(exc.value)
    for field in (
        "APP_SECRET_KEY",
        "DB_PASSWORD",
        "XIAOZHI_API_URL",
        "XIAOZHI_TOKEN",
        "XIAOZHI_JSESSIONID",
        "MODEL_CREDENTIAL_ENCRYPTION_KEY",
        "SERVICE_API_KEY_PEPPER",
        "RESULT_DOWNLOAD_SIGNING_KEY",
    ):
        assert field in message


def test_worker_and_media_settings_are_bounded():
    settings = Settings(
        worker_poll_interval_seconds=0.5,
        worker_lease_seconds=120,
        worker_lease_renew_seconds=30,
        worker_max_attempts=3,
        worker_batch_size=4,
        worker_max_concurrency=4,
        ai_result_retention_days=7,
        ai_result_download_ttl_seconds=600,
        max_ai_audio_bytes=20 * 1024 * 1024,
        max_ai_image_bytes=10 * 1024 * 1024,
        max_ai_prompt_chars=4000,
    )

    assert settings.worker_lease_renew_seconds < settings.worker_lease_seconds
    assert settings.ai_task_input_prefix == "tasks/input"
    assert settings.ai_task_result_prefix == "tasks/result"

    with pytest.raises(ValidationError):
        Settings(worker_lease_seconds=30, worker_lease_renew_seconds=30)
