from fastapi.testclient import TestClient

from app.main import create_app


def login(client: TestClient) -> str:
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "admin", "password": "development-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def create_speech_model(client: TestClient, csrf: str, *, configured: bool = True):
    payload = {
        "modelName": "百度语音",
        "modelCode": "baidu-asr",
        "provider": "baidu",
        "appId": "baidu-app",
        "devPid": 1537,
    }
    if configured:
        payload.update({"apiKey": "baidu-api-key", "secretKey": "baidu-secret-key"})
    response = client.post(
        "/api/admin/ai-models/speech-recognition",
        headers={"X-CSRF-Token": csrf},
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_image_model(client: TestClient, csrf: str):
    response = client.post(
        "/api/admin/ai-models/image-generation",
        headers={"X-CSRF-Token": csrf},
        json={
            "modelName": "Seedream",
            "modelCode": "seedream-main",
            "provider": "volcengine",
            "apiUrl": "https://ark.example.test/api/v3/images/generations",
            "apiKey": "seedream-api-key",
            "upstreamModel": "seedream-model-id",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def service_payload(speech_id: int | None, image_id: int | None, **overrides):
    payload = {
        "serviceName": "展厅前端 AI 服务",
        "enabled": False,
        "remark": "供展厅数字人前端使用",
        "rateLimitPerMinute": 60,
        "maxInflightTasks": 3,
        "allowedOrigins": ["https://hall.example.com"],
        "speechModelId": speech_id,
        "imageModelId": image_id,
    }
    payload.update(overrides)
    return payload


def service_update_payload(speech_id: int | None, image_id: int | None, **overrides):
    payload = service_payload(speech_id, image_id, **overrides)
    payload.pop("serviceCode", None)
    return payload


def test_frontend_ai_service_crud_returns_api_key_only_once_and_rotates_it():
    with TestClient(create_app()) as client:
        csrf = login(client)
        speech = create_speech_model(client, csrf)
        image = create_image_model(client, csrf)

        created = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(speech["id"], image["id"]),
        )
        assert created.status_code == 201, created.text
        body = created.json()
        service_id = body["id"]
        first_key = body["apiKey"]
        assert first_key.startswith("dhs_")
        assert body["apiKeyVersion"] == 1
        assert body["apiKeyHint"].startswith("dhs_")
        assert body["speechModelName"] == "百度语音"
        assert body["imageModelName"] == "Seedream"

        detail = client.get(f"/api/admin/frontend-ai-services/{service_id}")
        assert detail.status_code == 200, detail.text
        assert "apiKey" not in detail.json()
        assert first_key not in detail.text

        updated = client.put(
            f"/api/admin/frontend-ai-services/{service_id}",
            headers={"X-CSRF-Token": csrf},
            json=service_update_payload(
                speech["id"],
                image["id"],
                serviceName="展厅 AI 服务（更新）",
                enabled=True,
            ),
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["enabled"] is True
        assert updated.json()["serviceName"] == "展厅 AI 服务（更新）"
        assert "apiKey" not in updated.json()

        rotated = client.post(
            f"/api/admin/frontend-ai-services/{service_id}/rotate-api-key",
            headers={"X-CSRF-Token": csrf},
        )
        assert rotated.status_code == 200, rotated.text
        second_key = rotated.json()["apiKey"]
        assert second_key.startswith("dhs_")
        assert second_key != first_key
        assert rotated.json()["apiKeyVersion"] == 2

        listing = client.get("/api/admin/frontend-ai-services?page=1&page_size=20")
        assert listing.status_code == 200, listing.text
        assert listing.json()["total"] == 1
        assert listing.json()["items"][0]["serviceCode"].startswith("svc-")
        assert first_key not in listing.text
        assert second_key not in listing.text


def test_service_code_is_generated_and_cannot_be_changed():
    with TestClient(create_app()) as client:
        csrf = login(client)
        first = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(None, None),
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(None, None, serviceName="重复服务"),
        )
        assert second.status_code == 201, second.text
        assert first.json()["serviceCode"].startswith("svc-")
        assert second.json()["serviceCode"].startswith("svc-")
        assert first.json()["serviceCode"] != second.json()["serviceCode"]

        changed = client.put(
            f"/api/admin/frontend-ai-services/{first.json()['id']}",
            headers={"X-CSRF-Token": csrf},
            json={**service_payload(None, None), "serviceCode": "changed-code"},
        )
        assert changed.status_code == 422


def test_enabling_service_requires_enabled_models_with_complete_credentials():
    with TestClient(create_app()) as client:
        csrf = login(client)
        speech = create_speech_model(client, csrf, configured=False)
        created = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(speech["id"], None),
        )
        service_id = created.json()["id"]

        enabled = client.put(
            f"/api/admin/frontend-ai-services/{service_id}",
            headers={"X-CSRF-Token": csrf},
            json=service_update_payload(speech["id"], None, enabled=True),
        )
        assert enabled.status_code == 409
        assert "凭据未完整配置" in enabled.json()["message"]


def test_bound_models_cannot_be_archived_until_service_is_unbound():
    with TestClient(create_app()) as client:
        csrf = login(client)
        speech = create_speech_model(client, csrf)
        image = create_image_model(client, csrf)
        service = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(speech["id"], image["id"]),
        ).json()

        disabled = client.put(
            f"/api/admin/ai-models/speech-recognition/{speech['id']}/status",
            headers={"X-CSRF-Token": csrf},
            json={"enabled": False},
        )
        assert disabled.status_code == 200, disabled.text
        assert disabled.json()["affectedServiceCount"] == 1

        blocked = client.delete(
            f"/api/admin/ai-models/speech-recognition/{speech['id']}",
            headers={"X-CSRF-Token": csrf},
        )
        assert blocked.status_code == 409
        assert "前端 AI 服务绑定" in blocked.json()["message"]
        image_blocked = client.delete(
            f"/api/admin/ai-models/image-generation/{image['id']}",
            headers={"X-CSRF-Token": csrf},
        )
        assert image_blocked.status_code == 409
        assert "前端 AI 服务绑定" in image_blocked.json()["message"]

        unbound = client.put(
            f"/api/admin/frontend-ai-services/{service['id']}",
            headers={"X-CSRF-Token": csrf},
            json=service_update_payload(None, None),
        )
        assert unbound.status_code == 200, unbound.text
        archived = client.delete(
            f"/api/admin/ai-models/speech-recognition/{speech['id']}",
            headers={"X-CSRF-Token": csrf},
        )
        assert archived.status_code == 200, archived.text
        image_archived = client.delete(
            f"/api/admin/ai-models/image-generation/{image['id']}",
            headers={"X-CSRF-Token": csrf},
        )
        assert image_archived.status_code == 200, image_archived.text


def test_archived_or_missing_model_cannot_be_bound_and_service_archive_is_safe():
    with TestClient(create_app()) as client:
        csrf = login(client)
        speech = create_speech_model(client, csrf)
        archived = client.delete(
            f"/api/admin/ai-models/speech-recognition/{speech['id']}",
            headers={"X-CSRF-Token": csrf},
        )
        assert archived.status_code == 200

        invalid = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(speech["id"], None),
        )
        assert invalid.status_code == 404
        assert "语音识别模型不存在" in invalid.json()["message"]

        created = client.post(
            "/api/admin/frontend-ai-services",
            headers={"X-CSRF-Token": csrf},
            json=service_payload(None, None),
        )
        service_id = created.json()["id"]
        deleted = client.delete(
            f"/api/admin/frontend-ai-services/{service_id}",
            headers={"X-CSRF-Token": csrf},
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["message"] == "前端 AI 服务已归档"
        assert (
            client.get(f"/api/admin/frontend-ai-services/{service_id}").status_code
            == 404
        )
