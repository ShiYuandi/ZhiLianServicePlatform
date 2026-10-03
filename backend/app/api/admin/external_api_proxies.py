from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    EXTERNAL_PROXY_TAG,
    NOT_FOUND_ERROR,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.models.external_api_proxy import ExternalApiProxy
from app.schemas.external_api_proxy import (
    ExternalApiProxyCreate,
    ExternalApiProxyListResponse,
    ExternalApiProxyOut,
    ExternalApiProxyUpdate,
)
from app.services import external_api_proxy


router = APIRouter(
    prefix="/api/admin/external-api-proxies",
    tags=[EXTERNAL_PROXY_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


def proxy_out(proxy: ExternalApiProxy) -> ExternalApiProxyOut:
    return ExternalApiProxyOut.model_validate(proxy)


@router.get(
    "",
    summary="分页查询外部接口代理",
    response_model=ExternalApiProxyListResponse,
    response_description="代理配置列表",
)
async def list_proxies(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页最多 100 条"),
    db: AsyncSession = Depends(get_db),
):
    """分页返回已配置的外部接口代理。"""
    items, total = await external_api_proxy.list_proxies(db, page, page_size)
    return ExternalApiProxyListResponse(
        items=[proxy_out(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    summary="创建外部接口代理",
    response_model=ExternalApiProxyOut,
    status_code=201,
    response_description="创建结果（包含自动生成的 UUID）",
    responses={403: CSRF_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_proxy(
    payload: ExternalApiProxyCreate, db: AsyncSession = Depends(get_db)
):
    """创建代理并自动生成供前端使用的 UUID。"""
    return proxy_out(await external_api_proxy.create_proxy(db, payload))


@router.put(
    "/{proxy_uuid}",
    summary="修改外部接口代理",
    response_model=ExternalApiProxyOut,
    response_description="更新后的代理配置",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_proxy(
    payload: ExternalApiProxyUpdate,
    proxy_uuid: UUID = Path(description="外部接口代理 UUID"),
    db: AsyncSession = Depends(get_db),
):
    """修改代理的上游网址或启用状态。"""
    return proxy_out(
        await external_api_proxy.update_proxy(db, str(proxy_uuid), payload)
    )


@router.delete(
    "/{proxy_uuid}",
    summary="删除外部接口代理",
    response_description="删除结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def delete_proxy(
    proxy_uuid: UUID = Path(description="外部接口代理 UUID"),
    db: AsyncSession = Depends(get_db),
):
    """删除指定的外部接口代理配置。"""
    await external_api_proxy.delete_proxy(db, str(proxy_uuid))
    return {"message": "外部接口代理已删除"}
