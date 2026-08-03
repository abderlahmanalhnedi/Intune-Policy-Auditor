"""Per-setting value canonicalization and explicitly ordered comparisons."""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation

from intune_auditor.domain.enums import AlignmentStatus, ComparisonMode, ValueType
from intune_auditor.domain.models import ComparisonRule, JsonValue, ValueDefinition


def _serialized_value(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonicalize_value(
    value: JsonValue, definition: ValueDefinition
) -> tuple[JsonValue, str | None]:
    if value is None:
        if definition.value_type is ValueType.NOT_CONFIGURED:
            return None, None
        return None, "unknown_value_semantics"
    mapped = definition.semantic_mapping.get(str(value))
    if mapped is not None:
        value = mapped
    value_type = definition.value_type
    try:
        if value_type is ValueType.BOOLEAN:
            if isinstance(value, bool):
                canonical: JsonValue = value
            elif isinstance(value, str) and value.lower() in {"true", "false"}:
                canonical = value.lower() == "true"
            else:
                return value, "unknown_value_semantics"
        elif value_type is ValueType.INTEGER:
            if isinstance(value, bool):
                return value, "unknown_value_semantics"
            number = Decimal(str(value))
            if not number.is_finite() or number != number.to_integral_value():
                return value, "unknown_value_semantics"
            canonical = int(number)
        elif value_type is ValueType.DECIMAL:
            if isinstance(value, bool):
                return value, "unknown_value_semantics"
            number = Decimal(str(value))
            if not number.is_finite():
                return value, "unknown_value_semantics"
            canonical = float(number)
            if not math.isfinite(canonical):
                return value, "unknown_value_semantics"
        elif value_type in {ValueType.STRING, ValueType.ENUM, ValueType.CHOICE}:
            if not isinstance(value, str):
                return value, "unknown_value_semantics"
            canonical = value
        elif value_type in {ValueType.LIST, ValueType.SET}:
            if not isinstance(value, list):
                return value, "unknown_value_semantics"
            canonical = value
        elif value_type is ValueType.RANGE:
            if not isinstance(value, (dict, list)):
                return value, "unknown_value_semantics"
            canonical = value
        elif value_type is ValueType.OBJECT:
            if not isinstance(value, dict):
                return value, "unknown_value_semantics"
            canonical = value
        elif value_type is ValueType.NOT_CONFIGURED:
            return value, "unknown_value_semantics"
        else:
            return value, "unknown_value_semantics"
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return value, "unknown_value_semantics"
    if definition.allowed_values:
        serialized_allowed = {_serialized_value(item) for item in definition.allowed_values}
        allowed = (
            all(_serialized_value(item) in serialized_allowed for item in canonical)
            if value_type in {ValueType.LIST, ValueType.SET} and isinstance(canonical, list)
            else _serialized_value(canonical) in serialized_allowed
        )
        if not allowed:
            return canonical, "unknown_value_semantics"
    return canonical, None


def _serialized_set(values: list[JsonValue]) -> set[str]:
    return {_serialized_value(value) for value in values}


def compare_values(
    configured: JsonValue,
    baseline: JsonValue,
    rule: ComparisonRule,
) -> AlignmentStatus:
    if configured == baseline:
        return AlignmentStatus.ALIGNED
    mode = rule.mode
    if mode in {ComparisonMode.EXACT, ComparisonMode.NOT_ORDERABLE}:
        return AlignmentStatus.DIFFERENT
    if mode is ComparisonMode.ORDERED:
        try:
            configured_index = rule.ordered_values.index(configured)
            baseline_index = rule.ordered_values.index(baseline)
        except ValueError:
            return AlignmentStatus.NOT_EVALUABLE
        return (
            AlignmentStatus.MORE_RESTRICTIVE
            if configured_index > baseline_index
            else AlignmentStatus.LESS_RESTRICTIVE
        )
    if mode in {ComparisonMode.NUMERIC_MINIMUM, ComparisonMode.NUMERIC_MAXIMUM}:
        try:
            configured_number = Decimal(str(configured))
            baseline_number = Decimal(str(baseline))
        except InvalidOperation:
            return AlignmentStatus.NOT_EVALUABLE
        if mode is ComparisonMode.NUMERIC_MINIMUM:
            return (
                AlignmentStatus.MORE_RESTRICTIVE
                if configured_number > baseline_number
                else AlignmentStatus.LESS_RESTRICTIVE
            )
        return (
            AlignmentStatus.MORE_RESTRICTIVE
            if configured_number < baseline_number
            else AlignmentStatus.LESS_RESTRICTIVE
        )
    if mode is ComparisonMode.NUMERIC_RANGE:
        if rule.minimum is None or rule.maximum is None:
            return AlignmentStatus.NOT_EVALUABLE
        try:
            number = Decimal(str(configured))
        except InvalidOperation:
            return AlignmentStatus.NOT_EVALUABLE
        return (
            AlignmentStatus.ALIGNED
            if rule.minimum <= number <= rule.maximum
            else AlignmentStatus.DIFFERENT
        )
    if mode in {ComparisonMode.SET_EQUALS, ComparisonMode.SET_CONTAINS}:
        if not isinstance(configured, list) or not isinstance(baseline, list):
            return AlignmentStatus.NOT_EVALUABLE
        configured_set = _serialized_set(configured)
        baseline_set = _serialized_set(baseline)
        if configured_set == baseline_set:
            return AlignmentStatus.ALIGNED
        if mode is ComparisonMode.SET_EQUALS:
            return AlignmentStatus.DIFFERENT
        if baseline_set < configured_set:
            return AlignmentStatus.MORE_RESTRICTIVE
        if configured_set < baseline_set:
            return AlignmentStatus.LESS_RESTRICTIVE
        return AlignmentStatus.DIFFERENT
    if mode is ComparisonMode.LIST_EQUALS:
        return AlignmentStatus.DIFFERENT
    return AlignmentStatus.NOT_EVALUABLE
