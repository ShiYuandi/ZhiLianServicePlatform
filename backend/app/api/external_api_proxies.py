from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import NOT_FOUND_ERROR, PUBLIC_RESPONSES, PUBLIC_TAG
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services import external_api_proxy


router = APIRouter(prefix="/api", tags=[PUBLIC_TAG], responses=PUBLIC_RESPONSES)


_FORWARD_ROUTE = "/external-proxies/{proxy_uuid}"
_FORWARD_ROUTE_OPTIONS = dict(
    summary="转发外部接口请求",
    response_class=Response,
    response_description="上游接口原始响应",
    responses={404: NOT_FOUND_ERROR, 502: {"description": "上游接口不可用"}, 503: {"description": "代理已停用"}, 504: {"description": "上游接口请求超时"}},
)
@router.get(_FORWARD_ROUTE, **_FORWARD_ROUTE_OPTIONS)
@router.post(_FORWARD_ROUTE, **_FORWARD_ROUTE_OPTIONS)
@router.put(_FORWARD_ROUTE, **_FORWARD_ROUTE_OPTIONS)
@router.patch(_FORWARD_ROUTE, **_FORWARD_ROUTE_OPTIONS)
@router.delete(_FORWARD_ROUTE, **_FORWARD_ROUTE_OPTIONS)
@router.head(_FORWARD_ROUTE, include_in_schema=False)
async def forward_external_request(
    request: Request,
    proxy_uuid: UUID = Path(description="外部接口代理 UUID"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """按 UUID 查找上游网址，透传请求并原样返回上游响应。"""
    proxy = await external_api_proxy.get_proxy(db, str(proxy_uuid))
    return await external_api_proxy.forward_request(
        request, proxy, settings.external_proxy_timeout_seconds
    )
