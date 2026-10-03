from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    message: str = Field(description="操作结果提示")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(description="稳定的错误代码", examples=["ERROR_CODE"])
    message: str = Field(description="可直接展示的中文错误信息")
    request_id: str = Field(
        alias="requestId",
        description="用于排查日志的请求编号",
        examples=["6f8b5bc2-3907-4b21-9a4e-7cc49b6c3a2f"],
    )


class Pagination(BaseModel):
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="符合条件的总记录数")


class HealthResponse(BaseModel):
    status: str = Field(description="服务运行状态", examples=["ok"])
    database: str = Field(description="数据库连接状态", examples=["ok"])


class DashboardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    qa_table_count: int = Field(alias="qaTableCount", description="问答表数量")
    qa_item_count: int = Field(alias="qaItemCount", description="问答项总数量")
    device_mapping_count: int = Field(
        alias="deviceMappingCount", description="设备映射数量"
    )
    database: str = Field(description="数据库连接状态", examples=["ok"])
