from urllib.parse import quote
from typing import Any

from fastapi import APIRouter, Depends, Path
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.api.docs import (
    EXCEL_MEDIA_TYPE,
    NOT_FOUND_ERROR,
    PUBLIC_RESPONSES,
    PUBLIC_TAG,
)
from app.db.session import get_db
from app.schemas.common import ErrorResponse
from app.schemas.device import DeviceAddRequest
from app.services import device_service, qa_service
from app.services.excel_service import create_workbook


router = APIRouter(
    prefix="/api",
    tags=[PUBLIC_TAG],
    responses=PUBLIC_RESPONSES,
)


@router.post(
    "/device/add",
    summary="代理添加小智设备",
    response_model=dict[str, Any],
    response_description="小智平台返回的设备添加结果",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "设备名称没有可用映射，或小智平台拒绝了请求",
        },
        502: {
            "model": ErrorResponse,
            "description": "小智平台请求失败或返回了无效数据",
        },
        504: {
            "model": ErrorResponse,
            "description": "请求小智平台超时",
        },
    },
)
async def add_device(
    payload: DeviceAddRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """根据设备名称补充数据库中维护的 agentId，再代理调用并原样返回小智平台的 JSON。"""

    return await device_service.add_device(db, payload, settings)


@router.get(
    "/tables/{table_name}/download",
    summary="按表名下载问答 Excel",
    response_class=Response,
    response_description="包含“问题、固定答案”两列的 Excel 文件",
    responses={
        200: {
            "description": "成功生成并下载问答 Excel 文件",
            "content": {
                EXCEL_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}
            },
        },
        404: NOT_FOUND_ERROR,
    },
)
async def download_table(
    table_name: str = Path(description="后台维护的问答表名称"),
    db: AsyncSession = Depends(get_db),
):
    """公开下载指定问答表；Excel 表头固定为“问题”和“固定答案”。"""

    table = await qa_service.get_table_by_name(db, table_name)
    items = await qa_service.all_items(db, table.id)
    data = create_workbook([(item.question, item.answer) for item in items])
    filename = quote(f"{table.name}.xlsx", safe="")
    return Response(
        data,
        media_type=EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
