from __future__ import annotations

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import verify_service_api_key
from app.db.session import get_db
from app.models.frontend_ai_service import FrontendAIService, FrontendAIServiceSpeechBinding, FrontendAIServiceImageBinding


async def get_frontend_ai_service(
    request: Request,
    authorization: str | None = Header(default=None, description="Bearer 服务 API Key"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FrontendAIService:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("SERVICE_UNAUTHORIZED", "缺少服务 API Key", 401)
    key = authorization[7:].strip()
    if not key:
        raise AppError("SERVICE_UNAUTHORIZED", "服务 API Key 无效", 401)
    service = await db.scalar(select(FrontendAIService).options(
        selectinload(FrontendAIService.speech_binding).selectinload(FrontendAIServiceSpeechBinding.model),
        selectinload(FrontendAIService.image_binding).selectinload(FrontendAIServiceImageBinding.model),
    ).where(FrontendAIService.service_code == request.path_params.get("service_code"), FrontendAIService.archived_at.is_(None)))
    if not service or not verify_service_api_key(key, service.api_key_hash, settings):
        raise AppError("SERVICE_UNAUTHORIZED", "服务 API Key 无效", 401)
    origin = request.headers.get("Origin")
    if origin and service.allowed_origins and origin.rstrip("/") not in service.allowed_origins:
        raise AppError("ORIGIN_NOT_ALLOWED", "请求来源不在服务允许列表中", 403)
    return service


async def get_frontend_ai_service_public(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FrontendAIService:
    """按路径编码解析服务但不校验 API Key，供自带平台签名令牌的下载端点使用。"""

    service = await db.scalar(select(FrontendAIService).where(
        FrontendAIService.service_code == request.path_params.get("service_code"),
        FrontendAIService.archived_at.is_(None),
    ))
    if not service:
        raise AppError("FRONTEND_AI_SERVICE_NOT_FOUND", "前端 AI 服务不存在", 404)
    return service
