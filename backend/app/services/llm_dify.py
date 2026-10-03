from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from app.core.config import Settings


class DifyLLMError(Exception):
    """Dify 服务不可用或返回了无法识别的内容。"""


def _first_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("answer", "text", "content", "output"):
            result = _first_string(value.get(key))
            if result:
                return result
        for item in value.values():
            result = _first_string(item)
            if result:
                return result
    if isinstance(value, list):
        for item in value:
            result = _first_string(item)
            if result:
                return result
    return None


class DifyLLMClient:
    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str,
        api_key: str,
        mode: str,
        timeout_seconds: float | None = None,
    ):
        if mode not in {"chat-messages", "workflows/run"}:
            raise DifyLLMError("不支持的 Dify 调用模式")
        self.settings = settings
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.mode = mode
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.upstream_llm_timeout_seconds
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
        }

    def _payload(
        self, question: str, service_code: str, streaming: bool
    ) -> dict[str, Any]:
        response_mode = "streaming" if streaming else "blocking"
        if self.mode == "chat-messages":
            return {
                "inputs": {},
                "query": question,
                "response_mode": response_mode,
                "user": service_code,
            }
        return {
            "inputs": {"query": question},
            "response_mode": response_mode,
            "user": service_code,
        }

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.mode}"

    async def complete(self, question: str, service_code: str) -> str:
        payload = self._payload(question, service_code, streaming=False)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url, headers=self._headers(), json=payload
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DifyLLMError from exc
        if not isinstance(data, dict):
            raise DifyLLMError("Dify 返回格式错误")
        response_data = data.get("data")
        answer = (
            data.get("answer")
            if self.mode == "chat-messages"
            else response_data.get("outputs")
            if isinstance(response_data, Mapping)
            else None
        )
        text = _first_string(answer)
        if not text:
            raise DifyLLMError("Dify 返回中没有答案")
        return text

    async def stream(self, question: str, service_code: str) -> AsyncIterator[str]:
        payload = self._payload(question, service_code, streaming=True)
        emitted = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream(
                    "POST", self.url, headers=self._headers(), json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        text = self._parse_sse_line(line, include_final=not emitted)
                        if text:
                            emitted = True
                            yield text
        except httpx.HTTPError as exc:
            raise DifyLLMError from exc

    def _parse_sse_line(self, line: str, *, include_final: bool = True) -> str | None:
        if not line.startswith("data:"):
            return None
        raw = line[5:].strip()
        if not raw or raw == "[DONE]":
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        event = data.get("event")
        if event == "message_replace":
            return None
        if event in {"message", "text_chunk"}:
            return _first_string(data.get("answer") or data.get("data"))
        if event in {"node_finished", "workflow_finished"} and include_final:
            event_data = data.get("data")
            return _first_string(
                event_data.get("outputs") if isinstance(event_data, Mapping) else None
            )
        if "answer" in data:
            return _first_string(data["answer"])
        return None
