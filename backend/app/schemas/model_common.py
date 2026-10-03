from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


MODEL_CODE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


class ModelCommonPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    model_name: str = Field(
        alias="modelName", description="模型显示名称", max_length=128
    )
    model_code: str | None = Field(
        alias="modelCode",
        description="平台内部唯一编码，不需要填写；留空时自动生成",
        default=None,
        min_length=2,
        max_length=64,
    )
    sort_order: int = Field(default=0, alias="sortOrder", description="列表显示顺序")
    doc_url: str | None = Field(
        default=None, alias="docUrl", description="供应器或模型文档地址", max_length=512
    )
    remark: str | None = Field(default=None, description="模型备注", max_length=4000)
    enabled: bool = Field(default=True, description="是否启用模型")

    @field_validator("model_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("模型名称不能为空")
        return value

    @field_validator("model_code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not MODEL_CODE_PATTERN.fullmatch(value):
            raise ValueError("模型编码只能使用小写字母、数字和短横线")
        return value

    @field_validator("doc_url", "remark")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ModelListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="模型编号")
    model_name: str = Field(alias="modelName", description="模型显示名称")
    model_code: str = Field(alias="modelCode", description="模型唯一编码")
    provider: str = Field(description="模型供应器编码")
    sort_order: int = Field(alias="sortOrder", description="列表显示顺序")
    enabled: bool = Field(description="是否启用模型")
    updated_at: datetime = Field(alias="updatedAt", description="最后更新时间")


class ModelListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ModelListItem] = Field(description="当前页模型")
    page: int = Field(description="当前页码")
    page_size: int = Field(alias="pageSize", description="每页数量")
    total: int = Field(description="模型总数")


class ModelDetailCommon(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="模型编号")
    model_name: str = Field(alias="modelName", description="模型显示名称")
    model_code: str = Field(alias="modelCode", description="模型唯一编码")
    sort_order: int = Field(alias="sortOrder", description="列表显示顺序")
    doc_url: str | None = Field(alias="docUrl", description="供应器或模型文档地址")
    remark: str | None = Field(description="模型备注")
    enabled: bool = Field(description="是否启用模型")
    credential_configured: bool = Field(
        alias="credentialConfigured", description="调用所需密钥是否已完整配置"
    )
    created_at: datetime = Field(alias="createdAt", description="创建时间")
    updated_at: datetime = Field(alias="updatedAt", description="最后更新时间")


class ModelStatusUpdate(BaseModel):
    enabled: bool = Field(description="是否启用模型")


class ModelStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(description="启停操作结果")
    enabled: bool = Field(description="操作后的启用状态")
    affected_service_count: int = Field(
        alias="affectedServiceCount", description="受到影响的服务数量"
    )


class ModelArchiveResponse(BaseModel):
    message: str = Field(description="归档操作结果")


class ModelConnectionTestResponse(BaseModel):
    success: bool = Field(description="连接测试是否成功")
    message: str = Field(description="连接测试中文结果")


def clean_secret(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def generated_model_code(model_name: str, provider: str) -> str:
    """生成仅供平台内部使用的稳定可读编码。"""
    slug = re.sub(r"[^a-z0-9]+", "-", model_name.lower()).strip("-")[:40]
    return f"{provider}-{slug or 'model'}-{uuid.uuid4().hex[:8]}"
