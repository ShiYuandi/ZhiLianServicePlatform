from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_result_download_token
from app.main import create_app
from app.models.ai_task import AITask
from app.models.frontend_ai_service import FrontendAIService


class FakeStorage:
    async def get(self, object_key: str):
        return (b"fake-png-bytes", "image/png", "etag")


def _make_task(service_id: int) -> AITask:
    now = datetime.now(timezone.utc)
    return AITask(
        id=str(uuid.uuid4()),
        service_id=service_id,
        task_type="image_generation",
        status="succeeded",
        result_object_key="tasks/result/demo.png",
        completed_at=now,
        result_expires_at=now + timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_image_result_downloads_with_signed_token_only(db, monkeypatch):
    """二维码等场景无法附加 Bearer 头，签名令牌本身即下载凭证。"""

    service = FrontendAIService(
        service_name="下载服务",
        service_code="svc-download-demo",
        enabled=True,
        api_key_hash="0" * 64,
        api_key_prefix="dhs_test",
        api_key_suffix="test",
        api_key_version=1,
        allowed_origins=[],
    )
    db.add(service)
    await db.flush()
    task = _make_task(service.id)
    db.add(task)
    await db.commit()

    monkeypatch.setattr(
        "app.api.ai_services.get_object_storage", lambda *args, **kwargs: FakeStorage()
    )
    settings = get_settings()
    token = create_result_download_token(
        task.id, task.result_object_key, task.result_expires_at, settings
    )

    with TestClient(create_app()) as client:
        ok = client.get(
            f"/api/v1/ai-services/svc-download-demo/image-results/{task.id}?token={token}"
        )
        assert ok.status_code == 200, ok.text
        assert ok.content == b"fake-png-bytes"
        assert ok.headers["content-type"].startswith("image/png")

        bad = client.get(
            f"/api/v1/ai-services/svc-download-demo/image-results/{task.id}?token=bad-token"
        )
        assert bad.status_code == 401

        other = _make_task(service.id)
        db.add(other)
        await db.commit()
        mismatched = client.get(
            f"/api/v1/ai-services/svc-download-demo/image-results/{other.id}?token={token}"
        )
        assert mismatched.status_code == 401


@pytest.mark.asyncio
async def test_image_result_rejects_expired_token(db, monkeypatch):
    service = FrontendAIService(
        service_name="过期服务",
        service_code="svc-expired-demo",
        enabled=True,
        api_key_hash="0" * 64,
        api_key_prefix="dhs_test",
        api_key_suffix="test",
        api_key_version=1,
        allowed_origins=[],
    )
    db.add(service)
    await db.flush()
    task = _make_task(service.id)
    task.result_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.add(task)
    await db.commit()

    monkeypatch.setattr(
        "app.api.ai_services.get_object_storage", lambda *args, **kwargs: FakeStorage()
    )
    token = create_result_download_token(
        task.id, task.result_object_key, task.result_expires_at, get_settings()
    )

    with TestClient(create_app()) as client:
        response = client.get(
            f"/api/v1/ai-services/svc-expired-demo/image-results/{task.id}?token={token}"
        )
        assert response.status_code == 401
