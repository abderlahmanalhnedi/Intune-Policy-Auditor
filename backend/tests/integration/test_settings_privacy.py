from fastapi.testclient import TestClient

from intune_auditor.main import create_app


def test_privacy_defaults_and_explicit_settings_lifecycle() -> None:
    with TestClient(create_app()) as client:
        defaults = client.get("/api/v1/settings")
        updated = client.put(
            "/api/v1/settings",
            json={
                "history_enabled": True,
                "retention_days": 7,
                "save_reports": False,
                "automatic_cleanup": True,
            },
        )
        current = client.get("/api/v1/settings")
        reset = client.post("/api/v1/settings/reset")
        cleared = client.get("/api/v1/settings")
    assert defaults.json()["data"]["raw_uploads_retained"] is False
    assert updated.status_code == 200
    assert current.json()["data"]["history_enabled"] is True
    assert reset.status_code == 200
    assert cleared.json()["data"]["history_enabled"] is False
