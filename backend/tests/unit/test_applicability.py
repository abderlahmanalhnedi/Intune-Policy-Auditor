from intune_auditor.applicability.engine import evaluate_applicability
from intune_auditor.domain.enums import (
    ApplicabilityState,
    EvidenceConfidence,
    Platform,
    Scope,
)
from intune_auditor.domain.models import ApplicabilityRule, AuditContext, SettingObservation


def observation() -> SettingObservation:
    return SettingObservation(
        observation_id="one",
        original_setting_id="synthetic.example",
        normalized_setting_id="synthetic.example",
        canonical_setting_id="synthetic.example",
        original_value=True,
        canonical_value=True,
        display_value="true",
        technical_json_path="$.settings[0]",
        source_policy_id="policy",
        source_policy_name="Policy",
        source_file="policy.json",
        platform=Platform.WINDOWS,
        scope=Scope.DEVICE,
        extraction_confidence=EvidenceConfidence.EXACT,
        parser_name="test",
        parser_version="1",
    )


def test_missing_sourced_target_fact_remains_unknown() -> None:
    rule = ApplicabilityRule(
        platforms=[Platform.WINDOWS],
        scopes=[Scope.DEVICE],
        minimum_os="11.0",
    )
    result = evaluate_applicability(rule, observation(), AuditContext())
    assert result.state is ApplicabilityState.UNKNOWN
    assert result.reasons == ["target_os_version_unknown"]


def test_explicit_os_mismatch_is_not_applicable() -> None:
    rule = ApplicabilityRule(
        platforms=[Platform.WINDOWS],
        scopes=[Scope.DEVICE],
        minimum_os="11.0",
    )
    result = evaluate_applicability(rule, observation(), AuditContext(os_version="10.0"))
    assert result.state is ApplicabilityState.NOT_APPLICABLE
    assert result.reasons == ["below_minimum_os"]


def test_all_sourced_constraints_can_be_proven_applicable() -> None:
    rule = ApplicabilityRule(
        platforms=[Platform.WINDOWS],
        scopes=[Scope.DEVICE],
        minimum_os="10.0",
        editions=["Enterprise"],
        architectures=["x64"],
        licensing_requirements=["Intune Plan 1"],
    )
    context = AuditContext(
        os_version="11.0",
        edition="enterprise",
        architecture="X64",
        granted_licenses=["Intune Plan 1"],
    )
    assert (
        evaluate_applicability(rule, observation(), context).state is ApplicabilityState.APPLICABLE
    )
