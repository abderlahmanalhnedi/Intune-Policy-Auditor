"""Distinguish duplicates from confirmed, probable, and possible conflicts."""

from __future__ import annotations

import json
from itertools import combinations
from uuid import NAMESPACE_URL, uuid5

from intune_auditor.domain.enums import AssignmentTargetType, ConflictConfidence, Scope
from intune_auditor.domain.models import (
    AssignmentTarget,
    ConflictResult,
    JsonValue,
    PolicyEvaluation,
)


def _text(de: str, en: str) -> dict[str, str]:
    return {"de": de, "en": en}


def _equivalent(left: JsonValue, right: JsonValue) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        try:
            return sorted(json.dumps(item, sort_keys=True) for item in left) == sorted(
                json.dumps(item, sort_keys=True) for item in right
            )
        except TypeError:
            return left == right
    return left == right


def _scope_compatible(left: Scope, right: Scope) -> bool:
    if Scope.UNKNOWN in {left, right}:
        return False
    return left == right or Scope.BOTH in {left, right}


def _effective_targets(assignments: list[AssignmentTarget]) -> list[AssignmentTarget]:
    return [
        item for item in assignments if item.target_type is not AssignmentTargetType.EXCLUSION_GROUP
    ]


def _group_ids(assignments: list[AssignmentTarget], target_type: AssignmentTargetType) -> set[str]:
    return {
        item.target_id
        for item in assignments
        if item.target_type is target_type and item.target_id is not None
    }


def _exclusions_eliminate_overlap(
    left: list[AssignmentTarget], right: list[AssignmentTarget]
) -> bool:
    left_effective = _effective_targets(left)
    right_effective = _effective_targets(right)
    left_groups = _group_ids(left_effective, AssignmentTargetType.GROUP)
    right_groups = _group_ids(right_effective, AssignmentTargetType.GROUP)
    left_only_groups = bool(left_groups) and len(left_groups) == len(left_effective)
    right_only_groups = bool(right_groups) and len(right_groups) == len(right_effective)
    left_exclusions = _group_ids(left, AssignmentTargetType.EXCLUSION_GROUP)
    right_exclusions = _group_ids(right, AssignmentTargetType.EXCLUSION_GROUP)
    return (left_only_groups and left_groups.issubset(right_exclusions)) or (
        right_only_groups and right_groups.issubset(left_exclusions)
    )


def analyze_overlap(
    left: list[AssignmentTarget],
    right: list[AssignmentTarget],
) -> tuple[ConflictConfidence, str, dict[str, str]]:
    left_targets = _effective_targets(left)
    right_targets = _effective_targets(right)
    if not left_targets or not right_targets:
        return (
            ConflictConfidence.NONE,
            "no_effective_assignment",
            _text(
                "Mindestens eine Richtlinie hat keine wirksame Einschlusszuweisung.",
                "At least one policy has no effective inclusion assignment.",
            ),
        )
    if _exclusions_eliminate_overlap(left, right):
        return (
            ConflictConfidence.NONE,
            "exclusions_eliminate_overlap",
            _text(
                "Explizite Gruppenausschlüsse beseitigen die erkennbare Überlappung.",
                "Explicit group exclusions eliminate the recognizable overlap.",
            ),
        )
    for left_target in left_targets:
        for right_target in right_targets:
            if left_target.filter and right_target.filter:
                same_filter = (
                    left_target.filter.filter_id
                    and left_target.filter.filter_id == right_target.filter.filter_id
                )
                opposite_modes = left_target.filter.mode is not right_target.filter.mode
                if (
                    same_filter
                    and opposite_modes
                    and left_target.filter.definition_available
                    and right_target.filter.definition_available
                ):
                    return (
                        ConflictConfidence.NONE,
                        "filters_eliminate_overlap",
                        _text(
                            "Gegenläufige, identische Filter teilen die Zielmenge nachweisbar.",
                            "Opposite modes on the same defined filter provably split the target set.",
                        ),
                    )
            if (left_target.filter and not left_target.filter.definition_available) or (
                right_target.filter and not right_target.filter.definition_available
            ):
                return (
                    ConflictConfidence.POSSIBLE,
                    "missing_filter_data",
                    _text(
                        "Mindestens eine Filterdefinition fehlt; Überlappung ist offline nicht beweisbar.",
                        "At least one filter definition is missing; overlap cannot be proven offline.",
                    ),
                )
            if left_target.target_type == right_target.target_type and left_target.target_type in {
                AssignmentTargetType.ALL_DEVICES,
                AssignmentTargetType.ALL_USERS,
            }:
                return (
                    ConflictConfidence.CONFIRMED,
                    "same_broad_target",
                    _text(
                        "Beide Richtlinien verwenden dasselbe breite Ziel ohne ausschließenden Filter.",
                        "Both policies use the same broad target without an eliminating filter.",
                    ),
                )
            if (
                left_target.target_type is AssignmentTargetType.GROUP
                and right_target.target_type is AssignmentTargetType.GROUP
            ):
                if left_target.target_id and left_target.target_id == right_target.target_id:
                    return (
                        ConflictConfidence.CONFIRMED,
                        "same_group",
                        _text(
                            "Beide Richtlinien schließen dieselbe Gruppen-ID ein.",
                            "Both policies include the same group ID.",
                        ),
                    )
                return (
                    ConflictConfidence.POSSIBLE,
                    "different_groups_unknown_membership",
                    _text(
                        "Verschiedene Gruppen-IDs werden offline nicht als überlappend angenommen.",
                        "Different group IDs are not assumed to overlap offline.",
                    ),
                )
            broad_types = {AssignmentTargetType.ALL_DEVICES, AssignmentTargetType.ALL_USERS}
            if left_target.target_type in broad_types or right_target.target_type in broad_types:
                return (
                    ConflictConfidence.PROBABLE,
                    "broad_target_probable_overlap",
                    _text(
                        "Ein breites Ziel macht eine Überlappung wahrscheinlich; Mitgliedschaftsdaten fehlen.",
                        "A broad target makes overlap probable; membership data is unavailable.",
                    ),
                )
    return (
        ConflictConfidence.POSSIBLE,
        "unknown_target_overlap",
        _text(
            "Die Offline-Daten beweisen oder widerlegen die Überlappung nicht.",
            "Offline data neither proves nor disproves overlap.",
        ),
    )


class ConflictEngine:
    def analyze(self, policies: list[PolicyEvaluation]) -> list[ConflictResult]:
        candidates: dict[str, list[tuple[PolicyEvaluation, JsonValue]]] = {}
        for policy in policies:
            for evaluation in policy.settings:
                candidates.setdefault(evaluation.observation.canonical_setting_id, []).append(
                    (policy, evaluation.observation.canonical_value)
                )
        results: list[ConflictResult] = []
        for canonical_id, observations in candidates.items():
            for (left_policy, left_value), (right_policy, right_value) in combinations(
                observations, 2
            ):
                left_doc = left_policy.policy
                right_doc = right_policy.policy
                if left_doc.platform != right_doc.platform or not _scope_compatible(
                    left_doc.scope, right_doc.scope
                ):
                    continue
                if _equivalent(left_value, right_value):
                    confidence = ConflictConfidence.NONE
                    classification = "duplicate_same_value"
                    overlap = "value_equivalent"
                    reasoning = _text(
                        "Beide Richtlinien konfigurieren denselben wirksamen Wert; dies ist ein Duplikat, kein Konflikt.",
                        "Both policies configure the same effective value; this is a duplicate, not a conflict.",
                    )
                else:
                    confidence, overlap, reasoning = analyze_overlap(
                        left_doc.assignments, right_doc.assignments
                    )
                    classification = (
                        "confirmed_conflict"
                        if confidence is ConflictConfidence.CONFIRMED
                        else "probable_conflict"
                        if confidence is ConflictConfidence.PROBABLE
                        else "possible_conflict"
                        if confidence is ConflictConfidence.POSSIBLE
                        else "no_effective_conflict"
                    )
                conflict_key = f"{canonical_id}:{left_doc.policy_id}:{right_doc.policy_id}"
                results.append(
                    ConflictResult(
                        conflict_id=str(uuid5(NAMESPACE_URL, conflict_key)),
                        confidence=confidence,
                        classification=classification,
                        canonical_setting_id=canonical_id,
                        policy_a_id=left_doc.policy_id,
                        policy_a_name=left_doc.name,
                        policy_a_value=left_value,
                        policy_b_id=right_doc.policy_id,
                        policy_b_name=right_doc.name,
                        policy_b_value=right_value,
                        assignments_a=left_doc.assignments,
                        assignments_b=right_doc.assignments,
                        overlap_result=overlap,
                        reasoning=reasoning,
                        recommended_action=_text(
                            "Zuweisungen, Ausschlüsse und Filter prüfen; keine Richtlinie automatisch ändern.",
                            "Review assignments, exclusions, and filters; do not change policies automatically.",
                        ),
                    )
                )
        return results
