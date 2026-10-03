from fastapi.testclient import TestClient

from app.main import create_app

SERVICE_PAYLOAD = {
    "serviceCode": "museum-a",
    "serviceName": "示例展馆小智服务",
    "digitalHumanName": "示例展馆数字人",
    "title": "欢迎来到示例展馆",
    "subtitle": "请向数字人提问",
    "questions": ["开放时间是什么？"],
    "voiceWakeupEnabled": True,
    "wakeWord": "你好小智",
    "wakeListeningTexts": ["你好小智"],
    "wakeRequirementCount": 1,
    "agentName": "示例展馆设备",
    "agentId": "0123456789abcdef0123456789abcdef",
    "deviceEnabled": True,
}

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
MP4_HEADER = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"


def login(client: TestClient) -> str:
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "admin", "password": "development-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def create_bindings(client: TestClient, csrf: str) -> tuple[int, int]:
    qa_table = client.post(
        "/api/admin/qa-tables",
        headers={"X-CSRF-Token": csrf},
        json={"name": "museum-qa", "description": "测试固定问答"},
    )
    assert qa_table.status_code == 201, qa_table.text
    llm = client.post(
        "/api/admin/ai-models/llm",
        headers={"X-CSRF-Token": csrf},
        json={
            "modelName": "示例展馆大模型",
            "modelCode": "museum-llm",
            "provider": "openai",
            "baseUrl": "https://llm.example.test/v1",
            "upstreamModel": "demo-model",
            "apiKey": "app-test-key-1234567890",
        },
    )
    assert llm.status_code == 201, llm.text
    return qa_table.json()["id"], llm.json()["id"]


def test_xiaozhi_service_draft_publish_and_public_config():
    with TestClient(create_app()) as client:
        csrf = login(client)
        qa_table_id, llm_model_id = create_bindings(client, csrf)
        payload = {
            **SERVICE_PAYLOAD,
            "qaTableId": qa_table_id,
            "llmModelId": llm_model_id,
        }
        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert created.status_code == 201, created.text
        service_id = created.json()["id"]
        assert created.json()["published"] is False
        assert created.json()["serviceName"] == "示例展馆小智服务"
        assert created.json()["digitalHumanName"] == "示例展馆数字人"
        assert created.json()["agentName"] == "示例展馆设备"
        assert created.json()["llmConfigured"] is True
        assert created.json()["llmProvider"] == "openai"
        assert "apiKey" not in created.text

        unavailable = client.get(
            "/api/xiaozhi-services/config",
            params={"serviceName": SERVICE_PAYLOAD["serviceName"]},
        )
        assert unavailable.status_code == 404

        published = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/publish",
            headers={"X-CSRF-Token": csrf},
        )
        assert published.status_code == 200, published.text
        assert published.json()["published"] is True

        names = client.get("/api/xiaozhi-services")
        assert names.status_code == 200, names.text
        assert names.json() == {"serviceNames": [SERVICE_PAYLOAD["serviceName"]]}

        config = client.get(
            "/api/xiaozhi-services/config",
            params={"serviceName": f"  {SERVICE_PAYLOAD['serviceName'].upper()}  "},
        )
        assert config.status_code == 200, config.text
        body = config.json()
        assert "serviceCode" not in body
        assert body["serviceName"] == SERVICE_PAYLOAD["serviceName"]
        assert body["agentId"] == SERVICE_PAYLOAD["agentId"]
        assert body["agentName"] == SERVICE_PAYLOAD["agentName"]
        assert body["digitalHumanName"] == "示例展馆数字人"
        for field in (
            "backgroundIconUrl",
            "wakeIconUrl",
            "menuBackgroundUrl",
            "keyboardIconUrl",
            "voiceIconUrl",
            "homeIconUrl",
            "holdToTalkBackgroundUrl",
            "sendIconUrl",
            "standingVideoUrl",
            "thinkingVideoUrl",
            "speakingVideoUrl",
        ):
            assert body[field] is None
        assert client.get("/api/xiaozhi-services/museum-a/config").status_code == 404


def test_xiaozhi_service_list_uses_new_route_and_old_routes_are_removed():
    with TestClient(create_app()) as client:
        csrf = login(client)
        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json=SERVICE_PAYLOAD,
        )
        assert created.status_code == 201, created.text

        response = client.get("/api/admin/xiaozhi-services?page=1&page_size=20")
        assert response.status_code == 200, response.text
        assert response.json()["pageSize"] == 20
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["serviceCode"] == "museum-a"
        assert response.json()["items"][0]["digitalHumanName"] == "示例展馆数字人"

        assert client.get("/api/admin/projects").status_code == 404
        assert client.get("/api/projects/museum-a/config").status_code == 404


def test_xiaozhi_service_rejects_invalid_image_and_unknown_bindings():
    with TestClient(create_app()) as client:
        csrf = login(client)
        invalid_binding = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json={**SERVICE_PAYLOAD, "llmModelId": 99999},
        )
        assert invalid_binding.status_code == 404

        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json=SERVICE_PAYLOAD,
        )
        service_id = created.json()["id"]
        proxied_upload = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/assets/background_icon",
            headers={
                "X-CSRF-Token": csrf,
                "Origin": "http://localhost:5173",
                "Host": "127.0.0.1:8000",
            },
            files={"file": ("background.jpg", b"\xff\xd8\xff\xe0test", "image/jpeg")},
        )
        assert proxied_upload.status_code == 200, proxied_upload.text

        invalid = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/assets/background_icon",
            headers={"X-CSRF-Token": csrf},
            files={"file": ("x.svg", b"<svg>", "image/svg+xml")},
        )
        assert invalid.status_code == 415


def test_xiaozhi_service_uploads_and_proxies_optional_video():
    with TestClient(create_app()) as client:
        csrf = login(client)
        qa_table_id, llm_model_id = create_bindings(client, csrf)
        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json={
                **SERVICE_PAYLOAD,
                "qaTableId": qa_table_id,
                "llmModelId": llm_model_id,
            },
        )
        service_id = created.json()["id"]
        uploaded = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/assets/standing_video",
            headers={"X-CSRF-Token": csrf},
            files={"file": ("standing.mp4", MP4_HEADER, "video/mp4")},
        )
        assert uploaded.status_code == 200, uploaded.text
        asset = uploaded.json()["asset"]
        assert asset["slot"] == "standing_video"
        assert asset["contentType"] == "video/mp4"

        invalid = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/assets/thinking_video",
            headers={"X-CSRF-Token": csrf},
            files={"file": ("thinking.mp4", b"not-a-video", "video/mp4")},
        )
        assert invalid.status_code == 415

        published = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/publish",
            headers={"X-CSRF-Token": csrf},
        )
        assert published.status_code == 200, published.text
        config = client.get(
            "/api/xiaozhi-services/config",
            params={"serviceName": SERVICE_PAYLOAD["serviceName"]},
        )
        assert config.status_code == 200, config.text
        body = config.json()
        assert body["standingVideoUrl"].startswith(
            "http://testserver/api/xiaozhi-service-assets/"
        )
        assert body["thinkingVideoUrl"] is None
        assert body["speakingVideoUrl"] is None

        proxied = client.get(body["standingVideoUrl"])
        assert proxied.status_code == 200
        assert proxied.headers["content-type"] == "video/mp4"
        assert proxied.content == MP4_HEADER


def test_publish_rejects_disabled_llm_model():
    with TestClient(create_app()) as client:
        csrf = login(client)
        qa_table_id, llm_model_id = create_bindings(client, csrf)
        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json={
                **SERVICE_PAYLOAD,
                "qaTableId": qa_table_id,
                "llmModelId": llm_model_id,
            },
        )
        service_id = created.json()["id"]
        disabled = client.put(
            f"/api/admin/ai-models/llm/{llm_model_id}/status",
            headers={"X-CSRF-Token": csrf},
            json={"enabled": False},
        )
        assert disabled.json()["affectedServiceCount"] == 1

        published = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/publish",
            headers={"X-CSRF-Token": csrf},
        )
        assert published.status_code == 409
        assert "已启用的大语言模型" in published.json()["message"]

        archived = client.delete(
            f"/api/admin/ai-models/llm/{llm_model_id}",
            headers={"X-CSRF-Token": csrf},
        )
        assert archived.status_code == 409
        assert "不能归档" in archived.json()["message"]


def test_xiaozhi_service_can_publish_without_qa_table():
    with TestClient(create_app()) as client:
        csrf = login(client)
        llm = client.post(
            "/api/admin/ai-models/llm",
            headers={"X-CSRF-Token": csrf},
            json={
                "modelName": "无问答发布模型",
                "modelCode": "no-qa-publish-llm",
                "provider": "openai",
                "baseUrl": "https://llm.example.test/v1",
                "upstreamModel": "demo-model",
                "apiKey": "app-test-key-1234567890",
            },
        )
        assert llm.status_code == 201, llm.text
        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json={**SERVICE_PAYLOAD, "llmModelId": llm.json()["id"]},
        )
        assert created.status_code == 201, created.text
        assert created.json()["qaTableId"] is None
        published = client.post(
            f"/api/admin/xiaozhi-services/{created.json()['id']}/publish",
            headers={"X-CSRF-Token": csrf},
        )
        assert published.status_code == 200, published.text


def test_ai_disabled_service_publishes_without_llm_model():
    with TestClient(create_app()) as client:
        csrf = login(client)
        qa_table = client.post(
            "/api/admin/qa-tables",
            headers={"X-CSRF-Token": csrf},
            json={"name": "qa-no-llm", "description": "纯问答模式"},
        )
        assert qa_table.status_code == 201, qa_table.text
        payload = {
            **SERVICE_PAYLOAD,
            "serviceCode": "no-llm-service",
            "qaTableId": qa_table.json()["id"],
            "aiReplyEnabled": False,
        }
        created = client.post(
            "/api/admin/xiaozhi-services",
            headers={"X-CSRF-Token": csrf},
            json=payload,
        )
        assert created.status_code == 201, created.text
        service_id = created.json()["id"]
        assert created.json()["aiReplyEnabled"] is False
        assert created.json()["defaultReplyText"] is None

        rejected = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/publish",
            headers={"X-CSRF-Token": csrf},
        )
        assert rejected.status_code == 409
        assert "默认回复词" in rejected.json()["message"]

        update_payload = {
            key: value for key, value in payload.items() if key != "serviceCode"
        }
        updated = client.put(
            f"/api/admin/xiaozhi-services/{service_id}",
            headers={"X-CSRF-Token": csrf},
            json={**update_payload, "defaultReplyText": "  这个问题我还需要学习  "},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["defaultReplyText"] == "这个问题我还需要学习"

        published = client.post(
            f"/api/admin/xiaozhi-services/{service_id}/publish",
            headers={"X-CSRF-Token": csrf},
        )
        assert published.status_code == 200, published.text
        assert published.json()["published"] is True
