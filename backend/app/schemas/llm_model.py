from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.model_common import (
    ModelCommonPayload,
    ModelDetailCommon,
    clean_secret,
)


class LLMOpenAIPayload(ModelCommonPayload):
    provider: Literal["openai"] = Field(description="供应器，固定为 OpenAI")
    base_url: str | None = Field(
        default=None, alias="baseUrl", description="OpenAI 兼容基础地址", max_length=512
    )
    upstream_model: str | None = Field(
        default=None, alias="upstreamModel", description="上游模型名称", max_length=128
    )
    api_key: str | None = Field(
        default=None,
        alias="apiKey",
        description="OpenAI API Key；修改时留空表示保持原值",
        max_length=4096,
    )
    timeout_seconds: float = Field(
        default=30.0,
        alias="timeoutSeconds",
        description="请求超时秒数",
        gt=0,
        le=600,
    )

    @field_validator("base_url", "upstream_model", "api_key")
    @classmethod
    def clean_call_fields(cls, value: str | None) -> str | None:
        return clean_secret(value)


class LLMDifyPayload(ModelCommonPayload):
    provider: Literal["dify"] = Field(description="供应器，固定为 Dify")
    base_url: str | None = Field(
        default=None, alias="baseUrl", description="Dify API 基础地址", max_length=512
    )
    mode: Literal["chat-messages", "workflows/run"] | None = Field(
        default=None, description="Dify 应用模式"
    )
    api_key: str | None = Field(
        default=None,
        alias="apiKey",
        description="Dify API Key；修改时留空表示保持原值",
        max_length=4096,
    )
    timeout_seconds: float = Field(
        default=30.0,
        alias="timeoutSeconds",
        description="请求超时秒数",
        gt=0,
        le=600,
    )

    @field_validator("base_url", "api_key")
    @classmethod
    def clean_call_fields(cls, value: str | None) -> str | None:
        return clean_secret(value)


LLMModelPayload = Annotated[
    LLMOpenAIPayload | LLMDifyPayload, Field(discriminator="provider")
]


class LLMOpenAIOut(ModelDetailCommon):
    provider: Literal["openai"] = Field(description="模型供应器")
    base_url: str | None = Field(alias="baseUrl", description="OpenAI 兼容基础地址")
    upstream_model: str | None = Field(
        alias="upstreamModel", description="上游模型名称"
    )
    api_key_masked: str | None = Field(
        alias="apiKeyMasked", description="脱敏后的 API Key"
    )
    timeout_seconds: float = Field(alias="timeoutSeconds", description="请求超时秒数")


class LLMDifyOut(ModelDetailCommon):
    provider: Literal["dify"] = Field(description="模型供应器")
    base_url: str | None = Field(alias="baseUrl", description="Dify API 基础地址")
    mode: Literal["chat-messages", "workflows/run"] | None = Field(
        description="Dify 应用模式"
    )
    api_key_masked: str | None = Field(
        alias="apiKeyMasked", description="脱敏后的 API Key"
    )
    timeout_seconds: float = Field(alias="timeoutSeconds", description="请求超时秒数")


LLMModelOut = Annotated[LLMOpenAIOut | LLMDifyOut, Field(discriminator="provider")]
