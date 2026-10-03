from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_result_download_token,
    decode_result_download_token,
    decrypt_model_credential,
    encrypt_model_credential,
    generate_service_api_key,
    hash_service_api_key,
    service_api_key_hint,
    verify_service_api_key,
)


def settings(**overrides) -> Settings:
    values = {
        "model_credential_encryption_key": "model-key-used-only-for-tests-32-bytes",
        "service_api_key_pepper": "service-pepper-used-only-for-tests-32-bytes",
        "result_download_signing_key": "download-key-used-only-for-tests-32-bytes",
    }
    values.update(overrides)
    return Settings(**values)


def test_model_credential_round_trip_uses_versioned_ciphertext():
    config = settings()

    encrypted = encrypt_model_credential("provider-secret", config)

    assert encrypted.startswith("v1:")
    assert "provider-secret" not in encrypted
    assert decrypt_model_credential(encrypted, config) == "provider-secret"


def test_model_credential_rejects_wrong_key_and_unknown_version():
    encrypted = encrypt_model_credential("provider-secret", settings())

    with pytest.raises(AppError) as wrong_key:
        decrypt_model_credential(
            encrypted,
            settings(
                model_credential_encryption_key="a-different-model-key-for-tests-32-bytes"
            ),
        )
    assert wrong_key.value.code == "MODEL_CREDENTIAL_INVALID"

    with pytest.raises(AppError) as unknown_version:
        decrypt_model_credential("v2:not-supported", settings())
    assert unknown_version.value.code == "MODEL_CREDENTIAL_INVALID"


def test_model_credential_can_be_read_with_previous_key_during_rotation():
    old_settings = settings(
        model_credential_encryption_key="old-model-key-used-only-for-tests-32-bytes"
    )
    encrypted = encrypt_model_credential("provider-secret", old_settings)

    rotating_settings = settings(
        model_credential_encryption_key="new-model-key-used-only-for-tests-32-bytes",
        model_credential_previous_encryption_key=(
            "old-model-key-used-only-for-tests-32-bytes"
        ),
    )

    assert decrypt_model_credential(encrypted, rotating_settings) == "provider-secret"


def test_service_api_key_is_high_entropy_and_only_hash_is_verified():
    config = settings()

    first = generate_service_api_key()
    second = generate_service_api_key()
    digest = hash_service_api_key(first, config)

    assert first.startswith("dhs_")
    assert len(first) >= 48
    assert first != second
    assert first not in digest
    assert verify_service_api_key(first, digest, config)
    assert not verify_service_api_key(second, digest, config)
    assert first not in service_api_key_hint(first)


def test_result_download_token_contains_task_and_object_and_expires():
    config = settings(ai_result_download_ttl_seconds=600)
    result_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    token = create_result_download_token(
        "task-123", "tasks/result/task-123.png", result_expires_at, config
    )

    assert decode_result_download_token(token, config) == (
        "task-123",
        "tasks/result/task-123.png",
    )

    expired = create_result_download_token(
        "task-123",
        "tasks/result/task-123.png",
        datetime.now(timezone.utc) - timedelta(seconds=1),
        config,
    )
    with pytest.raises(AppError) as exc:
        decode_result_download_token(expired, config)
    assert exc.value.code == "RESULT_LINK_INVALID"
