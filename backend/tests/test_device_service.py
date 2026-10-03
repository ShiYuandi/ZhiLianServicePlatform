import httpx
import pytest

from app.core.config import get_settings
from app.models.device_mapping import DeviceMapping
from app.schemas.device import DeviceAddRequest
from app.services.device_service import add_device


@pytest.mark.asyncio
async def test_device_proxy_preserves_existing_request_and_adds_agent_id(db):
    db.add(DeviceMapping(name="示例设备-A", agent_id="a" * 32, enabled=True))
    await db.commit()
    captured = {}

    async def handler(request: httpx.Request):
        captured["authorization"] = request.headers["Authorization"]
        captured["cookie"] = request.headers["Cookie"]
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"success": True})

    result = await add_device(
        db,
        DeviceAddRequest(
            name="示例设备-A",
            board="esp32",
            appVersion="1.0.0",
            macAddress="00:11:22:33:44:55",
        ),
        get_settings(),
        httpx.MockTransport(handler),
    )
    assert result == {"success": True}
    assert "fake-token" in captured["authorization"]
    assert "fake-session" in captured["cookie"]
    assert '"agentId":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' in captured["body"]


@pytest.mark.asyncio
async def test_device_name_matching_ignores_spaces_and_case(db):
    db.add(DeviceMapping(name="Demo-Agent", agent_id="b" * 32, enabled=True))
    await db.commit()

    async def handler(request: httpx.Request):
        return httpx.Response(200, json={"agentId": "b" * 32})

    result = await add_device(
        db,
        DeviceAddRequest(
            name="  demo-agent  ",
            board="esp32",
            appVersion="1.0.0",
            macAddress="00:11:22:33:44:55",
        ),
        get_settings(),
        httpx.MockTransport(handler),
    )
    assert result["agentId"] == "b" * 32
