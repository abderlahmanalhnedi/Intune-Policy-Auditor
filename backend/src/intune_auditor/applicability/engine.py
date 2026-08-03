"""Deterministic applicability gates; absent target facts always remain unknown."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from intune_auditor.domain.enums import ApplicabilityState, Platform, Scope
from intune_auditor.domain.models import ApplicabilityRule, AuditContext, SettingObservation


class ApplicabilityResult(BaseModel):
    state: ApplicabilityState
    reasons: list[str] = Field(default_factory=list)


def _version_tuple(value: str) -> tuple[int, ...] | None:
    if not re.fullmatch(r"\d+(?:\.\d+)*", value.strip()):
        return None
    return tuple(int(part) for part in value.split("."))


def _version_compare(left: str, right: str) -> int | None:
    left_value = _version_tuple(left)
    right_value = _version_tuple(right)
    if left_value is None or right_value is None:
        return None
    width = max(len(left_value), len(right_value))
    normalized_left = left_value + (0,) * (width - len(left_value))
    normalized_right = right_value + (0,) * (width - len(right_value))
    return (normalized_left > normalized_right) - (normalized_left < normalized_right)


def evaluate_applicability(
    rule: ApplicabilityRule,
    observation: SettingObservation,
    context: AuditContext,
) -> ApplicabilityResult:
    """Apply only explicit pack constraints and never treat missing facts as applicable."""

    if observation.platform is Platform.UNKNOWN or observation.scope is Scope.UNKNOWN:
        return ApplicabilityResult(
            state=ApplicabilityState.UNKNOWN,
            reasons=["platform_or_scope_unknown"],
        )
    if observation.platform not in rule.platforms:
        return ApplicabilityResult(
            state=ApplicabilityState.NOT_APPLICABLE,
            reasons=["platform_not_applicable"],
        )
    if observation.scope not in rule.scopes and Scope.BOTH not in rule.scopes:
        return ApplicabilityResult(
            state=ApplicabilityState.NOT_APPLICABLE,
            reasons=["scope_not_applicable"],
        )
    if rule.unsupported:
        return ApplicabilityResult(
            state=ApplicabilityState.NOT_APPLICABLE,
            reasons=["setting_unsupported"],
        )

    unknown: list[str] = []
    not_applicable: list[str] = []
    if rule.minimum_os or rule.maximum_os:
        if context.os_version is None:
            unknown.append("target_os_version_unknown")
        else:
            if rule.minimum_os:
                comparison = _version_compare(context.os_version, rule.minimum_os)
                if comparison is None:
                    unknown.append("target_os_version_unparseable")
                elif comparison < 0:
                    not_applicable.append("below_minimum_os")
            if rule.maximum_os:
                comparison = _version_compare(context.os_version, rule.maximum_os)
                if comparison is None:
                    unknown.append("target_os_version_unparseable")
                elif comparison > 0:
                    not_applicable.append("above_maximum_os")

    checks: list[tuple[list[str], str | None, str, str]] = [
        (rule.editions, context.edition, "target_edition_unknown", "edition_not_applicable"),
        (
            rule.architectures,
            context.architecture,
            "target_architecture_unknown",
            "architecture_not_applicable",
        ),
        (
            rule.enrollment_types,
            context.enrollment_type,
            "enrollment_type_unknown",
            "enrollment_type_not_applicable",
        ),
    ]
    for allowed, actual, unknown_reason, mismatch_reason in checks:
        if not allowed:
            continue
        if actual is None:
            unknown.append(unknown_reason)
        elif actual.casefold() not in {item.casefold() for item in allowed}:
            not_applicable.append(mismatch_reason)

    boolean_checks = [
        (
            rule.supervised_required,
            context.supervised,
            "supervised_state_unknown",
            "supervision_requirement_not_met",
        ),
        (
            rule.physical_device_required,
            context.physical_device,
            "physical_device_state_unknown",
            "physical_device_requirement_not_met",
        ),
    ]
    for required, actual_boolean, unknown_reason, mismatch_reason in boolean_checks:
        if required is None:
            continue
        if actual_boolean is None:
            unknown.append(unknown_reason)
        elif required != actual_boolean:
            not_applicable.append(mismatch_reason)

    if rule.vdi_supported is False:
        if context.vdi is None:
            unknown.append("vdi_state_unknown")
        elif context.vdi:
            not_applicable.append("vdi_not_supported")
    if rule.shared_device_supported is False:
        if context.shared_device is None:
            unknown.append("shared_device_state_unknown")
        elif context.shared_device:
            not_applicable.append("shared_device_not_supported")
    if rule.licensing_requirements:
        if not context.granted_licenses:
            unknown.append("licensing_state_unknown")
        elif not {item.casefold() for item in rule.licensing_requirements}.issubset(
            {item.casefold() for item in context.granted_licenses}
        ):
            not_applicable.append("licensing_requirement_not_met")

    if not_applicable:
        return ApplicabilityResult(
            state=ApplicabilityState.NOT_APPLICABLE,
            reasons=sorted(set(not_applicable)),
        )
    if unknown:
        return ApplicabilityResult(
            state=ApplicabilityState.UNKNOWN,
            reasons=sorted(set(unknown)),
        )
    reasons = ["deprecated"] if rule.deprecated else ["all_sourced_constraints_satisfied"]
    return ApplicabilityResult(state=ApplicabilityState.APPLICABLE, reasons=reasons)
