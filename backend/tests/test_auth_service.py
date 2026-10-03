import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.admin_user import AdminUser
from app.services.auth_service import authenticate, change_password, initialize_admin


@pytest.mark.asyncio
async def test_admin_initialization_is_idempotent_and_password_change_invalidates_session(
    db,
):
    settings = get_settings()
    await initialize_admin(db, settings)
    await initialize_admin(db, settings)
    admins = list((await db.scalars(select(AdminUser))).all())
    assert len(admins) == 1
    admin = await authenticate(db, "admin", "development-password")
    old_version = admin.session_version
    await change_password(db, admin, "development-password", "new-secure-password")
    assert admin.session_version == old_version + 1
    with pytest.raises(AppError):
        await authenticate(db, "admin", "development-password")
    assert await authenticate(db, "admin", "new-secure-password")
