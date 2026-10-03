from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"username": "admin", "password": "示例密码，请替换"}
        }
    )

    username: str = Field(description="管理员账号", min_length=1, max_length=64)
    password: str = Field(description="管理员密码", min_length=1, max_length=256)


class AdminProfile(BaseModel):
    id: int = Field(description="管理员编号")
    username: str = Field(description="管理员账号")
    csrf_token: str = Field(description="后台写请求需要携带的 CSRF Token")


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "当前示例密码",
                "new_password": "新的示例密码123",
            }
        }
    )

    current_password: str = Field(
        description="当前管理员密码", min_length=1, max_length=256
    )
    new_password: str = Field(
        description="新密码，至少 10 个字符", min_length=10, max_length=256
    )
