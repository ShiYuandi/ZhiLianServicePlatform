from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import health, public, llm_proxy, ai_services, external_api_proxies
from app.api.docs import OPENAPI_TAGS
from app.api.admin import (
    auth,
    dashboard,
    frontend_ai_services,
    external_api_proxies as admin_external_api_proxies,
    image_models,
    llm_models,
    qa,
    speech_models,
    xiaozhi_services,
)
from app.api import xiaozhi_services as public_xiaozhi_services
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.core.middleware import RequestContextMiddleware
from app.db.session import dispose_engine, get_session_factory
from app.services.auth_service import initialize_admin


def configure_application_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("app").setLevel(numeric_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with get_session_factory()() as db:
        await initialize_admin(db, settings)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_application_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        description=(
            "智联服务台提供小智中间件、问答表、独立 AI 模型以及"
            "面向数字人前端的 AI 服务管理。"
        ),
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=settings.cors_origin_list != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(health.router)
    app.include_router(public.router)
    app.include_router(llm_proxy.router)
    app.include_router(auth.router)
    app.include_router(qa.router)
    app.include_router(xiaozhi_services.router)
    app.include_router(llm_models.router)
    app.include_router(speech_models.router)
    app.include_router(image_models.router)
    app.include_router(frontend_ai_services.router)
    app.include_router(ai_services.router)
    app.include_router(public_xiaozhi_services.router)
    app.include_router(external_api_proxies.router)
    app.include_router(admin_external_api_proxies.router)
    app.include_router(dashboard.router)

    static_dir = Path(__file__).resolve().parent / "static"
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/{path:path}", include_in_schema=False)
    async def admin_spa(path: str = ""):
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "智联服务台运行中", "admin": "/admin"}

    return app


app = create_app()
