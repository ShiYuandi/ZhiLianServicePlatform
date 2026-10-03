from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def clean_required(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("字段不能为空")
    return value


class QaTableCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "展馆讲解", "description": "展馆数字人固定问答"}
        }
    )

    name: str = Field(
        description="问答表名称，公开下载时作为表名", min_length=1, max_length=128
    )
    description: str | None = Field(
        default=None, description="问答表用途说明", max_length=255
    )

    _clean_name = field_validator("name")(clean_required)


class QaTableUpdate(QaTableCreate):
    pass


class QaTableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="问答表编号")
    name: str = Field(description="问答表名称")
    description: str | None = Field(description="问答表用途说明")
    item_count: int = Field(default=0, description="表内问答项数量")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")


class QaItemCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "开放时间是什么时候？",
                "answer": "开放时间为每天上午九点到下午五点。",
                "sort_order": 0,
            }
        }
    )

    question: str = Field(
        description="前端用于匹配的假问题", min_length=1, max_length=1000
    )
    answer: str = Field(
        description="匹配成功后返回的固定答案", min_length=1, max_length=20000
    )
    sort_order: int = Field(default=0, description="显示顺序，数值越小越靠前", ge=0)

    _clean_question = field_validator("question")(clean_required)
    _clean_answer = field_validator("answer")(clean_required)


class QaItemUpdate(QaItemCreate):
    pass


class QaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="问答项编号")
    table_id: int = Field(description="所属问答表编号")
    question: str = Field(description="前端用于匹配的假问题")
    answer: str = Field(description="匹配成功后返回的固定答案")
    sort_order: int = Field(description="显示顺序")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")


class QaBatchRequest(BaseModel):
    items: list[QaItemCreate] = Field(
        description="要批量新增的问答项，单次最多 10000 条",
        min_length=1,
        max_length=10000,
    )


class QaBatchResponse(BaseModel):
    message: str = Field(description="批量操作结果提示")
    count: int = Field(description="成功写入的问答项数量")


class ExcelImportResponse(QaBatchResponse):
    mode: str = Field(description="本次导入模式：append 追加或 replace 替换")


class QaTableListResponse(BaseModel):
    items: list[QaTableOut] = Field(description="当前页问答表")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="符合条件的问答表总数")


class QaItemListResponse(BaseModel):
    items: list[QaItemOut] = Field(description="当前页问答项")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="符合条件的问答项总数")
