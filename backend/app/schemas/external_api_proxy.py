from __future__ import annotations

from datetime import datetime
from uuid import UUID
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_target_url(value: str) -> str:
    value = value.strip()
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.netloc
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise ValueError("上游网址必须是 http 或 https 地址，不能包含账号密码或片段")
    return value


class ExternalApiProxyPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    target_url: str = Field(
        alias="targetUrl",
        description="上游接口完整网址，平台会透传请求并原样返回响应",
        min_length=8,
        max_length=2048,
    )
    enabled: bool = Field(default=True, description="是否允许公开转发")

    @field_validator("target_url")
    @classmethod
    def clean_target_url(cls, value: str) -> str:
        return validate_target_url(value)


class ExternalApiProxyCreate(ExternalApiProxyPayload):
    pass


class ExternalApiProxyUpdate(ExternalApiProxyPayload):
    pass


class ExternalApiProxyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    proxy_uuid: UUID = Field(alias="proxyUuid", description="公开访问 UUID")
    target_url: str = Field(alias="targetUrl", description="上游接口网址")
    enabled: bool = Field(description="是否启用公开转发")
    created_at: datetime = Field(alias="createdAt", description="创建时间")
    updated_at: datetime = Field(alias="updatedAt", description="最后更新时间")


class ExternalApiProxyListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ExternalApiProxyOut] = Field(description="外部接口代理列表")
    page: int = Field(description="当前页码")
    page_size: int = Field(alias="pageSize", description="每页数量")
    total: int = Field(description="代理总数")
