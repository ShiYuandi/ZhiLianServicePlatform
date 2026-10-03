from __future__ import annotations

import base64
import io
import math

import httpx
from PIL import Image

from app.providers.image.base import ImageGenerationResult, ImageProvider, ImageProviderError


class VolcengineImageProvider(ImageProvider):
    """火山方舟 Seedream，兼容 Unity 的文生图/单图图生图请求。"""

    min_request_pixels = 921_600

    def __init__(self, *, api_url: str, api_key: str, upstream_model: str, default_width: int = 1024, default_height: int = 1024, timeout_seconds: float = 120, watermark: bool = False, client: httpx.AsyncClient | None = None) -> None:
        self.api_url = api_url.strip()
        self.api_key = api_key.strip()
        self.upstream_model = upstream_model.strip()
        self.default_width = default_width
        self.default_height = default_height
        self.timeout = httpx.Timeout(timeout_seconds)
        self.watermark = watermark
        self._client = client

    def _validate(self) -> None:
        if not self.api_url or not self.api_key or not self.upstream_model:
            raise ImageProviderError("火山 Seedream API 地址、API Key、模型 ID 未完整配置", code="IMAGE_CREDENTIAL_MISSING")

    def _request_size(self, width: int, height: int) -> tuple[int, int]:
        pixels = width * height
        if pixels >= self.min_request_pixels:
            return width, height
        scale = math.sqrt(self.min_request_pixels / pixels)
        req_w = math.ceil(width * scale / 2) * 2
        req_h = math.ceil(height * scale / 2) * 2
        while req_w * req_h < self.min_request_pixels:
            req_w += 2
            req_h += 2
        return req_w, req_h

    async def test_connection(self) -> None:
        self._validate()

    async def generate(self, prompt: str, *, image_bytes: bytes | None = None, width: int | None = None, height: int | None = None) -> ImageGenerationResult:
        self._validate()
        prompt = prompt.strip()
        if not prompt:
            raise ImageProviderError("生成提示词不能为空", code="IMAGE_PROMPT_EMPTY")
        target_w, target_h = width or self.default_width, height or self.default_height
        request_w, request_h = self._request_size(target_w, target_h)
        body: dict[str, object] = {
            "model": self.upstream_model,
            "prompt": prompt,
            "size": f"{request_w}x{request_h}",
            "sequential_image_generation": "disabled",
            "stream": False,
            "response_format": "url",
            "watermark": self.watermark,
        }
        if image_bytes:
            body["image"] = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await client.post(self.api_url, json=body, headers={"Authorization": f"Bearer {self.api_key}"})
            if response.status_code >= 500:
                raise ImageProviderError("火山 Seedream 服务暂时不可用", code="IMAGE_UPSTREAM_UNAVAILABLE", retryable=True)
            if response.status_code >= 400:
                raise ImageProviderError("火山 Seedream 请求失败", code="IMAGE_REQUEST_INVALID")
            data = response.json()
            image_url = ((data.get("data") or [{}])[0]).get("url")
            if not image_url:
                raise ImageProviderError("火山 Seedream 返回中没有图片地址", code="IMAGE_PROVIDER_RESPONSE_INVALID")
            image_response = await client.get(str(image_url))
            if image_response.status_code >= 400:
                raise ImageProviderError("生成结果下载失败", code="IMAGE_RESULT_DOWNLOAD_FAILED", retryable=image_response.status_code >= 500)
            if len(image_response.content) > 20 * 1024 * 1024:
                raise ImageProviderError("生成结果超过大小限制", code="IMAGE_RESULT_TOO_LARGE")
            try:
                with Image.open(io.BytesIO(image_response.content)) as source:
                    source.load()
                    converted = source.convert("RGBA" if "A" in source.getbands() else "RGB")
                    if converted.size != (target_w, target_h):
                        converted = converted.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    converted.save(output, format="PNG", optimize=True)
                    png_bytes = output.getvalue()
            except Exception as exc:
                raise ImageProviderError("生成结果不是有效图片", code="IMAGE_RESULT_INVALID") from exc
            return ImageGenerationResult(png_bytes=png_bytes, provider="volcengine", width=target_w, height=target_h)
        except httpx.HTTPError as exc:
            raise ImageProviderError("火山 Seedream 服务暂时不可用", code="IMAGE_UPSTREAM_UNAVAILABLE", retryable=True) from exc
        finally:
            if own_client:
                await client.aclose()
