from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import ADMIN_READ_RESPONSES, DASHBOARD_TAG
from app.db.session import get_db
from app.dependencies.auth import get_current_admin
from app.models.device_mapping import DeviceMapping
from app.models.qa import QaItem, QaTable
from app.schemas.common import DashboardResponse


router = APIRouter(
    prefix="/api/admin/dashboard",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


@router.get(
    "",
    summary="获取后台数据概览",
    response_model=DashboardResponse,
    response_description="问答表、问答项和设备映射数量",
)
async def dashboard(db: AsyncSession = Depends(get_db)):
    """返回后台首页展示的业务记录数量和数据库状态；需要管理员登录。"""

    return {
        "qaTableCount": int(await db.scalar(select(func.count(QaTable.id))) or 0),
        "qaItemCount": int(await db.scalar(select(func.count(QaItem.id))) or 0),
        "deviceMappingCount": int(
            await db.scalar(select(func.count(DeviceMapping.id))) or 0
        ),
        "database": "ok",
    }
