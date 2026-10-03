from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "user", "assistant", "tool"]
    content: Any = Field(description="消息正文；通常为字符串")


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(description="小智中间件服务编码")
    messages: list[ChatMessage] = Field(min_length=1, description="对话消息列表")
    stream: bool = Field(default=False, description="是否以 SSE 流式返回")

    @field_validator("model")
    @classmethod
    def clean_model(cls, value: str) -> str:
        return value.strip()
