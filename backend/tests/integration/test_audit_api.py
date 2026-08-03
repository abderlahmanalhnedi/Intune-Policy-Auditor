import codecs
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from intune_auditor.application.audit_service import AuditService
from intune_auditor.main import create_app
from intune_auditor.security.limits import ProcessingLimits

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


@pytest.mark.parametrize(
    ("encoding", "encode"),
    [
        ("utf-8", lambda text: text.encode("utf-8")),
        ("utf-8-bom", lambda text: codecs.BOM_UTF8 + text.encode("utf-8")),
        ("utf-16-le-bom", lambda text: codecs.BOM_UTF16_LE + text.encode("utf-16-le")),
        ("utf-16-be-bom", lambda text: codecs.BOM_UTF16_BE + text.encode("utf-16-be")),
    ],
    ids=["utf-8", "utf-8-bom", "utf-16-le-bom", "utf-16-be-bom"],
)
def test_preview_accepts_supported_json_text_encodings(
    encoding: str,
    encode: Callable[[str], bytes],
) -> None:
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    content = encode(policy.read_text(encoding="utf-8"))
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/audits/preview",
            files={"files": (f"policy-{encoding}.json", content, "application/json")},
        )
    assert response.status_code == 200
    assert response.json()["data"]["policy_count"] == 1


@pytest.mark.parametrize(
    ("filename", "content", "expected_code"),
    [
        ("binary.json", b"\x00\x01MZ\xff\x10", "unsupported_encoding"),
        ("renamed.json", b"<!doctype html><html></html>", "malformed_json"),
        ("malformed.json", b'{"id":', "malformed_json"),
        ("latin-1.json", b'{"id":"\xe9"}', "unsupported_encoding"),
        ("utf16-without-bom.json", '{"id":"policy"}'.encode("utf-16-le"), "unsupported_encoding"),
        (
            "utf-32-le.json",
            codecs.BOM_UTF32_LE + '{"id":"policy"}'.encode("utf-32-le"),
            "unsupported_encoding",
        ),
        (
            "utf-32-be.json",
            codecs.BOM_UTF32_BE + '{"id":"policy"}'.encode("utf-32-be"),
            "unsupported_encoding",
        ),
        ("program.exe", b"MZ", "unsupported_file_type"),
    ],
)
def test_preview_rejects_binary_html_malformed_and_unsupported_uploads(
    filename: str,
    content: bytes,
    expected_code: str,
) -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/audits/preview",
            files={"files": (filename, content, "application/octet-stream")},
        )
    assert response.status_code == 422
    assert expected_code in response.json()["detail"]


def test_preview_rejects_input_over_the_existing_size_limit() -> None:
    app = create_app()
    app.state.audit_service = AuditService(
        ROOT,
        limits=ProcessingLimits(single_file_bytes=1024),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/audits/preview",
            files={"files": ("oversized.json", b" " * 1025, "application/json")},
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "single_file_size_exceeded"
