import importlib.util
from pathlib import Path


def load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0006_create_ai_model_tables.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0006", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_0006_only_creates_models_for_projects_with_llm_values():
    migration = load_migration()

    assert migration.revision == "0006"
    assert migration.down_revision == "0005"
    assert not migration._has_llm_configuration(
        {
            "llm_base_url": None,
            "llm_model": None,
            "llm_api_key_encrypted": None,
            "llm_mode": None,
        }
    )
    assert migration._has_llm_configuration(
        {
            "llm_base_url": "https://example.com/v1",
            "llm_model": None,
            "llm_api_key_encrypted": None,
            "llm_mode": None,
        }
    )
