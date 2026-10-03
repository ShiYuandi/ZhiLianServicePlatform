from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal["pending", "processing", "succeeded", "failed", "expired"]
TaskType = Literal["speech_recognition", "image_generation"]


class AITaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    task_id: str = Field(alias="taskId", description="任务编号")
    task_type: TaskType = Field(alias="taskType", description="任务类型：语音识别或图像生成")
    status: TaskStatus = Field(description="任务状态")
    text: str | None = Field(default=None, description="语音识别文字")
    result_url: str | None = Field(default=None, alias="resultUrl", description="图像结果临时下载地址")
    error_code: str | None = Field(default=None, alias="errorCode", description="失败错误代码")
    error_message: str | None = Field(default=None, alias="errorMessage", description="失败原因")
    created_at: datetime = Field(alias="createdAt", description="提交时间")
    completed_at: datetime | None = Field(default=None, alias="completedAt", description="完成时间")
    result_expires_at: datetime | None = Field(default=None, alias="resultExpiresAt", description="结果过期时间")
    result: dict | None = Field(default=None, description="成功结果；语音包含 text，图像包含 imageUrl 和 expiresAt")


class ServiceConfigOut(BaseModel):
    service_name: str = Field(alias="serviceName", description="服务名称")
    service_code: str = Field(alias="serviceCode", description="服务编码")
    enabled: bool = Field(description="是否启用")
    capabilities: list[str] = Field(description="已绑定能力")
    api_version: str = Field(alias="apiVersion", default="v1", description="接口版本")


class ImageTaskOptions(BaseModel):
    width: int | None = Field(default=None, ge=64, le=4096, description="目标宽度")
    height: int | None = Field(default=None, ge=64, le=4096, description="目标高度")
