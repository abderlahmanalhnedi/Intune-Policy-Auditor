from fastapi.testclient import TestClient

from intune_auditor.main import create_app


def test_unconfigured_tenant_mode_does_not_affect_offline_health() -> None:
    with TestClient(create_app()) as client:
        status = client.get("/api/v1/tenant/status")
        health = client.get("/api/v1/health")
        begin = client.post("/api/v1/tenant/device-code")
    assert status.status_code == 200
    assert status.json()["data"]["configured"] is False
    assert health.status_code == 200
    assert begin.status_code == 409
