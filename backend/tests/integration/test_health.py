from fastapi.testclient import TestClient

from intune_auditor.config import get_settings
from intune_auditor.main import create_app


def test_health_endpoint(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("INTUNE_AUDITOR_DATA_DIR_OVERRIDE", str(tmp_path))
    monkeypatch.setenv("INTUNE_AUDITOR_FRONTEND_DIST_OVERRIDE", str(tmp_path / "dist"))
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    get_settings.cache_clear()
