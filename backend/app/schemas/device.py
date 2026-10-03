from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceAddRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "演示设备",
                "board": "esp32",
                "appVersion": "1.0.0",
                "macAddress": "00:11:22:33:44:55",
            }
        }
    )

    name: str = Field(
        description="设备名称，用于查找对应的 agentId", min_length=1, max_length=128
    )
    board: str = Field(description="设备主板型号", min_length=1, max_length=128)
    appVersion: str = Field(description="设备端应用版本", min_length=1, max_length=128)
    macAddress: str = Field(description="设备 MAC 地址", min_length=1, max_length=128)

    @field_validator("name", "board", "appVersion", "macAddress")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value
