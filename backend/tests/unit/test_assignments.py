from intune_auditor.assignments.engine import analyze_assignment_risks
from intune_auditor.domain.enums import (
    AssignmentTargetType,
    FilterMode,
    Platform,
    PolicyKind,
    Scope,
)
from intune_auditor.domain.models import (
    AssignmentFilter,
    AssignmentTarget,
    PolicyDocument,
    UploadedSource,
)


def _policy(
    assignments: list[AssignmentTarget],
    *,
    name: str = "Production security policy",
    scope: Scope = Scope.DEVICE,
) -> PolicyDocument:
    return PolicyDocument(
        policy_id="policy-a",
        name=name,
        platform=Platform.WINDOWS,
        kind=PolicyKind.ENDPOINT_SECURITY,
        scope=scope,
        source=UploadedSource(
            source_id="a" * 64,
            filename="policy.json",
            content_type="application/json",
            size_bytes=2,
            sha256="a" * 64,
        ),
        assignments=assignments,
    )


def _risk_types(policy: PolicyDocument, *, high_impact: bool = False) -> set[str]:
    return {item.risk_type for item in analyze_assignment_risks(policy, high_impact=high_impact)}


def test_missing_and_sensitive_unassigned_policy_are_distinguished() -> None:
    assert _risk_types(_policy([])) == {"missing_assignment"}
    assert _risk_types(_policy([]), high_impact=True) == {
        "missing_assignment",
        "sensitive_policy_without_assignment",
    }


def test_broad_pilot_and_exclusions_only_risks_are_detected() -> None:
    all_devices = AssignmentTarget(target_type=AssignmentTargetType.ALL_DEVICES)
    assert "pilot_policy_assigned_broadly" in _risk_types(
        _policy([all_devices], name="Pilot security policy")
    )
    exclusion = AssignmentTarget(
        target_type=AssignmentTargetType.EXCLUSION_GROUP, target_id="group-a"
    )
    assert "exclusions_only" in _risk_types(_policy([exclusion]))


def test_unknown_scope_filter_and_platform_risks_remain_visible() -> None:
    unknown = AssignmentTarget(target_type=AssignmentTargetType.UNKNOWN)
    missing_filter = AssignmentTarget(
        target_type=AssignmentTargetType.GROUP,
        target_id="group-a",
        scope=Scope.USER,
        filter=AssignmentFilter(
            filter_id="filter-a",
            mode=FilterMode.INCLUDE,
            platform=Platform.IOS,
            definition_available=False,
        ),
    )
    risks = _risk_types(_policy([unknown, missing_filter]))
    assert {
        "unknown_assignment_target",
        "missing_filter_definition",
        "platform_filter_mismatch",
        "scope_targeting_risk",
    }.issubset(risks)


def test_contradictory_groups_and_high_impact_without_pilot_are_detected() -> None:
    include = AssignmentTarget(target_type=AssignmentTargetType.GROUP, target_id="group-a")
    exclude = AssignmentTarget(
        target_type=AssignmentTargetType.EXCLUSION_GROUP, target_id="group-a"
    )
    risks = _risk_types(_policy([include, exclude]), high_impact=True)
    assert "contradictory_include_exclude" in risks
    assert "high_impact_without_pilot_stage" in risks


def test_recognizable_pilot_stage_satisfies_high_impact_rollout_gate() -> None:
    pilot = AssignmentTarget(
        target_type=AssignmentTargetType.GROUP,
        target_id="pilot-group",
        display_name="Pilot devices",
    )
    assert "high_impact_without_pilot_stage" not in _risk_types(_policy([pilot]), high_impact=True)
