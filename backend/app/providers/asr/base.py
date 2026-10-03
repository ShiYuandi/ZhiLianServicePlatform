from __future__ import annotations

from dataclasses import dataclass


class ASRProviderError(RuntimeError):
    """语音供应器返回了可控的协议或调用错误。"""

    def __init__(self, message: str, *, code: str = "ASR_PROVIDER_ERROR", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class SpeechRecognitionResult:
    text: str
    provider: str


class ASRProvider:
    async def recognize(self, pcm_bytes: bytes) -> SpeechRecognitionResult:
        raise NotImplementedError

    async def test_connection(self) -> None:
        raise NotImplementedError
