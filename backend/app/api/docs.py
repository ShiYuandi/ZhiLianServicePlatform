from app.schemas.common import ErrorResponse


SYSTEM_TAG = "系统状态"
PUBLIC_TAG = "前端公开接口"
AUTH_TAG = "管理员认证"
DASHBOARD_TAG = "后台概览"
QA_TAG = "问答管理"
XIAOZHI_SERVICE_TAG = "小智中间件服务"
LLM_PROXY_TAG = "大模型代理"
LLM_MODEL_TAG = "大语言模型管理"
SPEECH_MODEL_TAG = "语音识别模型管理"
IMAGE_MODEL_TAG = "图像生成模型管理"
FRONTEND_AI_SERVICE_TAG = "前端 AI 服务管理"
EXTERNAL_PROXY_TAG = "外部接口代理管理"
EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

OPENAPI_TAGS = [
    {"name": SYSTEM_TAG, "description": "检查中间件服务和 MySQL 数据库是否正常。"},
    {
        "name": PUBLIC_TAG,
        "description": "供数字人前端调用的设备添加代理、服务配置、图片、问答 Excel 和外部接口代理。",
    },
    {
        "name": AUTH_TAG,
        "description": "管理员登录、退出、会话查询和密码修改接口。",
    },
    {"name": DASHBOARD_TAG, "description": "读取后台首页所需的业务数据统计。"},
    {
        "name": QA_TAG,
        "description": "维护多张问答表、固定问答内容以及 Excel 导入导出。",
    },
    {
        "name": XIAOZHI_SERVICE_TAG,
        "description": "维护小智设备、数字人页面、可选问答表和大语言模型绑定。",
    },
    {
        "name": LLM_PROXY_TAG,
        "description": "供小智服务调用的 OpenAI 兼容接口；固定问答优先，未命中或未绑定问答表时转发外部大模型。",
    },
    {
        "name": LLM_MODEL_TAG,
        "description": "集中维护 OpenAI 和 Dify 大语言模型及其加密调用凭据。",
    },
    {
        "name": SPEECH_MODEL_TAG,
        "description": "集中维护百度短语音和火山豆包 ASR 模型及其加密调用凭据。",
    },
    {
        "name": IMAGE_MODEL_TAG,
        "description": "集中维护火山 Seedream 文生图和单图图生图模型及其加密调用凭据。",
    },
    {
        "name": FRONTEND_AI_SERVICE_TAG,
        "description": "维护供数字人前端调用的 AI 服务、一次性 API Key、安全限制和模型绑定。",
    },
    {
        "name": EXTERNAL_PROXY_TAG,
        "description": "配置上游接口网址并通过 UUID 原样转发请求，解决浏览器跨域访问问题。",
    },
]

VALIDATION_ERROR = {
    "description": "请求参数或请求体校验失败",
}
UNAUTHORIZED_ERROR = {
    "model": ErrorResponse,
    "description": "未登录、登录会话无效或会话已过期",
}
CSRF_ERROR = {
    "model": ErrorResponse,
    "description": "CSRF Token 缺失、不匹配或请求来源不受信任",
}
NOT_FOUND_ERROR = {
    "model": ErrorResponse,
    "description": "指定的服务、模型、图片、问答数据或设备映射不存在",
}
CONFLICT_ERROR = {
    "model": ErrorResponse,
    "description": "服务、模型、名称、问题或设备映射与已有数据冲突",
}

PUBLIC_RESPONSES = {422: VALIDATION_ERROR}
ADMIN_READ_RESPONSES = {
    401: UNAUTHORIZED_ERROR,
    422: VALIDATION_ERROR,
}
ADMIN_WRITE_RESPONSES = {
    401: UNAUTHORIZED_ERROR,
    403: CSRF_ERROR,
    422: VALIDATION_ERROR,
}
