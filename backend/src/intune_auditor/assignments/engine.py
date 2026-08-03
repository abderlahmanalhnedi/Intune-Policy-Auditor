"""Explain rollout risks without treating broad targeting as inherently wrong."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from intune_auditor.domain.enums import AssignmentTargetType, FindingSeverity, Platform, Scope
from intune_auditor.domain.models import AssignmentRisk, PolicyDocument


def _text(de: str, en: str) -> dict[str, str]:
    return {"de": de, "en": en}


def _risk(
    policy: PolicyDocument, risk_type: str, severity: FindingSeverity, de: str, en: str
) -> AssignmentRisk:
    return AssignmentRisk(
        risk_id=str(uuid5(NAMESPACE_URL, f"assignment-risk:{policy.policy_id}:{risk_type}")),
        policy_id=policy.policy_id,
        risk_type=risk_type,
        severity=severity,
        explanation=_text(de, en),
        recommended_action=_text(
            "Zielgruppe, Ausschlüsse, Filter und Pilotstatus vor dem Rollout verifizieren.",
            "Verify target, exclusions, filters, and pilot stage before rollout.",
        ),
    )


def analyze_assignment_risks(
    policy: PolicyDocument, *, high_impact: bool = False
) -> list[AssignmentRisk]:
    risks: list[AssignmentRisk] = []
    if not policy.assignments:
        risks.append(
            _risk(
                policy,
                "missing_assignment",
                FindingSeverity.LOW,
                "Die Richtlinie hat keine erkennbare Zuweisung.",
                "The policy has no recognizable assignment.",
            )
        )
        if high_impact:
            risks.append(
                _risk(
                    policy,
                    "sensitive_policy_without_assignment",
                    FindingSeverity.MEDIUM,
                    "Eine belegte Richtlinie mit hoher Auswirkung hat keine erkennbare Zuweisung.",
                    "A substantiated high-impact policy has no recognizable assignment.",
                )
            )
        return risks
    types = {assignment.target_type for assignment in policy.assignments}
    if AssignmentTargetType.ALL_DEVICES in types:
        risks.append(
            _risk(
                policy,
                "broad_assignment_all_devices",
                FindingSeverity.LOW,
                "Die Richtlinie zielt auf alle Geräte. Das ist nicht automatisch falsch, erhöht aber die Rollout-Auswirkung.",
                "The policy targets all devices. This is not automatically wrong, but increases rollout impact.",
            )
        )
    if AssignmentTargetType.ALL_USERS in types:
        risks.append(
            _risk(
                policy,
                "broad_assignment_all_users",
                FindingSeverity.LOW,
                "Die Richtlinie zielt auf alle Benutzer. Plattform- und Gerätekontext sollten geprüft werden.",
                "The policy targets all users. Verify platform and device context.",
            )
        )
    if "pilot" in policy.name.lower() and types.intersection(
        {AssignmentTargetType.ALL_DEVICES, AssignmentTargetType.ALL_USERS}
    ):
        risks.append(
            _risk(
                policy,
                "pilot_policy_assigned_broadly",
                FindingSeverity.MEDIUM,
                "Der Name deutet auf einen Pilot hin, die Zuweisung ist jedoch breit.",
                "The name suggests a pilot, but assignment is broad.",
            )
        )
    if types == {AssignmentTargetType.EXCLUSION_GROUP}:
        risks.append(
            _risk(
                policy,
                "exclusions_only",
                FindingSeverity.MEDIUM,
                "Es wurden nur Ausschlüsse erkannt; eine wirksame Einschlusszuweisung fehlt möglicherweise.",
                "Only exclusions were detected; an effective inclusion may be missing.",
            )
        )
    if AssignmentTargetType.UNKNOWN in types:
        risks.append(
            _risk(
                policy,
                "unknown_assignment_target",
                FindingSeverity.INFORMATION,
                "Mindestens ein Zuweisungsziel ist unbekannt.",
                "At least one assignment target is unknown.",
            )
        )
    for assignment in policy.assignments:
        if assignment.filter and not assignment.filter.definition_available:
            risks.append(
                _risk(
                    policy,
                    "missing_filter_definition",
                    FindingSeverity.INFORMATION,
                    "Eine Filter-ID ist vorhanden, die Filterdefinition fehlt jedoch.",
                    "A filter ID is present, but its definition is missing.",
                )
            )
        if (
            assignment.filter
            and assignment.filter.platform is not Platform.UNKNOWN
            and assignment.filter.platform is not policy.platform
        ):
            risks.append(
                _risk(
                    policy,
                    "platform_filter_mismatch",
                    FindingSeverity.MEDIUM,
                    "Die dokumentierte Filterplattform stimmt nicht mit der Richtlinienplattform überein.",
                    "The documented filter platform does not match the policy platform.",
                )
            )
        if (
            assignment.scope not in {Scope.UNKNOWN, Scope.BOTH, policy.scope}
            and policy.scope is not Scope.BOTH
        ):
            risks.append(
                _risk(
                    policy,
                    "scope_targeting_risk",
                    FindingSeverity.LOW,
                    "Richtlinien- und Zuweisungsbereich wirken inkompatibel.",
                    "Policy and assignment scope appear incompatible.",
                )
            )
    included = {
        item.target_id
        for item in policy.assignments
        if item.target_type is AssignmentTargetType.GROUP and item.target_id
    }
    excluded = {
        item.target_id
        for item in policy.assignments
        if item.target_type is AssignmentTargetType.EXCLUSION_GROUP and item.target_id
    }
    if included.intersection(excluded):
        risks.append(
            _risk(
                policy,
                "contradictory_include_exclude",
                FindingSeverity.MEDIUM,
                "Dieselbe Gruppe ist ein- und ausgeschlossen.",
                "The same group is both included and excluded.",
            )
        )
    pilot_recognizable = "pilot" in policy.name.casefold() or any(
        assignment.display_name and "pilot" in assignment.display_name.casefold()
        for assignment in policy.assignments
    )
    if high_impact and not pilot_recognizable:
        risks.append(
            _risk(
                policy,
                "high_impact_without_pilot_stage",
                FindingSeverity.MEDIUM,
                "Für diese belegte Richtlinie mit hoher Auswirkung ist keine erkennbare Pilotstufe vorhanden.",
                "No recognizable pilot stage is present for this substantiated high-impact policy.",
            )
        )
    return risks
