from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import (
    ADMIN_READ_RESPONSES,
    CONFLICT_ERROR,
    CSRF_ERROR,
    EXCEL_MEDIA_TYPE,
    NOT_FOUND_ERROR,
    QA_TAG,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.dependencies.auth import get_current_admin, require_csrf
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.qa import (
    ExcelImportResponse,
    QaBatchRequest,
    QaBatchResponse,
    QaItemCreate,
    QaItemListResponse,
    QaItemOut,
    QaTableCreate,
    QaTableListResponse,
    QaTableOut,
)
from app.services import qa_service
from app.services.excel_service import create_workbook, parse_workbook


router = APIRouter(
    prefix="/api/admin",
    tags=[QA_TAG],
    dependencies=[Depends(get_current_admin)],
    responses=ADMIN_READ_RESPONSES,
)


def table_out(table, item_count: int = 0) -> QaTableOut:
    return QaTableOut(
        id=table.id,
        name=table.name,
        description=table.description,
        item_count=item_count,
        created_at=table.created_at,
        updated_at=table.updated_at,
    )


@router.get(
    "/qa-tables",
    summary="分页查询问答表",
    response_model=QaTableListResponse,
    response_description="问答表分页结果",
)
async def list_tables(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="每页数量，最多 100 条"
    ),
    keyword: str | None = Query(
        default=None, description="按问答表名称搜索；忽略前后空格和大小写"
    ),
    db: AsyncSession = Depends(get_db),
):
    """分页查询后台维护的问答表；需要管理员登录。"""

    items, total = await qa_service.list_tables(db, page, page_size, keyword)
    return QaTableListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post(
    "/qa-tables",
    summary="新建问答表",
    response_model=QaTableOut,
    response_description="创建后的问答表",
    status_code=201,
    responses={403: CSRF_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_table(payload: QaTableCreate, db: AsyncSession = Depends(get_db)):
    """创建一张可独立维护和下载的问答表；写请求需要 CSRF 校验。"""

    table = await qa_service.create_table(db, payload)
    return table_out(table)


@router.put(
    "/qa-tables/{table_id}",
    summary="修改问答表",
    response_model=QaTableOut,
    response_description="更新后的问答表",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_table(
    payload: QaTableCreate,
    table_id: int = Path(description="要修改的问答表编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改指定问答表的名称和说明；写请求需要 CSRF 校验。"""

    table = await qa_service.update_table(db, table_id, payload)
    count = len(await qa_service.all_items(db, table_id))
    return table_out(table, count)


@router.delete(
    "/qa-tables/{table_id}",
    summary="删除问答表",
    response_model=MessageResponse,
    response_description="删除结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def delete_table(
    table_id: int = Path(description="要删除的问答表编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """永久删除问答表及表内全部问答项；写请求需要 CSRF 校验。"""

    await qa_service.delete_table(db, table_id)
    return MessageResponse(message="问答表已删除")


@router.get(
    "/qa-tables/{table_id}/items",
    summary="分页查询问答项",
    response_model=QaItemListResponse,
    response_description="问答项分页结果",
    responses={404: NOT_FOUND_ERROR},
)
async def list_items(
    table_id: int = Path(description="所属问答表编号", ge=1),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(
        default=50, ge=1, le=200, description="每页数量，最多 200 条"
    ),
    keyword: str | None = Query(
        default=None, description="同时搜索问题和固定答案；忽略前后空格和大小写"
    ),
    db: AsyncSession = Depends(get_db),
):
    """分页查询指定问答表中的假问题和固定答案；需要管理员登录。"""

    items, total = await qa_service.list_items(db, table_id, page, page_size, keyword)
    return QaItemListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post(
    "/qa-tables/{table_id}/items",
    summary="新增问答项",
    response_model=QaItemOut,
    response_description="创建后的问答项",
    status_code=201,
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def create_item(
    payload: QaItemCreate,
    table_id: int = Path(description="所属问答表编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """向指定问答表添加一条假问题和固定答案；重复判断忽略前后空格和大小写。"""

    return await qa_service.create_item(db, table_id, payload)


@router.put(
    "/qa-items/{item_id}",
    summary="修改问答项",
    response_model=QaItemOut,
    response_description="更新后的问答项",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def update_item(
    payload: QaItemCreate,
    item_id: int = Path(description="要修改的问答项编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """修改一条假问题、固定答案及显示顺序；写请求需要 CSRF 校验。"""

    return await qa_service.update_item(db, item_id, payload)


@router.delete(
    "/qa-items/{item_id}",
    summary="删除问答项",
    response_model=MessageResponse,
    response_description="删除结果",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def delete_item(
    item_id: int = Path(description="要删除的问答项编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """永久删除指定问答项；写请求必须携带 X-CSRF-Token。"""

    await qa_service.delete_item(db, item_id)
    return MessageResponse(message="问答项已删除")


@router.post(
    "/qa-tables/{table_id}/items/batch",
    summary="批量新增问答项",
    response_model=QaBatchResponse,
    response_description="批量添加结果和成功数量",
    responses={403: CSRF_ERROR, 404: NOT_FOUND_ERROR, 409: CONFLICT_ERROR},
    dependencies=[Depends(require_csrf)],
)
async def batch_items(
    payload: QaBatchRequest,
    table_id: int = Path(description="所属问答表编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """在一个事务中批量添加问答项；任意一条失败时整批回滚。"""

    items = await qa_service.batch_create_items(db, table_id, payload.items)
    return {"message": "批量添加成功", "count": len(items)}


@router.post(
    "/qa-tables/{table_id}/import",
    summary="从 Excel 导入问答项",
    response_model=ExcelImportResponse,
    response_description="Excel 导入结果、数量和模式",
    responses={
        403: CSRF_ERROR,
        404: NOT_FOUND_ERROR,
        409: CONFLICT_ERROR,
        413: {
            "model": ErrorResponse,
            "description": "Excel 文件超过 10 MiB",
        },
        415: {
            "model": ErrorResponse,
            "description": "上传的文件不是 .xlsx 格式",
        },
    },
    dependencies=[Depends(require_csrf)],
)
async def import_excel(
    table_id: int = Path(description="要导入数据的问答表编号", ge=1),
    mode: str = Query(
        default="append",
        pattern="^(append|replace)$",
        description="导入模式：append 追加，replace 清空原数据后替换",
    ),
    file: UploadFile = File(
        ...,
        description="两列表头为“问题、固定答案”的 .xlsx 文件，最大 10 MiB",
    ),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """导入两列 Excel；支持追加或替换，单次最多读取当前环境配置的最大行数。"""

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise AppError("INVALID_EXCEL_TYPE", "只允许上传 .xlsx 文件", 415)
    data = await file.read(settings.max_excel_bytes + 1)
    if len(data) > settings.max_excel_bytes:
        raise AppError("EXCEL_TOO_LARGE", "Excel 文件不能超过 10 MiB", 413)
    items = parse_workbook(data, settings.max_excel_rows)
    if mode == "replace":
        count = await qa_service.replace_items(db, table_id, items)
    else:
        count = len(await qa_service.batch_create_items(db, table_id, items))
    return {"message": "Excel 导入成功", "count": count, "mode": mode}


@router.get(
    "/qa-tables/{table_id}/export",
    summary="导出问答表 Excel",
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
async def export_excel(
    table_id: int = Path(description="要导出的问答表编号", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """将指定问答表实时生成两列 `.xlsx` 文件；需要管理员登录。"""

    table = await qa_service.get_table_or_404(db, table_id)
    items = await qa_service.all_items(db, table_id)
    data = create_workbook([(item.question, item.answer) for item in items])
    filename = f"{table.name}.xlsx"
    return Response(
        data,
        media_type=EXCEL_MEDIA_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote_filename(filename)}"
        },
    )


def quote_filename(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")
