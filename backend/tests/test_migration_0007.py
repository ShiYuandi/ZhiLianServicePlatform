import importlib.util
from pathlib import Path

from app.models.device_mapping import DeviceMapping
from app.models.xiaozhi_service import XiaozhiMiddlewareService
from app.models.xiaozhi_service_asset import XiaozhiServiceAsset


def load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0007_rename_projects_to_xiaozhi_services.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0007", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_0007_uses_xiaozhi_service_domain_names_everywhere():
    migration = load_migration()

    assert migration.revision == "0007"
    assert migration.down_revision == "0006"
    assert XiaozhiMiddlewareService.__tablename__ == "extended_xiaozhi_services"
    assert XiaozhiServiceAsset.__tablename__ == "extended_xiaozhi_service_assets"
    assert "service_code" in XiaozhiMiddlewareService.__table__.columns
    assert "service_name" in XiaozhiMiddlewareService.__table__.columns
    assert "service_id" in XiaozhiServiceAsset.__table__.columns
    assert "service_id" in DeviceMapping.__table__.columns
