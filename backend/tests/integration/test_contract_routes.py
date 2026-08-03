from pathlib import Path

from fastapi.testclient import TestClient

from intune_auditor.main import create_app

ROOT = Path(__file__).resolve().parents[3]


def test_diagnostics_deviation_validation_and_tenant_contract_aliases() -> None:
    deviation = ROOT / "organization" / "accepted-deviations.example.json"
    with TestClient(create_app()) as client, deviation.open("rb") as handle:
        diagnostics = client.get("/api/v1/diagnostics")
        validation = client.post(
            "/api/v1/deviations/validate",
            files={"deviations": (deviation.name, handle, "application/json")},
        )
        connect = client.post("/api/v1/tenant/connect")
        signout = client.post("/api/v1/tenant/signout")

    assert diagnostics.status_code == 200
    assert diagnostics.json()["data"]["offline_mode_ready"] is True
    assert validation.status_code == 200
    assert validation.json()["data"]["deviation_count"] == 2
    assert connect.status_code == 409
    assert signout.status_code == 200


def test_offline_api_retains_typed_organization_requirements() -> None:
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    requirements = ROOT / "organization" / "requirements.example.json"
    with (
        TestClient(create_app()) as client,
        policy.open("rb") as policy_handle,
        requirements.open("rb") as requirement_handle,
    ):
        response = client.post(
            "/api/v1/audits",
            files={
                "files": (policy.name, policy_handle, "application/json"),
                "organization_requirements": (
                    requirements.name,
                    requirement_handle,
                    "application/json",
                ),
            },
            data={"knowledge_pack_ids": "[]", "language": "en"},
        )

    assert response.status_code == 201
    configuration = response.json()["data"]["configuration"]
    assert configuration["active_pack_ids"] == []
    assert configuration["organization_requirements"][0]["requirement_id"] == (
        "synthetic-pilot-required"
    )


def test_declared_oversized_request_is_rejected_before_body_processing() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/health",
            headers={"content-length": str(200 * 1024 * 1024)},
        )
    assert response.status_code == 413
    assert response.headers["content-type"].startswith("application/problem+json")
