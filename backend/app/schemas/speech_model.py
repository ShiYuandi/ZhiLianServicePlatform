from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.model_common import (
    ModelCommonPayload,
    ModelDetailCommon,
    clean_secret,
)


class SpeechBaiduPayload(ModelCommonPayload):
    provider: Literal["baidu"] = Field(description="供应器，固定为百度")
    app_id: str | None = Field(
        default=None, alias="appId", description="百度应用 AppID"
    )
    api_key: str | None = Field(
        default=None, alias="apiKey", description="百度 API Key；修改时留空保持原值"
    )
    secret_key: str | None = Field(
        default=None,
        alias="secretKey",
        description="百度 Secret Key；修改时留空保持原值",
    )
    dev_pid: int = Field(
        default=1537, alias="devPid", description="百度语音识别语言模型编号", ge=1
    )

    @field_validator("app_id", "api_key", "secret_key")
    @classmethod
    def clean_call_fields(cls, value: str | None) -> str | None:
        return clean_secret(value)


class SpeechVolcenginePayload(ModelCommonPayload):
    provider: Literal["volcengine"] = Field(description="供应器，固定为火山引擎")
    app_id: str | None = Field(
        default=None, alias="appId", description="火山应用 AppID"
    )
    access_token: str | None = Field(
        default=None,
        alias="accessToken",
        description="火山 Access Token；修改时留空保持原值",
    )
    resource_id: str | None = Field(
        default=None, alias="resourceId", description="豆包语音识别资源 ID"
    )
    language: str | None = Field(default=None, description="识别语言编码")
    boosting_table_name: str | None = Field(
        default=None, alias="boostingTableName", description="可选热词表名称"
    )
    correct_table_name: str | None = Field(
        default=None, alias="correctTableName", description="可选纠错表名称"
    )

    @field_validator(
        "app_id",
        "access_token",
        "resource_id",
        "language",
        "boosting_table_name",
        "correct_table_name",
    )
    @classmethod
    def clean_call_fields(cls, value: str | None) -> str | None:
        return clean_secret(value)


SpeechModelPayload = Annotated[
    SpeechBaiduPayload | SpeechVolcenginePayload, Field(discriminator="provider")
]


class SpeechBaiduOut(ModelDetailCommon):
    provider: Literal["baidu"] = Field(description="模型供应器")
    app_id: str | None = Field(alias="appId", description="百度应用 AppID")
    api_key_masked: str | None = Field(
        alias="apiKeyMasked", description="脱敏后的 API Key"
    )
    secret_key_masked: str | None = Field(
        alias="secretKeyMasked", description="脱敏后的 Secret Key"
    )
    dev_pid: int = Field(alias="devPid", description="百度语音识别语言模型编号")


class SpeechVolcengineOut(ModelDetailCommon):
    provider: Literal["volcengine"] = Field(description="模型供应器")
    app_id: str | None = Field(alias="appId", description="火山应用 AppID")
    access_token_masked: str | None = Field(
        alias="accessTokenMasked", description="脱敏后的 Access Token"
    )
    resource_id: str | None = Field(alias="resourceId", description="资源 ID")
    language: str | None = Field(description="识别语言编码")
    boosting_table_name: str | None = Field(
        alias="boostingTableName", description="热词表名称"
    )
    correct_table_name: str | None = Field(
        alias="correctTableName", description="纠错表名称"
    )


SpeechModelOut = Annotated[
    SpeechBaiduOut | SpeechVolcengineOut, Field(discriminator="provider")
]
