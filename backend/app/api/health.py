from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.errors import AppError
from app.api.docs import SYSTEM_TAG
from app.schemas.common import ErrorResponse, HealthResponse


router = APIRouter(tags=[SYSTEM_TAG])


@router.get(
    "/health",
    summary="检查服务健康状态",
    response_model=HealthResponse,
    response_description="服务和数据库均正常",
    responses={
        503: {"model": ErrorResponse, "description": "数据库连接异常"},
    },
)
async def health(db: AsyncSession = Depends(get_db)):
    """检查中间件进程是否可用，并执行一次数据库连接测试。"""

    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError("DATABASE_UNAVAILABLE", "数据库连接异常", 503) from exc
    return {"status": "ok", "database": "ok"}
