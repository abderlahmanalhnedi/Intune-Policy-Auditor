from pathlib import Path

from intune_auditor.application.audit_service import AuditService
from intune_auditor.conflicts.engine import analyze_overlap
from intune_auditor.domain.enums import (
    AssignmentTargetType,
    ConflictConfidence,
    FilterMode,
    Platform,
)
from intune_auditor.domain.models import AssignmentFilter, AssignmentTarget

ROOT = Path(__file__).resolve().parents[3]


def test_demo_distinguishes_confirmed_probable_and_possible_overlap() -> None:
    result = AuditService(ROOT).demonstration_audit("en")
    confidences = {item.confidence for item in result.conflicts}
    assert ConflictConfidence.CONFIRMED in confidences
    assert ConflictConfidence.PROBABLE in confidences
    assert ConflictConfidence.POSSIBLE in confidences


def test_different_groups_are_not_assumed_to_overlap() -> None:
    result = AuditService(ROOT).demonstration_audit("en")
    telemetry = next(
        item for item in result.conflicts if "telemetry_mode" in item.canonical_setting_id
    )
    assert telemetry.confidence is ConflictConfidence.POSSIBLE
    assert telemetry.overlap_result == "different_groups_unknown_membership"


def test_explicit_group_exclusion_can_prove_no_overlap() -> None:
    group = AssignmentTarget(target_type=AssignmentTargetType.GROUP, target_id="group-a")
    broad_with_exclusion = [
        AssignmentTarget(target_type=AssignmentTargetType.ALL_DEVICES),
        AssignmentTarget(target_type=AssignmentTargetType.EXCLUSION_GROUP, target_id="group-a"),
    ]
    confidence, result, _ = analyze_overlap([group], broad_with_exclusion)
    assert confidence is ConflictConfidence.NONE
    assert result == "exclusions_eliminate_overlap"


def test_opposite_defined_filters_eliminate_overlap_but_missing_data_does_not() -> None:
    include = AssignmentFilter(
        filter_id="filter-a",
        mode=FilterMode.INCLUDE,
        platform=Platform.WINDOWS,
        definition_available=True,
    )
    exclude = include.model_copy(update={"mode": FilterMode.EXCLUDE})
    left = AssignmentTarget(target_type=AssignmentTargetType.ALL_DEVICES, filter=include)
    right = AssignmentTarget(target_type=AssignmentTargetType.ALL_DEVICES, filter=exclude)
    confidence, result, _ = analyze_overlap([left], [right])
    assert confidence is ConflictConfidence.NONE
    assert result == "filters_eliminate_overlap"

    unknown_filter = include.model_copy(update={"definition_available": False})
    confidence, result, _ = analyze_overlap(
        [left.model_copy(update={"filter": unknown_filter})], [right]
    )
    assert confidence is ConflictConfidence.POSSIBLE
    assert result == "missing_filter_data"
