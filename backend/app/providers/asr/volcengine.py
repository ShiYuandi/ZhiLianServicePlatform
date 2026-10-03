from __future__ import annotations

import gzip
import json
import uuid

import websockets

from app.providers.asr.base import ASRProvider, ASRProviderError, SpeechRecognitionResult


class VolcengineASRProvider(ASRProvider):
    """火山豆包 ASR v2 非流式协议，复用小智 doubao.py 的帧格式。"""

    ws_url = "wss://openspeech.bytedance.com/api/v2/asr"

    def __init__(
        self,
        *,
        app_id: str | None,
        access_token: str,
        resource_id: str = "volc.bigasr.sauc.duration",
        language: str = "zh-CN",
        boosting_table_name: str | None = None,
        correct_table_name: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self.app_id = (app_id or "").strip()
        self.access_token = access_token.strip()
        self.resource_id = (resource_id or "volc.bigasr.sauc.duration").strip()
        self.language = (language or "zh-CN").strip()
        self.boosting_table_name = (boosting_table_name or "").strip()
        self.correct_table_name = (correct_table_name or "").strip()
        self.timeout_seconds = timeout_seconds

    def _validate(self) -> None:
        if not self.app_id or not self.access_token or not self.resource_id:
            raise ASRProviderError("火山 ASR AppID、Access Token、资源 ID 未完整配置", code="ASR_CREDENTIAL_MISSING")

    @staticmethod
    def _header(message_type: int = 1, flags: int = 0) -> bytes:
        return bytes((0x11, (message_type << 4) | flags, 0x11, 0x00))

    @staticmethod
    def _parse_response(data: bytes) -> dict:
        if len(data) < 8:
            raise ASRProviderError("火山 ASR 返回帧格式无效", code="ASR_PROTOCOL_ERROR")
        message_type = data[1] >> 4
        payload = data[4:]
        if message_type == 0x0F:
            code = int.from_bytes(payload[:4], "big") if len(payload) >= 4 else 0
            raise ASRProviderError("火山 ASR 返回错误", code=f"ASR_PROVIDER_{code}", retryable=code >= 5000)
        if len(payload) < 4:
            return {}
        size = int.from_bytes(payload[:4], "big", signed=False)
        body = payload[4 : 4 + size]
        if data[2] & 0x0F == 1:
            body = gzip.decompress(body)
        return json.loads(body.decode("utf-8")) if body else {}

    def _request_body(self) -> dict:
        return {
            "app": {"appid": self.app_id, "cluster": "volcengine", "token": self.access_token},
            "user": {"uid": str(uuid.uuid4())},
            "request": {
                "reqid": str(uuid.uuid4()),
                "show_utterances": False,
                "sequence": 1,
                "boosting_table_name": self.boosting_table_name,
                "correct_table_name": self.correct_table_name,
            },
            "audio": {"format": "raw", "rate": 16000, "language": self.language, "bits": 16, "channel": 1, "codec": "raw"},
        }

    async def test_connection(self) -> None:
        self._validate()

    async def recognize(self, pcm_bytes: bytes) -> SpeechRecognitionResult:
        self._validate()
        if not pcm_bytes:
            raise ASRProviderError("音频数据为空", code="ASR_AUDIO_EMPTY")
        headers = {
            "Authorization": f"Bearer; {self.access_token}",
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }
        try:
            async with websockets.connect(self.ws_url, additional_headers=headers, open_timeout=self.timeout_seconds, close_timeout=5) as ws:
                meta = gzip.compress(json.dumps(self._request_body(), ensure_ascii=False).encode())
                await ws.send(self._header(1) + len(meta).to_bytes(4, "big") + meta)
                await ws.recv()  # 初始化 ACK
                chunk_size = 15_000 * 2 * 16  # 15 秒，16kHz、16bit、单声道
                for offset in range(0, len(pcm_bytes), chunk_size):
                    chunk = pcm_bytes[offset : offset + chunk_size]
                    last = offset + chunk_size >= len(pcm_bytes)
                    payload = gzip.compress(chunk)
                    await ws.send(self._header(2, 2 if last else 0) + len(payload).to_bytes(4, "big") + payload)
                result = self._parse_response(await ws.recv())
                payload = result.get("result") or []
                return SpeechRecognitionResult(text=str(payload[0].get("text", "")) if payload else "", provider="volcengine")
        except ASRProviderError:
            raise
        except (TimeoutError, websockets.WebSocketException) as exc:
            raise ASRProviderError("火山 ASR 服务暂时不可用", code="ASR_UPSTREAM_UNAVAILABLE", retryable=True) from exc
