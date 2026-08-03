from pathlib import Path

from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.enums import DecisionStatus
from intune_auditor.domain.models import AuditConfiguration
from intune_auditor.evaluation.metrics import coverage_metrics

ROOT = Path(__file__).resolve().parents[3]


def test_empty_denominators_and_missing_runtime_are_not_reported_as_zero() -> None:
    coverage = coverage_metrics([], [])
    assert coverage.parser_coverage is None
    assert coverage.microsoft_baseline_coverage is None
    assert coverage.assignment_analysis_coverage is None
    assert coverage.conflict_analysis_coverage is None
    assert coverage.runtime_evidence_coverage is None


def test_limited_analysis_has_no_exact_value_semantics_and_blocks_pilot() -> None:
    service = AuditService(ROOT)
    sample = ROOT / "samples" / "policies" / "01-core-device-security.json"
    result = service.audit_uploads(
        [(sample.name, sample.read_bytes())], AuditConfiguration(active_pack_ids=[])
    )
    assert result.coverage.exact_value_semantic_coverage == 0
    assert result.coverage.runtime_evidence_coverage is None
    assert result.decision.status is DecisionStatus.INSUFFICIENT_EVIDENCE


def test_decision_titles_are_localized_and_runtime_coverage_is_explicit() -> None:
    result = AuditService(ROOT).demonstration_audit("de")
    assert result.coverage.runtime_evidence_coverage is not None
    assert result.decision.title["de"] == "Laufzeitfehler untersuchen"
    assert result.decision.title["en"] == "Runtime remediation required"
