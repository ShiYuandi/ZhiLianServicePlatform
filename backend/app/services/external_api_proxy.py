from __future__ import annotations

import uuid

import httpx
from fastapi import Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.external_api_proxy import ExternalApiProxy
from app.schemas.external_api_proxy import ExternalApiProxyCreate, ExternalApiProxyUpdate


_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


async def get_proxy(db: AsyncSession, proxy_uuid: str) -> ExternalApiProxy:
    proxy = await db.get(ExternalApiProxy, proxy_uuid)
    if not proxy:
        raise AppError("EXTERNAL_API_PROXY_NOT_FOUND", "外部接口代理不存在", 404)
    return proxy


async def list_proxies(
    db: AsyncSession, page: int, page_size: int
) -> tuple[list[ExternalApiProxy], int]:
    total = int(await db.scalar(select(func.count(ExternalApiProxy.proxy_uuid))) or 0)
    result = await db.scalars(
        select(ExternalApiProxy)
        .order_by(ExternalApiProxy.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.all()), total


async def create_proxy(
    db: AsyncSession, payload: ExternalApiProxyCreate
) -> ExternalApiProxy:
    proxy = ExternalApiProxy(
        proxy_uuid=str(uuid.uuid4()),
        target_url=payload.target_url,
        enabled=payload.enabled,
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy


async def update_proxy(
    db: AsyncSession, proxy_uuid: str, payload: ExternalApiProxyUpdate
) -> ExternalApiProxy:
    proxy = await get_proxy(db, proxy_uuid)
    proxy.target_url = payload.target_url
    proxy.enabled = payload.enabled
    await db.commit()
    await db.refresh(proxy)
    return proxy


async def delete_proxy(db: AsyncSession, proxy_uuid: str) -> None:
    proxy = await get_proxy(db, proxy_uuid)
    await db.delete(proxy)
    await db.commit()


async def forward_request(
    request: Request, proxy: ExternalApiProxy, timeout_seconds: float
) -> Response:
    if not proxy.enabled:
        raise AppError("EXTERNAL_API_PROXY_DISABLED", "外部接口代理已停用", 503)

    body = await request.body()
    headers = [
        (name, value)
        for name, value in request.headers.items()
        if name.lower() not in _HOP_BY_HOP_HEADERS and name.lower() != "cookie"
    ]
    query = list(request.query_params.multi_items())
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
            upstream = await client.request(
                request.method,
                proxy.target_url,
                params=query,
                headers=headers,
                content=body,
            )
    except httpx.TimeoutException as exc:
        raise AppError("EXTERNAL_API_PROXY_TIMEOUT", "上游接口请求超时", 504) from exc
    except httpx.RequestError as exc:
        raise AppError("EXTERNAL_API_PROXY_UNAVAILABLE", "上游接口暂时不可用", 502) from exc

    response_headers = {
        name: value
        for name, value in upstream.headers.multi_items()
        if name.lower() not in _HOP_BY_HOP_HEADERS and name.lower() != "content-encoding"
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
