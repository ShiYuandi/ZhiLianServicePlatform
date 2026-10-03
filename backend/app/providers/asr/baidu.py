from __future__ import annotations

import base64
import time
import uuid

import httpx

from app.providers.asr.base import ASRProvider, ASRProviderError, SpeechRecognitionResult


class BaiduASRProvider(ASRProvider):
    """百度短语音识别，对齐 Unity BaiduSpeechService 的 JSON 协议。"""

    token_url = "https://aip.baidubce.com/oauth/2.0/token"
    asr_url = "https://vop.baidu.com/server_api"

    def __init__(
        self,
        *,
        app_id: str | None,
        api_key: str,
        secret_key: str,
        dev_pid: int = 1537,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.app_id = (app_id or "").strip()
        self.api_key = api_key.strip()
        self.secret_key = secret_key.strip()
        self.dev_pid = dev_pid
        self.timeout = httpx.Timeout(timeout_seconds)
        self._client = client
        self._token: str | None = None
        self._token_expires_at = 0.0

    def _validate(self) -> None:
        if not self.api_key or not self.secret_key:
            raise ASRProviderError("百度 API Key / Secret Key 未配置", code="ASR_CREDENTIAL_MISSING")

    async def _get_token(self) -> str:
        self._validate()
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await client.post(
                self.token_url,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
            )
            if response.status_code >= 400:
                raise ASRProviderError("百度鉴权请求失败", code="ASR_AUTH_FAILED", retryable=response.status_code >= 500)
            data = response.json()
            token = data.get("access_token")
            if not token:
                raise ASRProviderError("百度鉴权响应无有效 token", code="ASR_AUTH_FAILED")
            self._token = str(token)
            self._token_expires_at = time.monotonic() + max(60, int(data.get("expires_in", 2592000)) - 300)
            return self._token
        except httpx.HTTPError as exc:
            raise ASRProviderError("百度鉴权服务暂时不可用", code="ASR_UPSTREAM_UNAVAILABLE", retryable=True) from exc
        finally:
            if own_client:
                await client.aclose()

    async def test_connection(self) -> None:
        await self._get_token()

    async def recognize(self, pcm_bytes: bytes) -> SpeechRecognitionResult:
        if not pcm_bytes:
            raise ASRProviderError("音频数据为空", code="ASR_AUDIO_EMPTY")
        token = await self._get_token()
        body = {
            "format": "pcm",
            "rate": 16000,
            "channel": 1,
            "cuid": str(uuid.uuid4()),
            "token": token,
            "dev_pid": self.dev_pid,
            "speech": base64.b64encode(pcm_bytes).decode("ascii"),
            "len": len(pcm_bytes),
        }
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await client.post(self.asr_url, json=body)
            if response.status_code >= 500:
                raise ASRProviderError("百度语音识别服务暂时不可用", code="ASR_UPSTREAM_UNAVAILABLE", retryable=True)
            if response.status_code >= 400:
                raise ASRProviderError("百度语音识别请求失败", code="ASR_REQUEST_FAILED")
            data = response.json()
            if int(data.get("err_no", 0)) != 0:
                code = int(data.get("err_no", 0))
                if code in {3301, 3302, 3303, 3304}:
                    raise ASRProviderError("百度语音识别鉴权或参数错误", code="ASR_REQUEST_INVALID")
                raise ASRProviderError("百度语音识别失败", code="ASR_PROVIDER_ERROR", retryable=code in {18, 282000})
            result = data.get("result") or []
            return SpeechRecognitionResult(text=str(result[0]) if result else "", provider="baidu")
        except httpx.HTTPError as exc:
            raise ASRProviderError("百度语音识别服务暂时不可用", code="ASR_UPSTREAM_UNAVAILABLE", retryable=True) from exc
        finally:
            if own_client:
                await client.aclose()
