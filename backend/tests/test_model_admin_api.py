from fastapi.testclient import TestClient

from app.main import create_app


def login(client: TestClient) -> str:
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "admin", "password": "development-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def test_llm_model_crud_masks_credentials_and_preserves_blank_secret():
    with TestClient(create_app()) as client:
        csrf = login(client)
        created = client.post(
            "/api/admin/ai-models/llm",
            headers={"X-CSRF-Token": csrf},
            json={
                "modelName": "OpenAI 主模型",
                "modelCode": "openai-main",
                "provider": "openai",
                "sortOrder": 10,
                "docUrl": "https://example.test/docs",
                "remark": "开发环境",
                "enabled": True,
                "baseUrl": "https://example.test/v1",
                "upstreamModel": "gpt-example",
                "apiKey": "secret-openai-key-123456",
                "timeoutSeconds": 35,
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        model_id = body["id"]
        assert body["provider"] == "openai"
        assert body["credentialConfigured"] is True
        assert body["apiKeyMasked"].startswith("secr")
        assert body["apiKeyMasked"].endswith("3456")
        assert "secret-openai-key-123456" not in created.text

        updated = client.put(
            f"/api/admin/ai-models/llm/{model_id}",
            headers={"X-CSRF-Token": csrf},
            json={
                "modelName": "OpenAI 主模型（更新）",
                "modelCode": "openai-main",
                "provider": "openai",
                "sortOrder": 20,
                "enabled": True,
                "baseUrl": "https://example.test/v1",
                "upstreamModel": "gpt-example-2",
                "apiKey": "   ",
                "timeoutSeconds": 40,
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["apiKeyMasked"] == body["apiKeyMasked"]
        assert updated.json()["modelName"] == "OpenAI 主模型（更新）"

        switched = client.put(
            f"/api/admin/ai-models/llm/{model_id}",
            headers={"X-CSRF-Token": csrf},
            json={
                "modelName": "Dify 主模型",
                "modelCode": "openai-main",
                "provider": "dify",
                "baseUrl": "https://dify.example.test/v1",
                "mode": "chat-messages",
                "apiKey": "dify-replacement-secret",
            },
        )
        assert switched.status_code == 200, switched.text
        assert switched.json()["provider"] == "dify"
        assert switched.json()["credentialConfigured"] is True
        assert "dify-replacement-secret" not in switched.text

        listing = client.get("/api/admin/ai-models/llm?page=1&page_size=20")
        assert listing.status_code == 200, listing.text
        assert listing.json()["pageSize"] == 20
        assert listing.json()["total"] == 1
        assert "apiKey" not in listing.text


def test_llm_model_provider_union_rejects_unrelated_fields():
    with TestClient(create_app()) as client:
        csrf = login(client)
        invalid = client.post(
            "/api/admin/ai-models/llm",
            headers={"X-CSRF-Token": csrf},
            json={
                "modelName": "混合配置",
                "modelCode": "mixed-config",
                "provider": "openai",
                "baseUrl": "https://example.test/v1",
                "upstreamModel": "gpt-example",
                "mode": "chat-messages",
            },
        )
        assert invalid.status_code == 422


def test_all_model_providers_can_be_created_and_are_safely_returned():
    cases = (
        (
            "/api/admin/ai-models/llm",
            {
                "modelName": "Dify 应用",
                "modelCode": "dify-main",
                "provider": "dify",
                "baseUrl": "https://dify.example.test/v1",
                "mode": "chat-messages",
                "apiKey": "dify-secret-key",
            },
        ),
        (
            "/api/admin/ai-models/speech-recognition",
            {
                "modelName": "百度语音",
                "modelCode": "baidu-asr",
                "provider": "baidu",
                "appId": "baidu-app",
                "apiKey": "baidu-api-key",
                "secretKey": "baidu-secret-key",
                "devPid": 1537,
            },
        ),
        (
            "/api/admin/ai-models/speech-recognition",
            {
                "modelName": "火山语音",
                "modelCode": "volc-asr",
                "provider": "volcengine",
                "appId": "volc-app",
                "accessToken": "volc-access-token",
                "resourceId": "volc-resource",
                "language": "zh-CN",
            },
        ),
        (
            "/api/admin/ai-models/image-generation",
            {
                "modelName": "Seedream",
                "modelCode": "seedream-main",
                "provider": "volcengine",
                "apiUrl": "https://ark.example.test/api/v3/images/generations",
                "apiKey": "seedream-api-key",
                "upstreamModel": "seedream-model-id",
                "defaultWidth": 1024,
                "defaultHeight": 1024,
                "timeoutSeconds": 120,
                "watermark": False,
            },
        ),
    )
    with TestClient(create_app()) as client:
        csrf = login(client)
        for path, payload in cases:
            response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
            assert response.status_code == 201, response.text
            assert response.json()["credentialConfigured"] is True
            for value in (
                payload.get("apiKey"),
                payload.get("secretKey"),
                payload.get("accessToken"),
            ):
                if value:
                    assert value not in response.text


def test_model_status_archive_constraints_and_connection_placeholder():
    with TestClient(create_app()) as client:
        csrf = login(client)
        created = client.post(
            "/api/admin/ai-models/llm",
            headers={"X-CSRF-Token": csrf},
            json={
                "modelName": "可归档模型",
                "modelCode": "archivable-llm",
                "provider": "openai",
                "baseUrl": "https://example.test/v1",
                "upstreamModel": "gpt-example",
                "apiKey": "provider-secret",
            },
        )
        model_id = created.json()["id"]

        disabled = client.put(
            f"/api/admin/ai-models/llm/{model_id}/status",
            headers={"X-CSRF-Token": csrf},
            json={"enabled": False},
        )
        assert disabled.status_code == 200, disabled.text
        assert disabled.json() == {
            "message": "大语言模型已停用",
            "enabled": False,
            "affectedServiceCount": 0,
        }

        test_result = client.post(
            f"/api/admin/ai-models/llm/{model_id}/test-connection",
            headers={"X-CSRF-Token": csrf},
        )
        assert test_result.status_code == 409
        assert "模型已停用" in test_result.json()["message"]

        archived = client.delete(
            f"/api/admin/ai-models/llm/{model_id}",
            headers={"X-CSRF-Token": csrf},
        )
        assert archived.status_code == 200, archived.text
        assert archived.json()["message"] == "大语言模型已归档"
        assert client.get(f"/api/admin/ai-models/llm/{model_id}").status_code == 404
