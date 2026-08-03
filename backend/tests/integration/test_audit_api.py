from pathlib import Path

from fastapi.testclient import TestClient

from intune_auditor.main import create_app

ROOT = Path(__file__).resolve().parents[3]


def test_offline_upload_navigation_and_pdf_report() -> None:
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    with TestClient(create_app()) as client, policy.open("rb") as handle:
        created = client.post(
            "/api/v1/audits",
            files={"files": (policy.name, handle, "application/json")},
            data={
                "knowledge_pack_ids": '["synthetic.test-baseline"]',
                "language": "en",
                "audit_context": '{"physical_device":true,"vdi":false}',
            },
        )
        audit_id = created.json()["data"]["audit_id"]
        dashboard = client.get(f"/api/v1/audits/{audit_id}/dashboard")
        policies = client.get(f"/api/v1/audits/{audit_id}/policies")
        findings = client.get(f"/api/v1/audits/{audit_id}/findings")
        conflicts = client.get(f"/api/v1/audits/{audit_id}/conflicts")
        report = client.get(f"/api/v1/audits/{audit_id}/reports/pdf?language=en")
    assert created.status_code == 201
    assert dashboard.status_code == policies.status_code == findings.status_code == 200
    assert conflicts.status_code == 200
    assert dashboard.json()["data"]["evidence_quality"] in {
        "exact",
        "strong",
        "partial",
        "unknown",
    }
    assert sum(dashboard.json()["data"]["policy_health_counts"].values()) == 1
    assert isinstance(dashboard.json()["data"]["not_evaluable_reasons"], dict)
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/pdf")
    assert report.content.startswith(b"%PDF")


def test_malformed_upload_returns_problem_response_without_server_error() -> None:
    malformed = ROOT / "samples" / "malformed" / "malformed.json"
    with TestClient(create_app()) as client, malformed.open("rb") as handle:
        response = client.post(
            "/api/v1/audits",
            files={"files": (malformed.name, handle, "application/json")},
            data={"knowledge_pack_ids": '["synthetic.test-baseline"]'},
        )
    assert response.status_code == 422
    assert response.json()["title"] == "Audit input rejected"


def test_preview_detects_scope_without_creating_an_audit() -> None:
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    with TestClient(create_app()) as client, policy.open("rb") as handle:
        response = client.post(
            "/api/v1/audits/preview",
            files={"files": (policy.name, handle, "application/json")},
        )
    assert response.status_code == 200
    assert response.json()["data"]["policy_count"] == 1
    assert response.json()["data"]["setting_count"] > 0
