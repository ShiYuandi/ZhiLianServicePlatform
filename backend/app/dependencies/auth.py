from fastapi import Cookie, Depends, Header, Request
from urllib.parse import urlparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_session_token
from app.db.session import get_db
from app.models.admin_user import AdminUser


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminUser:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise AppError("UNAUTHORIZED", "请先登录", 401)
    admin_id, session_version = decode_session_token(token, settings)
    admin = await db.scalar(select(AdminUser).where(AdminUser.id == admin_id))
    if not admin or admin.session_version != session_version:
        raise AppError("UNAUTHORIZED", "登录已失效，请重新登录", 401)
    return admin


async def require_csrf(
    request: Request,
    settings: Settings = Depends(get_settings),
    csrf_header: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
        description="登录响应中的 CSRF Token；后台写请求必须携带",
    ),
    csrf_cookie: str | None = Cookie(
        default=None,
        alias="xz_csrf",
        description="登录成功后由服务自动写入的 CSRF Cookie",
    ),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("Origin")
    host = request.headers.get("Host")
    if origin and host:
        origin_netloc = urlparse(origin).netloc.casefold()
        configured_origins = {
            item.rstrip("/").casefold()
            for item in settings.cors_origin_list
            if item != "*"
        }
        if (
            "*" not in settings.cors_origin_list
            and origin_netloc != host.casefold()
            and origin.rstrip("/").casefold() not in configured_origins
        ):
            raise AppError("CSRF_FAILED", "请求来源不受信任", 403)
    if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
        raise AppError("CSRF_FAILED", "安全校验失败，请刷新页面后重试", 403)
