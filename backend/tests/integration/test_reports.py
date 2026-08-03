import json
from pathlib import Path

from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.models import AuditConfiguration
from intune_auditor.reporting.service import ReportService

ROOT = Path(__file__).resolve().parents[3]


def test_all_report_formats_render_with_expected_content_types() -> None:
    service = AuditService(ROOT)
    audit = service.demonstration_audit("en")
    reports = ReportService(service.limits)
    expectations = {
        "html": ("text/html", b"Intune Policy Auditor"),
        "technical-html": ("text/html", b"Report metadata"),
        "markdown": ("text/markdown", b"# Intune Policy Auditor"),
        "json": ("application/json", b'"metadata"'),
        "findings-csv": ("text/csv", b"finding_id"),
        "conflicts-csv": ("text/csv", b"conflict_id"),
        "not-evaluable-csv": ("text/csv", b"reasons"),
        "provenance-json": ("application/json", b"knowledge_packs"),
        "pdf": ("application/pdf", b"%PDF"),
    }
    for report_format, (media_type, marker) in expectations.items():
        rendered = reports.render(audit, report_format, "en")
        assert rendered.media_type.startswith(media_type)
        assert marker in rendered.content
        assert rendered.filename


def test_unsupported_report_format_is_rejected() -> None:
    service = AuditService(ROOT)
    try:
        ReportService(service.limits).render(service.demonstration_audit(), "docx")
    except ValueError as exc:
        assert str(exc) == "unsupported_report_format"
    else:
        raise AssertionError("unsupported format was accepted")


def test_untrusted_policy_names_are_escaped_in_html_and_markdown() -> None:
    service = AuditService(ROOT)
    policy = {
        "id": "report-injection",
        "name": '<img src=x onerror="alert(1)">',
        "platform": "windows",
        "policyKind": "settings_catalog",
        "scope": "device",
        "settings": [{"settingDefinitionId": "synthetic/firewall_mode", "value": "audit"}],
    }
    audit = service.audit_uploads(
        [("policy.json", json.dumps(policy).encode())],
        AuditConfiguration(active_pack_ids=["synthetic.test-baseline"]),
    )
    reports = ReportService(service.limits)

    html = reports.render(audit, "html", "en").content
    markdown = reports.render(audit, "markdown", "en").content
    assert b"<img src=x" not in html
    assert b"&lt;img src=x" in html
    assert b"<img src=x" not in markdown
    assert b"&lt;img src=x" in markdown
