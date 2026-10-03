from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.model_common import (
    ModelCommonPayload,
    ModelDetailCommon,
    clean_secret,
)


class ImageVolcenginePayload(ModelCommonPayload):
    provider: Literal["volcengine"] = Field(description="供应器，固定为火山引擎")
    api_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3/images/generations",
        alias="apiUrl",
        description="火山方舟图片生成 API 地址",
        max_length=512,
    )
    api_key: str | None = Field(
        default=None, alias="apiKey", description="火山 API Key；修改时留空保持原值"
    )
    upstream_model: str | None = Field(
        default=None, alias="upstreamModel", description="Seedream 实际模型 ID"
    )
    default_width: int = Field(
        default=1024, alias="defaultWidth", description="默认生成宽度", ge=256, le=4096
    )
    default_height: int = Field(
        default=1024, alias="defaultHeight", description="默认生成高度", ge=256, le=4096
    )
    timeout_seconds: float = Field(
        default=120.0,
        alias="timeoutSeconds",
        description="请求超时秒数",
        gt=0,
        le=900,
    )
    watermark: bool = Field(default=False, description="生成图片是否添加水印")

    @field_validator("api_url", "api_key", "upstream_model")
    @classmethod
    def clean_call_fields(cls, value: str | None) -> str | None:
        return clean_secret(value)


ImageModelPayload = Annotated[ImageVolcenginePayload, Field(discriminator="provider")]


class ImageVolcengineOut(ModelDetailCommon):
    provider: Literal["volcengine"] = Field(description="模型供应器")
    api_url: str = Field(alias="apiUrl", description="火山方舟图片生成 API 地址")
    api_key_masked: str | None = Field(
        alias="apiKeyMasked", description="脱敏后的 API Key"
    )
    upstream_model: str | None = Field(alias="upstreamModel", description="实际模型 ID")
    default_width: int = Field(alias="defaultWidth", description="默认生成宽度")
    default_height: int = Field(alias="defaultHeight", description="默认生成高度")
    timeout_seconds: float = Field(alias="timeoutSeconds", description="请求超时秒数")
    watermark: bool = Field(description="生成图片是否添加水印")


ImageModelOut = ImageVolcengineOut
