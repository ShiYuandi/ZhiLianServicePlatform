from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import decrypt_model_credential
from app.schemas.llm_proxy import ChatCompletionRequest
from app.services import qa_service, xiaozhi_service
from app.services.llm_upstream import UpstreamLLMClient, UpstreamLLMError
from app.services.llm_dify import DifyLLMClient, DifyLLMError


logger = logging.getLogger(__name__)
_SPEAKER_PREFIX_RE = re.compile(
    r"^\s*[\[【]\s*(?:说话人|speaker)\s*[:：][^\]】]*[\]】]\s*",
    re.IGNORECASE,
)


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                envelope = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                envelope = None
            if isinstance(envelope, dict):
                nested = envelope.get("content", envelope.get("text"))
                if nested is not None:
                    return _message_text(nested)
        return _SPEAKER_PREFIX_RE.sub("", text)
    if isinstance(content, dict):
        nested = content.get("content", content.get("text"))
        return _message_text(nested) if nested is not None else ""
    if isinstance(content, list):
        return "".join(_message_text(item) for item in content)
    return ""


def _last_user_question(payload: ChatCompletionRequest) -> str:
    for message in reversed(payload.messages):
        if message.role == "user":
            text = _message_text(message.content)
            if _is_tool_instruction(text):
                continue
            return text
    return ""


def _is_tool_instruction(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("<tool_calling>") and "</tool_calling>" in stripped


def _last_user_content(payload: ChatCompletionRequest) -> Any:
    for message in reversed(payload.messages):
        if message.role == "user":
            return message.content
    return None


def _log_request_received(
    payload: ChatCompletionRequest, question: str, request_id: str
) -> None:
    skipped_tool_instructions = sum(
        1
        for message in payload.messages
        if message.role == "user"
        and _is_tool_instruction(_message_text(message.content))
    )
    logger.info(
        "event=llm_request_received request_id=%s model=%s stream=%s "
        "message_count=%s raw_user_content=%r parsed_question=%r "
        "injected_user_messages_skipped=%s",
        request_id,
        payload.model,
        payload.stream,
        len(payload.messages),
        _last_user_content(payload),
        question,
        skipped_tool_instructions,
    )


def _validate_limits(payload: ChatCompletionRequest, settings: Settings) -> None:
    if len(payload.messages) > settings.llm_proxy_max_messages:
        raise AppError("TOO_MANY_MESSAGES", "消息数量超过限制", 422)
    total = 0
    for message in payload.messages:
        text = _message_text(message.content)
        if len(text) > settings.llm_proxy_max_message_chars:
            raise AppError("MESSAGE_TOO_LONG", "单条消息超过长度限制", 422)
        total += len(text)
    if total > settings.llm_proxy_max_total_chars:
        raise AppError("MESSAGES_TOO_LONG", "消息总长度超过限制", 422)


def _response(content: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _sse(data: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def _delta(
    content: str, model: str, completion_id: str, finish_reason: str | None = None
) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "delta": {"content": content}, "finish_reason": finish_reason}
        ],
    }


async def resolve_service(db: AsyncSession, model: str):
    service = await xiaozhi_service.get_published_service(db, model)
    if not service.device_mapping or not service.device_mapping.enabled:
        raise AppError("DEVICE_DISABLED", "数字人设备已停用", 403)
    return service


def service_llm_client(
    service, settings: Settings
) -> UpstreamLLMClient | DifyLLMClient:
    model = service.llm_model_config
    if not model:
        raise AppError("LLM_MODEL_NOT_BOUND", "该小智中间件服务未绑定大语言模型", 409)
    if model.archived_at is not None:
        raise AppError("LLM_MODEL_ARCHIVED", "绑定的大语言模型已归档", 503)
    if not model.enabled:
        raise AppError("LLM_MODEL_DISABLED", "绑定的大语言模型已停用", 503)
    if model.provider == "dify":
        config = model.dify_config
        if (
            not config
            or not config.base_url
            or config.mode
            not in {
                "chat-messages",
                "workflows/run",
            }
        ):
            raise AppError(
                "LLM_MODEL_CONFIG_INVALID",
                "绑定的 Dify 模型调用配置不完整",
                409,
            )
        if not config.api_key_encrypted:
            raise AppError(
                "LLM_CREDENTIAL_MISSING", "绑定的 Dify 模型缺少 API Key", 409
            )
        return DifyLLMClient(
            settings,
            base_url=config.base_url,
            api_key=decrypt_model_credential(config.api_key_encrypted, settings),
            mode=config.mode,
            timeout_seconds=config.timeout_seconds,
        )
    if model.provider != "openai":
        raise AppError(
            "LLM_MODEL_CONFIG_INVALID", "绑定的大语言模型供应器不受支持", 409
        )
    config = model.openai_config
    if not config or not config.base_url or not config.upstream_model:
        raise AppError(
            "LLM_MODEL_CONFIG_INVALID", "绑定的 OpenAI 模型调用配置不完整", 409
        )
    if not config.api_key_encrypted:
        raise AppError("LLM_CREDENTIAL_MISSING", "绑定的 OpenAI 模型缺少 API Key", 409)
    return UpstreamLLMClient(
        settings,
        base_url=config.base_url,
        model=config.upstream_model,
        api_key=decrypt_model_credential(config.api_key_encrypted, settings),
        timeout_seconds=config.timeout_seconds,
    )


async def _fixed_reply(
    db: AsyncSession,
    service,
    question: str,
    settings: Settings,
    *,
    request_id: str = "-",
    log_result: bool = True,
) -> str | None:
    """优先返回问答表固定答案；关闭真实大模型时未命中返回默认回复词。"""

    if service.qa_table_id is not None:
        if log_result:
            logger.info(
                "event=qa_pipeline_start request_id=%s service=%s table_id=%s "
                "ai_reply_enabled=%s parsed_question=%r",
                request_id,
                service.service_code,
                service.qa_table_id,
                service.ai_reply_enabled,
                question,
            )
        answer = await qa_service.find_fixed_answer(
            db,
            service.qa_table_id,
            question,
            request_id=request_id,
            log_details=log_result,
        )
        if answer is None:
            # 语音识别常把唤醒词带进问题（“小智，你们几点开门”），剥离后重试一次。
            stripped = qa_service.strip_wake_prefix(
                service.wake_listening_texts, question
            )
            if stripped:
                if log_result:
                    logger.info(
                        "event=qa_wake_prefix_stripped request_id=%s service=%s "
                        "original_question=%r stripped_question=%r",
                        request_id,
                        service.service_code,
                        question,
                        stripped,
                    )
                answer = await qa_service.find_fixed_answer(
                    db,
                    service.qa_table_id,
                    stripped,
                    request_id=request_id,
                    attempt="wake_stripped",
                    log_details=log_result,
                )
        if answer is not None:
            if log_result:
                logger.info(
                    "event=qa_response_selected request_id=%s service=%s table_id=%s "
                    "result=fixed_answer question=%r",
                    request_id,
                    service.service_code,
                    service.qa_table_id,
                    question,
                )
            return answer
    if not service.ai_reply_enabled:
        if log_result:
            logger.info(
                "event=qa_response_selected request_id=%s service=%s table_id=%s "
                "result=default_reply question=%r normalized=%r",
                request_id,
                service.service_code,
                service.qa_table_id,
                question,
                qa_service.normalize_question(question),
            )
        return service.default_reply_text or settings.llm_proxy_fallback_text
    if log_result:
        logger.info(
            "event=qa_response_selected request_id=%s service=%s table_id=%s "
            "result=forward_to_ai question=%r",
            request_id,
            service.service_code,
            service.qa_table_id,
            question,
        )
    return None


async def validate_stream_ready(
    db: AsyncSession,
    payload: ChatCompletionRequest,
    settings: Settings,
    request_id: str = "-",
) -> None:
    """在发送 SSE 响应头前完成会产生稳定业务错误的校验。"""

    _validate_limits(payload, settings)
    question = _last_user_question(payload)
    _log_request_received(payload, question, request_id)
    service = await resolve_service(db, payload.model)
    if (
        await _fixed_reply(
            db,
            service,
            question,
            settings,
            request_id=request_id,
            log_result=False,
        )
        is None
    ):
        service_llm_client(service, settings)


async def complete(
    db: AsyncSession,
    payload: ChatCompletionRequest,
    settings: Settings,
    request_id: str = "-",
) -> dict[str, Any]:
    _validate_limits(payload, settings)
    question = _last_user_question(payload)
    _log_request_received(payload, question, request_id)
    service = await resolve_service(db, payload.model)
    answer = await _fixed_reply(
        db, service, question, settings, request_id=request_id
    )
    if answer is not None:
        return _response(answer, payload.model)
    try:
        client = service_llm_client(service, settings)
        if isinstance(client, DifyLLMClient):
            return _response(
                await client.complete(question, service.service_code), payload.model
            )
        return await client.complete(payload.model_dump(mode="json"))
    except (UpstreamLLMError, DifyLLMError):
        return _response(settings.llm_proxy_fallback_text, payload.model)


async def stream(
    db: AsyncSession,
    payload: ChatCompletionRequest,
    settings: Settings,
    request_id: str = "-",
) -> AsyncIterator[bytes]:
    _validate_limits(payload, settings)
    service = await resolve_service(db, payload.model)
    question = _last_user_question(payload)
    answer = await _fixed_reply(
        db, service, question, settings, request_id=request_id
    )
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    if answer is not None:
        yield _sse(_delta(answer, payload.model, completion_id))
        yield _sse(_delta("", payload.model, completion_id, "stop"))
        yield b"data: [DONE]\n\n"
        return
    try:
        seen_done = False
        client = service_llm_client(service, settings)
        if isinstance(client, DifyLLMClient):
            async for content in client.stream(question, service.service_code):
                yield _sse(_delta(content, payload.model, completion_id))
        else:
            async for line in client.stream(payload.model_dump(mode="json")):
                if b"[DONE]" in line:
                    seen_done = True
                yield line
        if not seen_done:
            yield b"data: [DONE]\n\n"
    except (UpstreamLLMError, DifyLLMError):
        yield _sse(
            _delta(
                settings.llm_proxy_stream_interruption_text,
                payload.model,
                completion_id,
            )
        )
        yield _sse(_delta("", payload.model, completion_id, "stop"))
        yield b"data: [DONE]\n\n"
