from __future__ import annotations

from dataclasses import dataclass


class ImageProviderError(RuntimeError):
    def __init__(self, message: str, *, code: str = "IMAGE_PROVIDER_ERROR", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class ImageGenerationResult:
    png_bytes: bytes
    provider: str
    width: int
    height: int


class ImageProvider:
    async def generate(self, prompt: str, *, image_bytes: bytes | None = None, width: int | None = None, height: int | None = None) -> ImageGenerationResult:
        raise NotImplementedError

    async def test_connection(self) -> None:
        raise NotImplementedError
