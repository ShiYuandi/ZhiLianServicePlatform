import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.admin_user import AdminUser


_login_attempts: dict[str, list[float]] = {}
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 5


def ensure_login_allowed(key: str) -> None:
    now = time.monotonic()
    attempts = [
        stamp
        for stamp in _login_attempts.get(key, [])
        if now - stamp < LOGIN_WINDOW_SECONDS
    ]
    _login_attempts[key] = attempts
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise AppError("LOGIN_RATE_LIMITED", "登录失败次数过多，请稍后再试", 429)


def record_login_failure(key: str) -> None:
    _login_attempts.setdefault(key, []).append(time.monotonic())


def clear_login_failures(key: str) -> None:
    _login_attempts.pop(key, None)


async def initialize_admin(db: AsyncSession, settings: Settings) -> None:
    count = await db.scalar(select(func.count(AdminUser.id)))
    if count:
        return
    if (
        not settings.admin_initial_password
        or settings.admin_initial_password.startswith("replace-with-")
    ):
        if settings.app_env == "production":
            raise RuntimeError("首次启动缺少 ADMIN_INITIAL_PASSWORD")
        return
    admin = AdminUser(
        username=settings.admin_initial_username.strip(),
        password_hash=hash_password(settings.admin_initial_password),
    )
    db.add(admin)
    await db.commit()


async def authenticate(db: AsyncSession, username: str, password: str) -> AdminUser:
    admin = await db.scalar(
        select(AdminUser).where(AdminUser.username == username.strip())
    )
    if not admin or not verify_password(password, admin.password_hash):
        raise AppError("INVALID_CREDENTIALS", "账号或密码错误", 401)
    return admin


async def change_password(
    db: AsyncSession, admin: AdminUser, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, admin.password_hash):
        raise AppError("INVALID_CURRENT_PASSWORD", "当前密码错误", 400)
    if current_password == new_password:
        raise AppError("PASSWORD_UNCHANGED", "新密码不能与当前密码相同", 400)
    admin.password_hash = hash_password(new_password)
    admin.session_version += 1
    await db.commit()
