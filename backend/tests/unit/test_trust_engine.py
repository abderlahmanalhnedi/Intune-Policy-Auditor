import json
from datetime import date
from pathlib import Path

import pytest

from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.enums import AlignmentStatus, AuditMode, FindingSeverity
from intune_auditor.domain.models import AuditConfiguration
from intune_auditor.evaluation.engine import EvaluationEngine
from intune_auditor.parsing.service import PolicyParser
from intune_auditor.security.limits import DEFAULT_LIMITS
from intune_auditor.security.uploads import validate_uploads

ROOT = Path(__file__).resolve().parents[3]


def audit_setting(identifier: str, value: object, *, platform: str = "windows"):
    policy = {
        "id": "trust-test-policy",
        "name": "Trust Test",
        "platform": platform,
        "policyKind": "settings_catalog",
        "scope": "device",
        "settings": [{"settingDefinitionId": identifier, "value": value}],
        "assignments": [{"target": {"type": "all_devices"}}],
    }
    result = AuditService(ROOT).audit_uploads(
        [("trust-test.json", json.dumps(policy).encode())],
        AuditConfiguration(language="en", active_pack_ids=["synthetic.test-baseline"]),
        mode=AuditMode.OFFLINE,
        on_date=date(2026, 8, 3),
    )
    return result.policies[0].settings[0], result.findings


@pytest.mark.parametrize(
    "identifier",
    [
        ".*firewall.*",
        "network security category",
        "Enable secure protection",
        "disable_insecure_feature",
        "allow_everything",
        "block_everything",
    ],
)
def test_regex_category_and_security_words_cannot_create_judgment(identifier: str) -> None:
    evaluation, findings = audit_setting(identifier, True)
    assert evaluation.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
    assert evaluation.not_evaluable_reasons[0] == "unknown_setting_id"
    assert findings[0].severity is FindingSeverity.INFORMATION


def test_exact_setting_with_unknown_value_is_not_evaluable() -> None:
    evaluation, _ = audit_setting("synthetic/legacy_protocol_mode", "mystery")
    assert evaluation.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
    assert "unknown_value_semantics" in evaluation.not_evaluable_reasons


def test_exact_value_without_exact_source_is_not_evaluable() -> None:
    service = AuditService(ROOT)
    pack = service.installed_packs()[0]
    setting = pack.settings[0].model_copy(update={"evidence_sources": []})
    pack_without_evidence = pack.model_copy(update={"settings": [setting, *pack.settings[1:]]})
    policy = {
        "id": "missing-source",
        "name": "Missing source",
        "platform": "windows",
        "policyKind": "settings_catalog",
        "scope": "device",
        "settings": [{"settingDefinitionId": "synthetic/firewall_mode", "value": "block"}],
    }
    parsed = PolicyParser(DEFAULT_LIMITS).parse(
        validate_uploads([("policy.json", json.dumps(policy).encode())], DEFAULT_LIMITS)
    )
    evaluation, _, _ = EvaluationEngine([pack_without_evidence]).evaluate_setting(
        parsed.policies[0].settings[0], [], date(2026, 8, 3)
    )
    assert evaluation.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
    assert "missing_official_source" in evaluation.not_evaluable_reasons


def test_platform_mismatch_cannot_be_aligned() -> None:
    evaluation, _ = audit_setting("synthetic/firewall_mode", "block", platform="macos")
    assert evaluation.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
    assert "unknown_setting_id" in evaluation.not_evaluable_reasons


def test_synthetic_evidence_cannot_create_high_finding() -> None:
    evaluation, findings = audit_setting("synthetic/firewall_mode", "audit")
    assert evaluation.raw_alignment_status is AlignmentStatus.LESS_RESTRICTIVE
    assert findings[0].severity is FindingSeverity.MEDIUM
    assert not findings[0].evidence[0].is_official


def test_more_restrictive_is_not_automatically_better() -> None:
    evaluation, findings = audit_setting("synthetic/password_length", 18)
    assert evaluation.effective_alignment_status is AlignmentStatus.MORE_RESTRICTIVE
    assert "not automatically better" in findings[0].explanation["en"]


def test_same_identifier_in_multiple_selected_pack_versions_is_not_evaluable() -> None:
    service = AuditService(ROOT)
    pack = service.installed_packs()[0]
    second_manifest = pack.manifest.model_copy(
        update={"pack_id": "synthetic.second-version", "baseline_version": "2.0.0"}
    )
    second_pack = pack.model_copy(update={"manifest": second_manifest})
    policy = {
        "id": "ambiguous-pack-version",
        "name": "Ambiguous pack version",
        "platform": "windows",
        "policyKind": "settings_catalog",
        "scope": "device",
        "settings": [{"settingDefinitionId": "synthetic/firewall_mode", "value": "block"}],
    }
    parsed = PolicyParser(DEFAULT_LIMITS).parse(
        validate_uploads([("policy.json", json.dumps(policy).encode())], DEFAULT_LIMITS)
    )
    evaluation, _, _ = EvaluationEngine([pack, second_pack]).evaluate_setting(
        parsed.policies[0].settings[0], [], date(2026, 8, 3)
    )

    assert evaluation.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
    assert "ambiguous_setting_id" in evaluation.not_evaluable_reasons
    assert "unresolved_baseline_version" in evaluation.not_evaluable_reasons


def test_demo_contains_all_required_nuanced_states() -> None:
    result = AuditService(ROOT).demonstration_audit("en")
    states = {
        item.effective_alignment_status for policy in result.policies for item in policy.settings
    }
    assert {
        AlignmentStatus.ALIGNED,
        AlignmentStatus.LESS_RESTRICTIVE,
        AlignmentStatus.MORE_RESTRICTIVE,
        AlignmentStatus.DIFFERENT,
        AlignmentStatus.NOT_EVALUABLE,
        AlignmentStatus.ACCEPTED_DEVIATION,
        AlignmentStatus.EXPIRED_DEVIATION,
    } <= states
