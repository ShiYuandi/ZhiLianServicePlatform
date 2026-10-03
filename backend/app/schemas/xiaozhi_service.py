from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


XIAOZHI_SERVICE_CODE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
XIAOZHI_SERVICE_IMAGE_SLOTS = (
    "background_icon",
    "wake_icon",
    "menu_background",
    "keyboard_icon",
    "voice_icon",
    "home_icon",
    "hold_to_talk_background",
    "send_icon",
)
XIAOZHI_SERVICE_VIDEO_SLOTS = (
    "standing_video",
    "thinking_video",
    "speaking_video",
)
XIAOZHI_SERVICE_ASSET_SLOTS = (
    *XIAOZHI_SERVICE_IMAGE_SLOTS,
    *XIAOZHI_SERVICE_VIDEO_SLOTS,
)


def clean_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name}不能为空")
    return value


def clean_string_array(value: list[str]) -> list[str]:
    cleaned = [item.strip() for item in value]
    if any(not item for item in cleaned):
        raise ValueError("数组项不能包含空字符串")
    return cleaned


class XiaozhiServiceBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    service_name: str = Field(
        alias="serviceName", description="小智中间件服务显示名称", max_length=128
    )
    digital_human_name: str | None = Field(
        default=None,
        alias="digitalHumanName",
        description="数字人名称，可为空",
        max_length=128,
    )
    title: str = Field(description="数字人首页标题", max_length=255)
    subtitle: str | None = Field(
        default=None, description="数字人首页副标题", max_length=255
    )
    questions: list[str] = Field(
        default_factory=list, description="首页推荐问题字符串数组", max_length=100
    )
    voice_wakeup_enabled: bool = Field(
        default=False, alias="voiceWakeupEnabled", description="是否启用语音唤醒"
    )
    wake_word: str | None = Field(
        default=None, alias="wakeWord", description="语音唤醒词", max_length=255
    )
    wake_listening_texts: list[str] = Field(
        default_factory=list,
        alias="wakeListeningTexts",
        description="唤醒词监听文字字符串数组",
        max_length=100,
    )
    wake_requirement_count: int = Field(
        default=0,
        alias="wakeRequirementCount",
        description="唤醒需求数量，仅按非负整数透传",
        ge=0,
    )
    device_name: str = Field(
        alias="agentName", description="设备名称，同时作为 agentName", max_length=128
    )
    agent_id: str = Field(
        alias="agentId",
        description="设备映射中的小智 agentId，32 位十六进制字符串",
        min_length=32,
        max_length=32,
    )
    device_enabled: bool = Field(
        default=True, alias="deviceEnabled", description="设备映射是否启用"
    )
    qa_table_id: int | None = Field(
        default=None,
        alias="qaTableId",
        description="可选的固定问答表编号；未绑定时直接调用大语言模型",
        ge=1,
    )
    ai_reply_enabled: bool = Field(
        default=True,
        alias="aiReplyEnabled",
        description="问答表未命中时是否调用真实大模型；关闭时返回默认回复词",
    )
    default_reply_text: str | None = Field(
        default=None,
        alias="defaultReplyText",
        description="默认回复词；关闭真实大模型且问答未命中时返回",
        max_length=255,
    )
    llm_model_id: int | None = Field(
        default=None,
        alias="llmModelId",
        description="绑定的大语言模型编号；草稿可为空，开启真实大模型时发布必填",
        ge=1,
    )

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, value: str) -> str:
        return clean_text(value, "服务名称")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return clean_text(value, "标题")

    @field_validator("digital_human_name", "subtitle", "wake_word", "default_reply_text")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("questions", "wake_listening_texts")
    @classmethod
    def validate_string_arrays(cls, value: list[str]) -> list[str]:
        return clean_string_array(value)

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{32}", value):
            raise ValueError("agentId 必须是 32 位十六进制字符串")
        return value

    @field_validator("device_name")
    @classmethod
    def validate_device_name(cls, value: str) -> str:
        return clean_text(value, "设备名称")


class XiaozhiServiceCreate(XiaozhiServiceBase):
    service_code: str | None = Field(
        alias="serviceCode",
        default=None,
        description="系统内部服务标识，留空时自动生成",
        min_length=2,
        max_length=64,
    )

    @field_validator("service_code")
    @classmethod
    def validate_service_code(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not XIAOZHI_SERVICE_CODE_PATTERN.fullmatch(value):
            raise ValueError("服务编码只能使用小写字母、数字和短横线")
        return value


class XiaozhiServiceUpdate(XiaozhiServiceBase):
    pass


class XiaozhiServiceAssetOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="媒体资产编号")
    slot: str = Field(description="图片或视频位置编码")
    original_filename: str = Field(alias="originalFilename", description="原始文件名")
    content_type: str = Field(alias="contentType", description="媒体 MIME 类型")
    size_bytes: int = Field(alias="sizeBytes", description="媒体大小，单位字节")
    etag: str = Field(description="媒体版本标识")
    url: str = Field(description="通过中间件访问的媒体地址")


class XiaozhiServiceOut(XiaozhiServiceBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(description="小智中间件服务编号")
    service_code: str = Field(alias="serviceCode", description="唯一服务编码")
    published: bool = Field(description="是否已发布")
    completeness: int = Field(description="配置完整度百分比")
    assets: list[XiaozhiServiceAssetOut] = Field(description="服务图片和视频资产")
    created_at: datetime = Field(alias="createdAt", description="创建时间")
    updated_at: datetime = Field(alias="updatedAt", description="最后更新时间")
    qa_table_name: str | None = Field(
        default=None, alias="qaTableName", description="绑定问答表名称"
    )
    llm_model_name: str | None = Field(
        default=None, alias="llmModelName", description="绑定的大语言模型名称"
    )
    llm_provider: str | None = Field(
        default=None, alias="llmProvider", description="绑定的大语言模型供应器"
    )
    llm_enabled: bool | None = Field(
        default=None, alias="llmEnabled", description="绑定的大语言模型是否启用"
    )
    llm_configured: bool = Field(
        alias="llmConfigured", description="绑定的大语言模型调用凭据是否完整"
    )


class XiaozhiServiceListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="小智中间件服务编号")
    service_code: str = Field(alias="serviceCode", description="唯一服务编码")
    service_name: str = Field(alias="serviceName", description="服务显示名称")
    digital_human_name: str | None = Field(
        default=None, alias="digitalHumanName", description="数字人名称，可为空"
    )
    device_name: str = Field(alias="agentName", description="关联设备名称")
    agent_id: str = Field(alias="agentId", description="关联小智 agentId")
    device_enabled: bool = Field(alias="deviceEnabled", description="设备映射是否启用")
    published: bool = Field(description="是否已发布")
    completeness: int = Field(description="配置完整度百分比")
    updated_at: datetime = Field(alias="updatedAt", description="最后更新时间")
    qa_table_id: int | None = Field(
        default=None, alias="qaTableId", description="绑定问答表编号"
    )
    qa_table_name: str | None = Field(
        default=None, alias="qaTableName", description="绑定问答表名称"
    )
    ai_reply_enabled: bool = Field(
        default=True,
        alias="aiReplyEnabled",
        description="问答表未命中时是否调用真实大模型",
    )
    default_reply_text: str | None = Field(
        default=None, alias="defaultReplyText", description="默认回复词"
    )
    llm_model_id: int | None = Field(
        default=None, alias="llmModelId", description="绑定的大语言模型编号"
    )
    llm_model_name: str | None = Field(
        default=None, alias="llmModelName", description="绑定的大语言模型名称"
    )
    llm_provider: str | None = Field(
        default=None, alias="llmProvider", description="绑定的大语言模型供应器"
    )
    llm_configured: bool = Field(
        default=False, alias="llmConfigured", description="大语言模型调用凭据是否完整"
    )


class XiaozhiServiceListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[XiaozhiServiceListItem] = Field(description="当前页小智中间件服务")
    page: int = Field(description="当前页码")
    page_size: int = Field(alias="pageSize", description="每页数量")
    total: int = Field(description="小智中间件服务总数")


class PublicXiaozhiServiceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    service_name: str = Field(alias="serviceName", description="前端显示名称")
    digital_human_name: str | None = Field(
        default=None, alias="digitalHumanName", description="数字人名称，可为空"
    )
    title: str = Field(description="数字人首页标题")
    subtitle: str | None = Field(description="数字人首页副标题")
    questions: list[str] = Field(description="首页推荐问题数组")
    background_icon_url: str | None = Field(
        default=None, alias="backgroundIconUrl", description="背景图标地址"
    )
    wake_icon_url: str | None = Field(
        default=None, alias="wakeIconUrl", description="唤醒图标地址"
    )
    menu_background_url: str | None = Field(
        default=None, alias="menuBackgroundUrl", description="菜单栏背景地址"
    )
    keyboard_icon_url: str | None = Field(
        default=None, alias="keyboardIconUrl", description="键盘图标地址"
    )
    voice_icon_url: str | None = Field(
        default=None, alias="voiceIconUrl", description="语音图标地址"
    )
    home_icon_url: str | None = Field(
        default=None, alias="homeIconUrl", description="首页图标地址"
    )
    hold_to_talk_background_url: str | None = Field(
        default=None,
        alias="holdToTalkBackgroundUrl",
        description="长按说话背景图标地址",
    )
    send_icon_url: str | None = Field(
        default=None, alias="sendIconUrl", description="点击发送图标地址"
    )
    standing_video_url: str | None = Field(
        default=None, alias="standingVideoUrl", description="站立视频地址"
    )
    thinking_video_url: str | None = Field(
        default=None, alias="thinkingVideoUrl", description="思考视频地址"
    )
    speaking_video_url: str | None = Field(
        default=None, alias="speakingVideoUrl", description="说话视频地址"
    )
    voice_wakeup_enabled: bool = Field(
        alias="voiceWakeupEnabled", description="是否启用语音唤醒"
    )
    wake_word: str | None = Field(alias="wakeWord", description="唤醒词")
    wake_listening_texts: list[str] = Field(
        alias="wakeListeningTexts", description="唤醒词监听文字数组"
    )
    wake_requirement_count: int = Field(
        alias="wakeRequirementCount", description="唤醒需求数量"
    )
    agent_id: str = Field(alias="agentId", description="数字人 agentId")
    agent_name: str = Field(alias="agentName", description="数字人设备名称")


class PublicXiaozhiServiceNameList(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    service_names: list[str] = Field(
        alias="serviceNames", description="已发布的小智中间件服务名称列表"
    )


class XiaozhiServiceAssetUploadResponse(BaseModel):
    asset: XiaozhiServiceAssetOut = Field(description="上传后的媒体资产")
