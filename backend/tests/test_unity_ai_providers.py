from __future__ import annotations

import io

import httpx
import pytest
from PIL import Image

from app.providers.asr.baidu import BaiduASRProvider
from app.providers.image.volcengine import VolcengineImageProvider


@pytest.mark.asyncio
async def test_baidu_provider_matches_unity_json_and_caches_token():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
        body = request.read().decode()
        assert '"format":"pcm"' in body
        assert '"rate":16000' in body
        assert '"dev_pid":1537' in body
        return httpx.Response(200, json={"err_no": 0, "result": ["你好世界"]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = BaiduASRProvider(
        app_id="app",
        api_key="key",
        secret_key="secret",
        client=client,
    )
    first = await provider.recognize(b"pcm")
    second = await provider.recognize(b"pcm")
    await client.aclose()

    assert first.text == second.text == "你好世界"
    assert sum(request.url.path.endswith("/token") for request in calls) == 1


@pytest.mark.asyncio
async def test_seedream_provider_supports_text_to_image_and_single_image_to_image():
    generated = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(generated, format="PNG")
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/generations"):
            import json

            data = json.loads(request.content)
            requests.append(data)
            return httpx.Response(200, json={"data": [{"url": "https://result.test/image.png"}]})
        return httpx.Response(200, content=generated.getvalue(), headers={"Content-Type": "image/png"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = VolcengineImageProvider(
        api_url="https://ark.test/api/v3/images/generations",
        api_key="key",
        upstream_model="doubao-seedream-4-0-250828",
        default_width=932,
        default_height=582,
        client=client,
    )
    text_result = await provider.generate("一只猫", width=932, height=582)
    image_result = await provider.generate("转成水彩", image_bytes=generated.getvalue(), width=932, height=582)
    await client.aclose()

    assert "image" not in requests[0]
    assert requests[1]["image"].startswith("data:image/png;base64,")
    assert requests[0]["model"] == "doubao-seedream-4-0-250828"
    assert text_result.width == image_result.width == 932
    with Image.open(io.BytesIO(text_result.png_bytes)) as output:
        assert output.size == (932, 582)
