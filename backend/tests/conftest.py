import os
from pathlib import Path

import pytest_asyncio


TEST_DB = Path(__file__).resolve().parents[1] / "test_xiaozhi.db"
os.environ.update(
    {
        "APP_ENV": "test",
        "APP_SECRET_KEY": "test-secret-key-that-is-longer-than-32-bytes",
        "MODEL_CREDENTIAL_ENCRYPTION_KEY": "test-model-key-that-is-longer-than-32-bytes",
        "SERVICE_API_KEY_PEPPER": "test-api-pepper-that-is-longer-than-32-bytes",
        "RESULT_DOWNLOAD_SIGNING_KEY": "test-download-key-that-is-longer-than-32-bytes",
        "DATABASE_URL": f"sqlite+aiosqlite:///{TEST_DB.as_posix()}",
        "ADMIN_INITIAL_USERNAME": "admin",
        "ADMIN_INITIAL_PASSWORD": "development-password",
        "XIAOZHI_API_URL": "https://xiaozhi.example.invalid/device/manual-add",
        "XIAOZHI_TOKEN": "fake-token",
        "XIAOZHI_JSESSIONID": "fake-session",
        "CORS_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
    }
)

from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, get_session_factory  # noqa: E402
from app.models import (  # noqa: E402, F401
    AdminUser,
    BaiduASRConfig,
    DeviceMapping,
    ExternalApiProxy,
    FrontendAIService,
    FrontendAIServiceImageBinding,
    FrontendAIServiceSpeechBinding,
    XiaozhiMiddlewareService,
    ImageGenerationModel,
    LLMDifyConfig,
    LLMModel,
    LLMOpenAIConfig,
    XiaozhiServiceAsset,
    QaItem,
    QaTable,
    SpeechRecognitionModel,
    VolcengineASRConfig,
    VolcengineImageConfig,
)


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db():
    async with get_session_factory()() as session:
        yield session
