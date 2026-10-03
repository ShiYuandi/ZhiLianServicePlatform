import importlib.util
from pathlib import Path


def load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0008_create_frontend_ai_services.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0008", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_0008_creates_frontend_ai_service_and_typed_bindings():
    migration = load_migration()
    source = Path(migration.__file__).read_text(encoding="utf-8")

    assert migration.revision == "0008"
    assert migration.down_revision == "0007"
    assert "extended_frontend_ai_services" in source
    assert "extended_frontend_ai_service_speech_bindings" in source
    assert "extended_frontend_ai_service_image_bindings" in source
    assert "extended_speech_recognition_models" in source
    assert "extended_image_generation_models" in source
    assert 'ondelete="RESTRICT"' in source
