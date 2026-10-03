from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.normalization import question_fingerprint
from app.core.security import encrypt_model_credential
from app.main import create_app
from app.models.device_mapping import DeviceMapping
from app.models.llm_model import LLMDifyConfig, LLMModel, LLMOpenAIConfig
from app.models.qa import QaItem, QaTable
from app.models.xiaozhi_service import XiaozhiMiddlewareService
from app.services.llm_upstream import UpstreamLLMClient
from app.services.llm_dify import DifyLLMClient


@pytest.mark.asyncio
async def test_fixed_answer_does_not_call_upstream(db):
    table = QaTable(name="proxy-table")
    table.items = [
        QaItem(
            question="你好",
            answer="固定答案",
            normalized_question="你好",
            question_fingerprint=question_fingerprint("你好"),
        )
    ]
    db.add(
        XiaozhiMiddlewareService(
            service_code="proxy-project",
            service_name="代理服务",
            title="代理",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            qa_table=table,
            device_mapping=DeviceMapping(name="设备", agent_id="a" * 32, enabled=True),
        )
    )
    await db.commit()
    get_settings().llm_proxy_api_key = "proxy"
    with patch.object(
        UpstreamLLMClient, "complete", new_callable=AsyncMock
    ) as upstream:
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "proxy-project",
                    "messages": [{"role": "user", "content": "  你好  "}],
                },
            )
    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "固定答案"
    upstream.assert_not_awaited()


@pytest.mark.asyncio
async def test_shared_llm_keeps_each_service_qa_table_independent(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    shared = LLMModel(
        model_name="复用模型",
        model_code="reused-llm",
        provider="openai",
        openai_config=LLMOpenAIConfig(
            base_url="https://example.test/v1",
            upstream_model="reused-model",
            api_key_encrypted=encrypt_model_credential("shared-key", settings),
        ),
    )

    def service(code: str, device: str, answer: str):
        table = QaTable(name=f"{code}-qa")
        table.items = [
            QaItem(
                question="同一个问题",
                answer=answer,
                normalized_question="同一个问题",
                question_fingerprint=question_fingerprint("同一个问题"),
            )
        ]
        return XiaozhiMiddlewareService(
            service_code=code,
            service_name=code,
            title=code,
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            qa_table=table,
            llm_model_config=shared,
            device_mapping=DeviceMapping(
                name=device, agent_id=("a" if code == "service-a" else "b") * 32
            ),
        )

    db.add_all(
        [
            service("service-a", "复用设备 A", "服务 A 的固定答案"),
            service("service-b", "复用设备 B", "服务 B 的固定答案"),
        ]
    )
    await db.commit()

    with TestClient(create_app()) as client:
        answers = []
        for code in ("service-a", "service-b"):
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": code,
                    "messages": [{"role": "user", "content": "同一个问题"}],
                },
            )
            assert response.status_code == 200, response.text
            answers.append(response.json()["choices"][0]["message"]["content"])
    assert answers == ["服务 A 的固定答案", "服务 B 的固定答案"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected_code", "expected_status"),
    [
        ("unbound", "LLM_MODEL_NOT_BOUND", 409),
        ("disabled", "LLM_MODEL_DISABLED", 503),
        ("archived", "LLM_MODEL_ARCHIVED", 503),
        ("missing-key", "LLM_CREDENTIAL_MISSING", 409),
    ],
)
async def test_proxy_rejects_unavailable_llm_with_stable_error(
    db, state, expected_code, expected_status
):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    model = None
    if state != "unbound":
        model = LLMModel(
            model_name="异常模型",
            model_code=f"error-{state}",
            provider="openai",
            enabled=state != "disabled",
            archived_at=(datetime.now(timezone.utc) if state == "archived" else None),
            openai_config=LLMOpenAIConfig(
                base_url="https://example.test/v1",
                upstream_model="example-model",
                api_key_encrypted=(
                    None
                    if state == "missing-key"
                    else encrypt_model_credential("provider-key", settings)
                ),
            ),
        )
    db.add(
        XiaozhiMiddlewareService(
            service_code=f"error-service-{state}",
            service_name="异常服务",
            title="异常服务",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            qa_table=QaTable(name=f"error-table-{state}"),
            llm_model_config=model,
            device_mapping=DeviceMapping(
                name=f"异常设备-{state}", agent_id="c" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer proxy"},
            json={
                "model": f"error-service-{state}",
                "messages": [{"role": "user", "content": "未命中问题"}],
                "stream": state == "disabled",
            },
        )
    assert response.status_code == expected_status, response.text
    assert response.json()["error"]["code"] == expected_code


@pytest.mark.asyncio
async def test_unmatched_question_uses_service_llm_config(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    db.add(
        XiaozhiMiddlewareService(
            service_code="configured-project",
            service_name="配置服务",
            title="配置",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            qa_table=QaTable(name="configured-table"),
            llm_model_config=LLMModel(
                model_name="共享 OpenAI 模型",
                model_code="shared-openai",
                provider="openai",
                openai_config=LLMOpenAIConfig(
                    base_url="https://service.example.test/v1",
                    upstream_model="service-model",
                    api_key_encrypted=encrypt_model_credential(
                        "service-secret", settings
                    ),
                    timeout_seconds=45,
                ),
            ),
            device_mapping=DeviceMapping(
                name="配置设备", agent_id="b" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    async def fake_complete(client, payload):
        assert client.base_url == "https://service.example.test/v1"
        assert client.model == "service-model"
        assert client.api_key == "service-secret"
        assert client.timeout_seconds == 45
        return {
            "id": "upstream-id",
            "object": "chat.completion",
            "created": 1,
            "model": "service-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "外部答案"},
                    "finish_reason": "stop",
                }
            ],
        }

    with patch.object(UpstreamLLMClient, "complete", new=fake_complete):
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "configured-project",
                    "messages": [{"role": "user", "content": "未命中问题"}],
                },
            )
    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "外部答案"


@pytest.mark.asyncio
async def test_service_without_qa_table_calls_openai_model(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    db.add(
        XiaozhiMiddlewareService(
            service_code="no-qa-openai",
            service_name="无问答 OpenAI 服务",
            title="无问答",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            llm_model_config=LLMModel(
                model_name="无问答模型",
                model_code="no-qa-openai-model",
                provider="openai",
                openai_config=LLMOpenAIConfig(
                    base_url="https://service.example.test/v1",
                    upstream_model="service-model",
                    api_key_encrypted=encrypt_model_credential("service-secret", settings),
                ),
            ),
            device_mapping=DeviceMapping(
                name="无问答设备", agent_id="e" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    async def fake_complete(client, payload):
        assert payload["messages"][-1]["content"] == "直接调用模型"
        return {
            "id": "upstream-id",
            "object": "chat.completion",
            "created": 1,
            "model": "service-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "模型答案"},
                    "finish_reason": "stop",
                }
            ],
        }

    with patch.object(UpstreamLLMClient, "complete", new=fake_complete):
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "no-qa-openai",
                    "messages": [{"role": "user", "content": "直接调用模型"}],
                },
            )
    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "模型答案"


@pytest.mark.asyncio
async def test_unmatched_question_uses_service_dify_config(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    db.add(
        XiaozhiMiddlewareService(
            service_code="dify-project",
            service_name="Dify 服务",
            title="Dify",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            qa_table=QaTable(name="dify-table"),
            llm_model_config=LLMModel(
                model_name="共享 Dify 模型",
                model_code="shared-dify",
                provider="dify",
                dify_config=LLMDifyConfig(
                    base_url="https://dify.example.test/v1",
                    mode="chat-messages",
                    api_key_encrypted=encrypt_model_credential("dify-key", settings),
                    timeout_seconds=50,
                ),
            ),
            device_mapping=DeviceMapping(
                name="Dify 设备", agent_id="c" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    async def fake_complete(client, question, service_code):
        assert client.base_url == "https://dify.example.test/v1"
        assert client.api_key == "dify-key"
        assert client.mode == "chat-messages"
        assert client.timeout_seconds == 50
        assert question == "未命中问题"
        assert service_code == "dify-project"
        return "Dify 答案"

    with patch.object(DifyLLMClient, "complete", new=fake_complete):
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "dify-project",
                    "messages": [{"role": "user", "content": "未命中问题"}],
                },
            )
    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "Dify 答案"


@pytest.mark.asyncio
async def test_service_without_qa_table_calls_dify_model(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    db.add(
        XiaozhiMiddlewareService(
            service_code="no-qa-dify",
            service_name="无问答 Dify 服务",
            title="无问答 Dify",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            llm_model_config=LLMModel(
                model_name="无问答 Dify 模型",
                model_code="no-qa-dify-model",
                provider="dify",
                dify_config=LLMDifyConfig(
                    base_url="https://dify.example.test/v1",
                    mode="chat-messages",
                    api_key_encrypted=encrypt_model_credential("dify-key", settings),
                ),
            ),
            device_mapping=DeviceMapping(
                name="无问答 Dify 设备", agent_id="f" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    async def fake_complete(client, question, service_code):
        assert question == "直接调用 Dify"
        assert service_code == "no-qa-dify"
        return "Dify 模型答案"

    with patch.object(DifyLLMClient, "complete", new=fake_complete):
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "no-qa-dify",
                    "messages": [{"role": "user", "content": "直接调用 Dify"}],
                },
            )
    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "Dify 模型答案"


@pytest.mark.asyncio
async def test_service_without_qa_table_streams_from_openai_model(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    db.add(
        XiaozhiMiddlewareService(
            service_code="no-qa-stream",
            service_name="无问答流式服务",
            title="无问答流式",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            llm_model_config=LLMModel(
                model_name="无问答流式模型",
                model_code="no-qa-stream-model",
                provider="openai",
                openai_config=LLMOpenAIConfig(
                    base_url="https://service.example.test/v1",
                    upstream_model="service-model",
                    api_key_encrypted=encrypt_model_credential("service-secret", settings),
                ),
            ),
            device_mapping=DeviceMapping(
                name="无问答流式设备", agent_id="1" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    async def fake_stream(client, payload):
        yield 'data: {"choices":[{"delta":{"content":"流式答案"}}]}\n\n'.encode()
        yield b"data: [DONE]\n\n"

    with patch.object(UpstreamLLMClient, "stream", new=fake_stream):
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "no-qa-stream",
                    "messages": [{"role": "user", "content": "流式问题"}],
                    "stream": True,
                },
            )
    assert response.status_code == 200, response.text
    assert "流式答案" in response.text
    assert response.text.endswith("data: [DONE]\n\n")


@pytest.mark.asyncio
async def test_dify_stream_is_converted_to_openai_sse(db):
    settings = get_settings()
    settings.llm_proxy_api_key = "proxy"
    db.add(
        XiaozhiMiddlewareService(
            service_code="dify-stream",
            service_name="Dify 流式服务",
            title="Dify 流式",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            qa_table=QaTable(name="dify-stream-table"),
            llm_model_config=LLMModel(
                model_name="Dify 流式模型",
                model_code="dify-stream-model",
                provider="dify",
                dify_config=LLMDifyConfig(
                    base_url="https://dify.example.test/v1",
                    mode="workflows/run",
                    api_key_encrypted=encrypt_model_credential("dify-key", settings),
                    timeout_seconds=55,
                ),
            ),
            device_mapping=DeviceMapping(
                name="流式设备", agent_id="d" * 32, enabled=True
            ),
        )
    )
    await db.commit()

    async def fake_stream(client, question, service_code):
        assert question == "流式问题"
        assert service_code == "dify-stream"
        yield "第一段"
        yield "第二段"

    with patch.object(DifyLLMClient, "stream", new=fake_stream):
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "dify-stream",
                    "messages": [{"role": "user", "content": "流式问题"}],
                    "stream": True,
                },
            )
    assert response.status_code == 200, response.text
    assert '"content": "第一段"' in response.text
    assert '"content": "第二段"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")


def test_dify_payload_and_sse_parsing():
    client = DifyLLMClient(
        get_settings(),
        base_url="https://dify.example.test/v1",
        api_key="key",
        mode="workflows/run",
    )
    assert client.url.endswith("/v1/workflows/run")
    assert client._payload("问题", "project", streaming=False) == {
        "inputs": {"query": "问题"},
        "response_mode": "blocking",
        "user": "project",
    }
    assert (
        client._parse_sse_line('data: {"event":"text_chunk","data":{"text":"答"}}')
        == "答"
    )


@pytest.mark.asyncio
async def test_dify_complete_sends_expected_request(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"answer": "Dify 回复"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, json=json)
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.llm_dify.httpx.AsyncClient", lambda **_kwargs: FakeClient()
    )
    client = DifyLLMClient(
        get_settings(),
        base_url="https://dify.example.test/v1",
        api_key="dify-key",
        mode="chat-messages",
    )
    assert await client.complete("问题", "project") == "Dify 回复"
    assert captured["url"] == "https://dify.example.test/v1/chat-messages"
    assert captured["headers"]["Authorization"] == "Bearer dify-key"
    assert captured["json"] == {
        "inputs": {},
        "query": "问题",
        "response_mode": "blocking",
        "user": "project",
    }


@pytest.mark.asyncio
async def test_dify_workflow_complete_reads_outputs(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"outputs": {"answer": "工作流答案"}}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.llm_dify.httpx.AsyncClient", lambda **_kwargs: FakeClient()
    )
    client = DifyLLMClient(
        get_settings(),
        base_url="https://dify.example.test/v1",
        api_key="dify-key",
        mode="workflows/run",
    )
    assert await client.complete("问题", "project") == "工作流答案"


@pytest.mark.asyncio
async def test_asr_variants_still_hit_qa_table(db, caplog):
    """唤醒词前缀、全角数字、尾随标点是语音识别的常见变体，均应命中问答表。"""

    table = QaTable(name="asr-variant-table")
    table.items = [
        QaItem(
            question="你好",
            answer="测试通过",
            normalized_question="你好",
            question_fingerprint=question_fingerprint("你好"),
        ),
        QaItem(
            question="需要担保金额为115万元",
            answer="补贴前1.15万元",
            normalized_question="需要担保金额为115万元",
            question_fingerprint=question_fingerprint("需要担保金额为115万元"),
        ),
    ]
    db.add(
        XiaozhiMiddlewareService(
            service_code="asr-variant-project",
            service_name="语音容错服务",
            title="语音容错",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=["小智"],
            wake_requirement_count=0,
            published=True,
            ai_reply_enabled=False,
            default_reply_text="听不懂哦。",
            qa_table=table,
            device_mapping=DeviceMapping(
                name="语音容错设备", agent_id="a" * 32, enabled=True
            ),
        )
    )
    await db.commit()
    get_settings().llm_proxy_api_key = "proxy"
    caplog.set_level(logging.INFO, logger="app.services.llm_proxy_service")

    def ask(content: str):
        return {
            "headers": {"Authorization": "Bearer proxy"},
            "json": {
                "model": "asr-variant-project",
                "messages": [{"role": "user", "content": content}],
            },
        }

    with TestClient(create_app()) as client:
        for content, expected in [
            ("小智，需要担保金额为１１５万元？", "补贴前1.15万元"),
            ("你好。", "测试通过"),
            ('{"speaker":"张三","content":"你好"}', "测试通过"),
            ("[说话人: 张三] 你好", "测试通过"),
            ("小智你好呀", "听不懂哦。"),
        ]:
            response = client.post("/v1/chat/completions", **ask(content))
            assert response.status_code == 200, response.text
            assert response.json()["choices"][0]["message"]["content"] == expected

        tool_prompt = """
<tool_calling>
【核心原则】你是拥有工具能力的智能助手。
</tool_calling>
当前可用工具: play_music、get_weather。
"""
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer proxy"},
            json={
                "model": "asr-variant-project",
                "stream": True,
                "messages": [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "上一轮回答"},
                    {"role": "user", "content": tool_prompt},
                ],
            },
        )
        assert response.status_code == 200, response.text
        assert "测试通过" in response.text

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "event=llm_request_received" in logs
    assert 'raw_user_content=\'{"speaker":"张三","content":"你好"}\'' in logs
    assert "parsed_question='你好'" in logs
    assert "injected_user_messages_skipped=1" in logs


@pytest.mark.asyncio
async def test_disabled_ai_returns_default_reply_without_llm(db):
    table = QaTable(name="default-reply-table")
    table.items = [
        QaItem(
            question="你好",
            answer="固定答案",
            normalized_question="你好",
            question_fingerprint=question_fingerprint("你好"),
        ),
        QaItem(
            question="你们几点开门",
            answer="九点开门",
            normalized_question="你们几点开门",
            question_fingerprint=question_fingerprint("你们几点开门"),
        ),
    ]
    db.add(
        XiaozhiMiddlewareService(
            service_code="default-reply-project",
            service_name="默认词服务",
            title="默认词",
            questions=[],
            voice_wakeup_enabled=False,
            wake_listening_texts=[],
            wake_requirement_count=0,
            published=True,
            ai_reply_enabled=False,
            default_reply_text="这个问题我还需要学习",
            qa_table=table,
            device_mapping=DeviceMapping(
                name="默认词设备", agent_id="b" * 32, enabled=True
            ),
        )
    )
    await db.commit()
    get_settings().llm_proxy_api_key = "proxy"
    with patch.object(
        UpstreamLLMClient, "complete", new_callable=AsyncMock
    ) as upstream:
        with TestClient(create_app()) as client:
            missed = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "default-reply-project",
                    "messages": [{"role": "user", "content": "你好呀"}],
                },
            )
            fuzzy = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "default-reply-project",
                    "messages": [{"role": "user", "content": "你们几点开门？"}],
                },
            )
            streamed = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer proxy"},
                json={
                    "model": "default-reply-project",
                    "stream": True,
                    "messages": [{"role": "user", "content": "再讲一个"}],
                },
            )
    assert missed.status_code == 200, missed.text
    assert (
        missed.json()["choices"][0]["message"]["content"] == "这个问题我还需要学习"
    )
    # 模糊命中问答表时仍优先返回固定答案
    assert fuzzy.status_code == 200, fuzzy.text
    assert fuzzy.json()["choices"][0]["message"]["content"] == "九点开门"
    # 流式模式同样返回默认词
    assert streamed.status_code == 200, streamed.text
    assert "这个问题我还需要学习" in streamed.text
    upstream.assert_not_awaited()
