from __future__ import annotations

from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import external_api_proxy


def login(client: TestClient) -> str:
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "admin", "password": "development-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def test_external_proxy_creates_uuid_and_forwards_request_raw():
    captured: dict[str, object] = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, method, url, **kwargs):
            captured.update(method=method, url=url, **kwargs)
            return httpx.Response(
                207,
                headers={"content-type": "application/json", "x-upstream": "ok"},
                content=b'{"from":"upstream"}',
            )

    with patch.object(
        external_api_proxy.httpx, "AsyncClient", lambda **_kwargs: FakeClient()
    ):
        with TestClient(create_app()) as client:
            csrf = login(client)
            created = client.post(
                "/api/admin/external-api-proxies",
                headers={"X-CSRF-Token": csrf},
                json={
                    "targetUrl": "https://example.test/api/v1/getFyTagList",
                    "enabled": True,
                },
            )
            assert created.status_code == 201, created.text
            proxy_uuid = created.json()["proxyUuid"]
            assert len(proxy_uuid) == 36

            response = client.post(
                f"/api/external-proxies/{proxy_uuid}?page=1&tag=x",
                headers={"appId": "demo-app", "X-Trace": "trace-1"},
                content=b"request-body",
            )

    assert response.status_code == 207
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-upstream"] == "ok"
    assert response.content == b'{"from":"upstream"}'
    assert captured["method"] == "POST"
    assert captured["url"] == "https://example.test/api/v1/getFyTagList"
    assert captured["content"] == b"request-body"
    assert ("page", "1") in captured["params"]
    assert ("tag", "x") in captured["params"]
    forwarded = dict(captured["headers"])
    assert forwarded["appid"] == "demo-app"
    assert forwarded["x-trace"] == "trace-1"
    assert "cookie" not in forwarded


def test_external_proxy_rejects_invalid_target_url():
    with TestClient(create_app()) as client:
        csrf = login(client)
        response = client.post(
            "/api/admin/external-api-proxies",
            headers={"X-CSRF-Token": csrf},
            json={"targetUrl": "file:///etc/passwd", "enabled": True},
        )
    assert response.status_code == 422
