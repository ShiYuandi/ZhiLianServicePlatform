from fastapi.testclient import TestClient

from app.main import create_app


def test_admin_login_and_question_table_crud():
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/admin/auth/login",
            json={"username": "admin", "password": "development-password"},
        )
        assert login.status_code == 200, login.text
        csrf = login.json()["csrf_token"]
        unauthenticated = TestClient(create_app()).get("/api/admin/qa-tables")
        assert unauthenticated.status_code == 401
        created = client.post(
            "/api/admin/qa-tables",
            headers={"X-CSRF-Token": csrf},
            json={"name": "示例展馆", "description": "开发数据"},
        )
        assert created.status_code == 201, created.text
        table_id = created.json()["id"]
        item = client.post(
            f"/api/admin/qa-tables/{table_id}/items",
            headers={"X-CSRF-Token": csrf},
            json={"question": "瑞安在哪里？", "answer": "瑞安位于浙江温州。"},
        )
        assert item.status_code == 201, item.text
        listing = client.get(f"/api/admin/qa-tables/{table_id}/items")
        assert listing.json()["total"] == 1
        downloaded = client.get("/api/tables/示例展馆/download")
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"PK")


def test_admin_write_requires_csrf():
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/admin/auth/login",
            json={"username": "admin", "password": "development-password"},
        )
        response = client.post("/api/admin/qa-tables", json={"name": "无令牌"})
        assert response.status_code == 403
        assert response.json()["code"] == "CSRF_FAILED"

        untrusted = client.post(
            "/api/admin/qa-tables",
            headers={
                "X-CSRF-Token": login.json()["csrf_token"],
                "Origin": "https://evil.example",
                "Host": "127.0.0.1:8000",
            },
            json={"name": "不受信任来源"},
        )
        assert untrusted.status_code == 403
        assert untrusted.json()["message"] == "请求来源不受信任"
