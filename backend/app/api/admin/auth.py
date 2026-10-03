from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import create_csrf_token, create_session_token
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.models.admin_user import AdminUser
from app.schemas.auth import AdminProfile, LoginRequest, PasswordChangeRequest
from app.schemas.common import MessageResponse
from app.services.auth_service import (
    authenticate,
    change_password,
    clear_login_failures,
    ensure_login_allowed,
    record_login_failure,
)
from app.core.errors import AppError
from app.api.docs import (
    ADMIN_READ_RESPONSES,
    AUTH_TAG,
    CSRF_ERROR,
    UNAUTHORIZED_ERROR,
)


router = APIRouter(
    prefix="/api/admin/auth",
    tags=[AUTH_TAG],
    responses=ADMIN_READ_RESPONSES,
)


@router.post(
    "/login",
    summary="管理员登录",
    response_model=AdminProfile,
    response_description="管理员资料和 CSRF Token",
    responses={401: UNAUTHORIZED_ERROR, 429: {"description": "登录尝试过于频繁"}},
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """验证管理员账号密码，写入 HttpOnly 会话 Cookie，并返回 CSRF Token。"""

    client_key = request.client.host if request.client else "unknown"
    ensure_login_allowed(client_key)
    try:
        admin = await authenticate(db, payload.username, payload.password)
    except AppError:
        record_login_failure(client_key)
        raise
    clear_login_failures(client_key)
    token = create_session_token(admin.id, admin.session_version, settings)
    csrf = create_csrf_token()
    secure = (
        settings.auth_cookie_secure
        if settings.auth_cookie_secure is not None
        else settings.app_env == "production"
    )
    max_age = settings.auth_cookie_ttl_minutes * 60
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        "xz_csrf",
        csrf,
        httponly=False,
        secure=secure,
        samesite="strict",
        max_age=max_age,
        path="/",
    )
    return AdminProfile(id=admin.id, username=admin.username, csrf_token=csrf)


@router.post(
    "/logout",
    summary="退出管理员登录",
    response_model=MessageResponse,
    response_description="退出登录结果",
    responses={403: CSRF_ERROR},
    dependencies=[Depends(get_current_admin), Depends(require_csrf)],
)
async def logout(response: Response, settings: Settings = Depends(get_settings)):
    """清除管理员会话和 CSRF Cookie；请求头必须携带 X-CSRF-Token。"""

    response.delete_cookie(settings.auth_cookie_name, path="/")
    response.delete_cookie("xz_csrf", path="/")
    return MessageResponse(message="已退出登录")


@router.get(
    "/me",
    summary="获取当前管理员",
    response_model=AdminProfile,
    response_description="当前登录管理员资料",
)
async def me(request: Request, admin: AdminUser = Depends(get_current_admin)):
    """根据 HttpOnly 会话 Cookie 返回当前登录管理员和 CSRF Token。"""

    return AdminProfile(
        id=admin.id,
        username=admin.username,
        csrf_token=request.cookies.get("xz_csrf", ""),
    )


@router.put(
    "/password",
    summary="修改管理员密码",
    response_model=MessageResponse,
    response_description="密码修改结果",
    responses={403: CSRF_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_password(
    payload: PasswordChangeRequest,
    response: Response,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """校验当前密码后设置新密码，并立即清除现有会话，要求重新登录。"""

    await change_password(db, admin, payload.current_password, payload.new_password)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    response.delete_cookie("xz_csrf", path="/")
    return MessageResponse(message="密码已修改，请重新登录")
