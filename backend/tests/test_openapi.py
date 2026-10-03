import re

from app.main import app


CHINESE = re.compile(r"[\u4e00-\u9fff]")

EXPECTED_OPERATIONS = {
    ("GET", "/health"),
    ("POST", "/api/device/add"),
    ("GET", "/api/tables/{table_name}/download"),
    ("POST", "/api/admin/auth/login"),
    ("POST", "/api/admin/auth/logout"),
    ("GET", "/api/admin/auth/me"),
    ("PUT", "/api/admin/auth/password"),
    ("GET", "/api/admin/dashboard"),
    ("GET", "/api/admin/qa-tables"),
    ("POST", "/api/admin/qa-tables"),
    ("PUT", "/api/admin/qa-tables/{table_id}"),
    ("DELETE", "/api/admin/qa-tables/{table_id}"),
    ("GET", "/api/admin/qa-tables/{table_id}/items"),
    ("POST", "/api/admin/qa-tables/{table_id}/items"),
    ("PUT", "/api/admin/qa-items/{item_id}"),
    ("DELETE", "/api/admin/qa-items/{item_id}"),
    ("POST", "/api/admin/qa-tables/{table_id}/items/batch"),
    ("POST", "/api/admin/qa-tables/{table_id}/import"),
    ("GET", "/api/admin/qa-tables/{table_id}/export"),
    ("GET", "/api/admin/xiaozhi-services"),
    ("POST", "/api/admin/xiaozhi-services"),
    ("GET", "/api/admin/xiaozhi-services/{service_id}"),
    ("PUT", "/api/admin/xiaozhi-services/{service_id}"),
    ("DELETE", "/api/admin/xiaozhi-services/{service_id}"),
    ("POST", "/api/admin/xiaozhi-services/{service_id}/publish"),
    ("POST", "/api/admin/xiaozhi-services/{service_id}/unpublish"),
    ("POST", "/api/admin/xiaozhi-services/{service_id}/assets/{slot}"),
    ("DELETE", "/api/admin/xiaozhi-services/{service_id}/assets/{slot}"),
    ("GET", "/api/xiaozhi-services"),
    ("GET", "/api/xiaozhi-services/config"),
    ("GET", "/api/xiaozhi-service-assets/{asset_id}"),
    ("POST", "/v1/chat/completions"),
    ("GET", "/api/admin/ai-models/llm"),
    ("POST", "/api/admin/ai-models/llm"),
    ("GET", "/api/admin/ai-models/llm/{model_id}"),
    ("PUT", "/api/admin/ai-models/llm/{model_id}"),
    ("DELETE", "/api/admin/ai-models/llm/{model_id}"),
    ("PUT", "/api/admin/ai-models/llm/{model_id}/status"),
    ("POST", "/api/admin/ai-models/llm/{model_id}/test-connection"),
    ("GET", "/api/admin/ai-models/speech-recognition"),
    ("POST", "/api/admin/ai-models/speech-recognition"),
    ("GET", "/api/admin/ai-models/speech-recognition/{model_id}"),
    ("PUT", "/api/admin/ai-models/speech-recognition/{model_id}"),
    ("DELETE", "/api/admin/ai-models/speech-recognition/{model_id}"),
    ("PUT", "/api/admin/ai-models/speech-recognition/{model_id}/status"),
    ("POST", "/api/admin/ai-models/speech-recognition/{model_id}/test-connection"),
    ("GET", "/api/admin/ai-models/image-generation"),
    ("POST", "/api/admin/ai-models/image-generation"),
    ("GET", "/api/admin/ai-models/image-generation/{model_id}"),
    ("PUT", "/api/admin/ai-models/image-generation/{model_id}"),
    ("DELETE", "/api/admin/ai-models/image-generation/{model_id}"),
    ("PUT", "/api/admin/ai-models/image-generation/{model_id}/status"),
    ("POST", "/api/admin/ai-models/image-generation/{model_id}/test-connection"),
    ("GET", "/api/admin/frontend-ai-services"),
    ("POST", "/api/admin/frontend-ai-services"),
    ("GET", "/api/admin/frontend-ai-services/{service_id}"),
    ("PUT", "/api/admin/frontend-ai-services/{service_id}"),
    ("DELETE", "/api/admin/frontend-ai-services/{service_id}"),
    ("POST", "/api/admin/frontend-ai-services/{service_id}/rotate-api-key"),
    ("GET", "/api/v1/ai-services/{service_code}"),
    ("POST", "/api/v1/ai-services/{service_code}/speech-tasks"),
    ("POST", "/api/v1/ai-services/{service_code}/image-tasks"),
    ("GET", "/api/v1/ai-services/{service_code}/tasks/{task_id}"),
    ("GET", "/api/v1/ai-services/{service_code}/image-results/{task_id}"),
    ("GET", "/api/external-proxies/{proxy_uuid}"),
    ("POST", "/api/external-proxies/{proxy_uuid}"),
    ("PUT", "/api/external-proxies/{proxy_uuid}"),
    ("PATCH", "/api/external-proxies/{proxy_uuid}"),
    ("DELETE", "/api/external-proxies/{proxy_uuid}"),
    ("GET", "/api/admin/external-api-proxies"),
    ("POST", "/api/admin/external-api-proxies"),
    ("PUT", "/api/admin/external-api-proxies/{proxy_uuid}"),
    ("DELETE", "/api/admin/external-api-proxies/{proxy_uuid}"),
}


def operation(schema: dict, method: str, path: str) -> dict:
    return schema["paths"][path][method.lower()]


def test_openapi_paths_and_methods_are_unchanged():
    schema = app.openapi()
    actual = {
        (method.upper(), path)
        for path, methods in schema["paths"].items()
        for method in methods
        if method.upper() in {"GET", "POST", "PUT", "DELETE", "PATCH"}
    }
    assert actual == EXPECTED_OPERATIONS


def test_openapi_has_chinese_groups_and_chinese_operation_text():
    schema = app.openapi()
    assert {tag["name"] for tag in schema["tags"]} == {
        "系统状态",
        "前端公开接口",
        "管理员认证",
        "后台概览",
        "问答管理",
        "小智中间件服务",
        "大模型代理",
        "大语言模型管理",
        "语音识别模型管理",
        "图像生成模型管理",
        "前端 AI 服务管理",
        "外部接口代理管理",
    }
    assert all(CHINESE.search(tag["description"]) for tag in schema["tags"])

    for method, path in EXPECTED_OPERATIONS:
        item = operation(schema, method, path)
        assert CHINESE.search(item["summary"]), f"{method} {path} 缺少中文标题"
        assert CHINESE.search(item["description"]), f"{method} {path} 缺少中文说明"
        assert all(CHINESE.search(tag) for tag in item["tags"])
        assert all(
            CHINESE.search(response["description"])
            for response in item["responses"].values()
        ), f"{method} {path} 存在缺少中文说明的响应"


def test_openapi_parameters_have_chinese_descriptions():
    schema = app.openapi()
    for method, path in EXPECTED_OPERATIONS:
        for parameter in operation(schema, method, path).get("parameters", []):
            assert CHINESE.search(parameter.get("description", "")), (
                f"{method} {path} 的参数 {parameter['name']} 缺少中文说明"
            )

    import_schema = operation(schema, "POST", "/api/admin/qa-tables/{table_id}/import")
    upload_schema = import_schema["requestBody"]["content"]["multipart/form-data"][
        "schema"
    ]
    upload_schema = schema["components"]["schemas"][
        upload_schema["$ref"].split("/")[-1]
    ]
    assert CHINESE.search(upload_schema["properties"]["file"]["description"])


def test_request_models_have_chinese_field_descriptions_and_safe_examples():
    schema = app.openapi()
    models = schema["components"]["schemas"]
    for model_name in (
        "LoginRequest",
        "PasswordChangeRequest",
        "DeviceAddRequest",
        "QaTableCreate",
        "QaItemCreate",
        "QaBatchRequest",
        "XiaozhiServiceCreate",
        "XiaozhiServiceUpdate",
        "LLMOpenAIPayload",
        "LLMDifyPayload",
        "SpeechBaiduPayload",
        "SpeechVolcenginePayload",
        "ImageVolcenginePayload",
        "FrontendAIServiceCreate",
        "FrontendAIServiceUpdate",
    ):
        model = models[model_name]
        assert all(
            CHINESE.search(field.get("description", ""))
            for field in model["properties"].values()
        ), f"{model_name} 存在缺少中文说明的字段"

    assert models["DeviceAddRequest"]["example"] == {
        "name": "演示设备",
        "board": "esp32",
        "appVersion": "1.0.0",
        "macAddress": "00:11:22:33:44:55",
    }
    assert models["LoginRequest"]["example"] == {
        "username": "admin",
        "password": "示例密码，请替换",
    }


def test_excel_responses_are_documented_as_files_in_chinese():
    schema = app.openapi()
    for method, path in (
        ("GET", "/api/tables/{table_name}/download"),
        ("GET", "/api/admin/qa-tables/{table_id}/export"),
    ):
        response = operation(schema, method, path)["responses"]["200"]
        assert CHINESE.search(response["description"])
        assert (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in (response["content"])
        )
