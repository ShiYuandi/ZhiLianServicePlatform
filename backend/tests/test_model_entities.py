import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import decrypt_model_credential, encrypt_model_credential
from app.db.base import Base
from app.models import (
    BaiduASRConfig,
    FrontendAIService,
    FrontendAIServiceImageBinding,
    FrontendAIServiceSpeechBinding,
    XiaozhiMiddlewareService,
    ImageGenerationModel,
    LLMModel,
    LLMOpenAIConfig,
    SpeechRecognitionModel,
    VolcengineASRConfig,
    VolcengineImageConfig,
)


def test_ai_model_metadata_uses_separate_typed_tables_without_json_configs():
    expected = {
        "extended_llm_models",
        "extended_llm_openai_configs",
        "extended_llm_dify_configs",
        "extended_speech_recognition_models",
        "extended_asr_baidu_configs",
        "extended_asr_volcengine_configs",
        "extended_image_generation_models",
        "extended_image_volcengine_configs",
    }

    assert expected.issubset(Base.metadata.tables)
    for table_name in expected:
        table = Base.metadata.tables[table_name]
        assert all(column.type.__class__.__name__ != "JSON" for column in table.columns)


def test_frontend_ai_service_metadata_uses_typed_binding_tables():
    expected = {
        "extended_frontend_ai_services",
        "extended_frontend_ai_service_speech_bindings",
        "extended_frontend_ai_service_image_bindings",
    }
    assert expected.issubset(Base.metadata.tables)

    service_table = inspect(FrontendAIService).local_table
    assert any(
        constraint.name == "uq_extended_frontend_ai_service_code"
        for constraint in service_table.constraints
    )
    assert inspect(FrontendAIServiceSpeechBinding).primary_key[0].name == "service_id"
    assert inspect(FrontendAIServiceImageBinding).primary_key[0].name == "service_id"


@pytest.mark.asyncio
async def test_typed_model_configs_and_project_binding_round_trip(db):
    settings = get_settings()
    openai = LLMModel(
        model_name="展厅大模型",
        model_code="hall-llm",
        provider="openai",
        openai_config=LLMOpenAIConfig(
            base_url="https://example.com/v1",
            upstream_model="example-model",
            api_key_encrypted=encrypt_model_credential("llm-secret", settings),
            timeout_seconds=30,
        ),
    )
    baidu = SpeechRecognitionModel(
        model_name="百度语音识别",
        model_code="baidu-asr",
        provider="baidu",
        baidu_config=BaiduASRConfig(
            app_id="app-id",
            api_key_encrypted=encrypt_model_credential("api-key", settings),
            secret_key_encrypted=encrypt_model_credential("secret-key", settings),
            dev_pid=1537,
        ),
    )
    volc_asr = SpeechRecognitionModel(
        model_name="火山语音识别",
        model_code="volc-asr",
        provider="volcengine",
        volcengine_config=VolcengineASRConfig(
            app_id="volc-app",
            access_token_encrypted=encrypt_model_credential("token", settings),
            resource_id="volc.bigasr.sauc.duration",
            language="zh-CN",
        ),
    )
    image = ImageGenerationModel(
        model_name="火山 Seedream",
        model_code="seedream",
        provider="volcengine",
        volcengine_config=VolcengineImageConfig(
            api_key_encrypted=encrypt_model_credential("image-key", settings),
            upstream_model="doubao-seedream-4-0-250828",
        ),
    )
    service = XiaozhiMiddlewareService(
        service_code="hall",
        service_name="展厅",
        title="展厅",
        questions=[],
        voice_wakeup_enabled=False,
        wake_listening_texts=[],
        wake_requirement_count=0,
        published=False,
        llm_model_config=openai,
    )
    db.add_all([service, baidu, volc_asr, image])
    await db.commit()

    loaded = (
        await db.execute(select(LLMModel).where(LLMModel.model_code == "hall-llm"))
    ).scalar_one()
    await db.refresh(loaded, ["openai_config", "xiaozhi_services"])

    assert loaded.xiaozhi_services[0].service_code == "hall"
    assert (
        decrypt_model_credential(loaded.openai_config.api_key_encrypted, settings)
        == "llm-secret"
    )
    assert image.volcengine_config.default_width == 1024
    assert baidu.baidu_config.dev_pid == 1537
    assert volc_asr.volcengine_config.resource_id == "volc.bigasr.sauc.duration"


@pytest.mark.asyncio
async def test_model_code_is_unique_within_each_capability_table(db):
    db.add_all(
        [
            LLMModel(model_name="模型一", model_code="duplicate", provider="openai"),
            LLMModel(model_name="模型二", model_code="duplicate", provider="dify"),
        ]
    )

    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    llm_table = inspect(LLMModel).local_table
    assert any(
        constraint.name == "uq_extended_llm_model_code"
        for constraint in llm_table.constraints
    )
