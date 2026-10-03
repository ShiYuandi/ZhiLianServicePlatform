from __future__ import annotations

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.normalization import normalize_device_name
from app.models.device_mapping import DeviceMapping
from app.schemas.device import DeviceAddRequest


async def add_device(
    db: AsyncSession,
    payload: DeviceAddRequest,
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    mapping = await db.scalar(
        select(DeviceMapping).where(
            func.lower(DeviceMapping.name) == normalize_device_name(payload.name),
            DeviceMapping.enabled.is_(True),
        )
    )
    if not mapping:
        raise AppError(
            "DEVICE_MAPPING_NOT_FOUND", f"未找到名称“{payload.name}”对应的设备映射", 400
        )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.xiaozhi_token}",
        "Cookie": f"JSESSIONID={settings.xiaozhi_jsessionid}",
    }
    body = {
        "agentId": mapping.agent_id,
        "board": payload.board,
        "appVersion": payload.appVersion,
        "macAddress": payload.macAddress,
    }
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.post(
                settings.xiaozhi_api_url,
                headers=headers,
                json=body,
                timeout=settings.xiaozhi_timeout_seconds,
            )
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:
            raise AppError(
                "XIAOZHI_INVALID_RESPONSE", "小智平台返回了无效响应", 502
            ) from exc
    except httpx.TimeoutException as exc:
        raise AppError("XIAOZHI_TIMEOUT", "小智平台请求超时", 504) from exc
    except httpx.HTTPStatusError as exc:
        status = (
            exc.response.status_code if 400 <= exc.response.status_code < 500 else 502
        )
        raise AppError(
            "XIAOZHI_REJECTED", "小智平台拒绝了设备添加请求", status
        ) from exc
    except httpx.RequestError as exc:
        raise AppError("XIAOZHI_UNAVAILABLE", "暂时无法连接小智平台", 502) from exc
