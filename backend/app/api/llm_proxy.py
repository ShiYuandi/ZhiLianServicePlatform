from __future__ import annotations

import hmac
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs import LLM_PROXY_TAG
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.llm_proxy import ChatCompletionRequest
from app.services import llm_proxy_service


router = APIRouter(prefix="/v1", tags=[LLM_PROXY_TAG])


def _app_error(exc: AppError) -> JSONResponse:
    error_type = (
        "authentication_error" if exc.status_code == 401 else "invalid_request_error"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"message": exc.message, "type": error_type, "code": exc.code}
        },
    )


async def require_proxy_key(
    authorization: str | None = None,
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.llm_proxy_api_key
    if not expected or not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "代理访问密钥无效", 401)
    supplied = authorization[7:].strip()
    if not hmac.compare_digest(supplied, expected):
        raise AppError("UNAUTHORIZED", "代理访问密钥无效", 401)


@router.post(
    "/chat/completions",
    summary="OpenAI 兼容大模型代理",
    description="绑定问答表时优先返回固定答案（支持高相似度模糊匹配，差异字符含否定词时不命中）；未命中时若服务开启真实大模型则调用外部大模型，否则返回服务配置的默认回复词。",
    response_description="非流式 JSON 或流式 SSE 结果",
    responses={
        200: {"description": "非流式 JSON 或流式 SSE 大模型结果"},
        401: {"description": "代理访问密钥无效"},
        403: {"description": "数字人设备已停用"},
        404: {"description": "小智中间件服务不存在或未发布"},
        409: {"description": "小智中间件服务未绑定大语言模型或模型配置不完整"},
        503: {"description": "绑定的大语言模型已停用、已归档或上游暂时不可用"},
        422: {"description": "请求参数或消息格式校验失败"},
    },
)
async def chat_completions(
    request: Request,
    payload: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(
        default=None, description="Bearer 格式的 LLM_PROXY_API_KEY"
    ),
):
    try:
        await require_proxy_key(authorization, settings)
        request_id = request.state.request_id
        if payload.stream:
            # 在返回 StreamingResponse 前完成鉴权和服务校验，避免生成器中的异常变成 500。
            await llm_proxy_service.validate_stream_ready(
                db, payload, settings, request_id
            )
            return StreamingResponse(
                llm_proxy_service.stream(db, payload, settings, request_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return await llm_proxy_service.complete(db, payload, settings, request_id)
    except AppError as exc:
        return _app_error(exc)
