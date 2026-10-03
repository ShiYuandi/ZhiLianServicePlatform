from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from app.core.config import Settings


class UpstreamLLMError(Exception):
    """上游 OpenAI 兼容服务不可用或返回了无效响应。"""


_FORWARDED_FIELDS = {
    "messages",
    "max_tokens",
    "temperature",
    "top_p",
    "frequency_penalty",
    "tools",
    "tool_choice",
    "stream",
}


def build_upstream_payload(payload: Mapping[str, Any], model: str) -> dict[str, Any]:
    result = {key: payload[key] for key in _FORWARDED_FIELDS if key in payload}
    result["model"] = model
    return result


class UpstreamLLMClient:
    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.settings = settings
        self.base_url = base_url or settings.upstream_llm_base_url
        self.api_key = api_key or settings.upstream_llm_api_key
        self.model = model or settings.upstream_llm_model
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.upstream_llm_timeout_seconds
        )
        self.url = f"{self.base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
        }

    async def complete(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request_payload = build_upstream_payload(payload, self.model)
        request_payload["stream"] = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url, headers=self._headers(), json=request_payload
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamLLMError from exc
        if not isinstance(data, dict) or not data.get("choices"):
            raise UpstreamLLMError
        return data

    async def stream(self, payload: Mapping[str, Any]) -> AsyncIterator[bytes]:
        request_payload = build_upstream_payload(payload, self.model)
        request_payload["stream"] = True
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream(
                    "POST", self.url, headers=self._headers(), json=request_payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            yield line.encode("utf-8") + b"\n\n"
        except httpx.HTTPError as exc:
            raise UpstreamLLMError from exc
