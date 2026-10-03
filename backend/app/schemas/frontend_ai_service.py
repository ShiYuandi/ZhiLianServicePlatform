from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrontendAIServicePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    service_name: str = Field(
        alias="serviceName", description="前端 AI 服务显示名称", max_length=128
    )
    enabled: bool = Field(default=False, description="是否允许创建新的 AI 任务")
    remark: str | None = Field(default=None, description="服务备注", max_length=4000)
    rate_limit_per_minute: int = Field(
        default=60,
        alias="rateLimitPerMinute",
        description="每分钟最多创建的任务数",
        ge=1,
        le=100000,
    )
    max_inflight_tasks: int = Field(
        default=3,
        alias="maxInflightTasks",
        description="同时处于等待或处理中的最大任务数",
        ge=1,
        le=10000,
    )
    allowed_origins: list[str] = Field(
        default_factory=list,
        alias="allowedOrigins",
        description="允许的浏览器 Origin；空数组表示不限制，原生客户端不发送 Origin",
        max_length=100,
    )
    speech_model_id: int | None = Field(
        default=None,
        alias="speechModelId",
        description="绑定的语音识别模型编号；不需要语音能力时为空",
        ge=1,
    )
    image_model_id: int | None = Field(
        default=None,
        alias="imageModelId",
        description="绑定的图像生成模型编号；不需要图像能力时为空",
        ge=1,
    )

    @field_validator("service_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("服务名称不能为空")
        return value

    @field_validator("remark")
    @classmethod
    def clean_remark(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        for raw in value:
            origin = raw.strip().rstrip("/")
            parts = urlsplit(origin)
            if (
                parts.scheme not in {"http", "https"}
                or not parts.netloc
                or parts.path
                or parts.query
                or parts.fragment
            ):
                raise ValueError(
                    "允许访问域名必须是 http 或 https Origin，不能包含路径"
                )
            if origin not in result:
                result.append(origin)
        return result


class FrontendAIServiceCreate(FrontendAIServicePayload):
    """创建请求；服务编码由系统自动生成。"""


class FrontendAIServiceUpdate(FrontendAIServicePayload):
    pass


class FrontendAIServiceOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="前端 AI 服务编号")
    service_name: str = Field(alias="serviceName", description="服务显示名称")
    service_code: str = Field(alias="serviceCode", description="唯一服务编码")
    enabled: bool = Field(description="是否允许创建新的 AI 任务")
    remark: str | None = Field(description="服务备注")
    api_key_hint: str = Field(
        alias="apiKeyHint", description="服务 API Key 的不可逆显示提示"
    )
    api_key_version: int = Field(
        alias="apiKeyVersion", description="服务 API Key 当前版本"
    )
    rate_limit_per_minute: int = Field(
        alias="rateLimitPerMinute", description="每分钟任务上限"
    )
    max_inflight_tasks: int = Field(
        alias="maxInflightTasks", description="最大在途任务数"
    )
    allowed_origins: list[str] = Field(
        alias="allowedOrigins", description="允许的浏览器 Origin 列表"
    )
    speech_model_id: int | None = Field(
        alias="speechModelId", description="绑定的语音识别模型编号"
    )
    speech_model_name: str | None = Field(
        alias="speechModelName", description="绑定的语音识别模型名称"
    )
    speech_provider: str | None = Field(
        alias="speechProvider", description="语音识别模型供应器"
    )
    image_model_id: int | None = Field(
        alias="imageModelId", description="绑定的图像生成模型编号"
    )
    image_model_name: str | None = Field(
        alias="imageModelName", description="绑定的图像生成模型名称"
    )
    image_provider: str | None = Field(
        alias="imageProvider", description="图像生成模型供应器"
    )
    created_at: datetime = Field(alias="createdAt", description="创建时间")
    updated_at: datetime = Field(alias="updatedAt", description="最后更新时间")


class FrontendAIServiceCreated(FrontendAIServiceOut):
    api_key: str = Field(
        alias="apiKey", description="仅本次返回的服务 API Key，请立即安全保存"
    )


class FrontendAIServiceListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[FrontendAIServiceOut] = Field(description="当前页前端 AI 服务")
    page: int = Field(description="当前页码")
    page_size: int = Field(alias="pageSize", description="每页数量")
    total: int = Field(description="服务总数")


class FrontendAIServiceKeyRotated(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_key: str = Field(
        alias="apiKey", description="仅本次返回的新服务 API Key，请立即安全保存"
    )
    api_key_hint: str = Field(alias="apiKeyHint", description="新 Key 的显示提示")
    api_key_version: int = Field(alias="apiKeyVersion", description="新 Key 版本")


class FrontendAIServiceArchiveResponse(BaseModel):
    message: str = Field(description="归档结果")
