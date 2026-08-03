from decimal import Decimal

import pytest

from intune_auditor.domain.enums import AlignmentStatus, ComparisonMode, ValueType
from intune_auditor.domain.models import ComparisonRule, ValueDefinition
from intune_auditor.evaluation.value_comparators import canonicalize_value, compare_values


@pytest.mark.parametrize(
    ("definition", "raw", "expected"),
    [
        (ValueDefinition(value_type=ValueType.BOOLEAN), True, True),
        (ValueDefinition(value_type=ValueType.INTEGER), "12", 12),
        (ValueDefinition(value_type=ValueType.DECIMAL), "1.25", 1.25),
        (ValueDefinition(value_type=ValueType.STRING), "text", "text"),
        (ValueDefinition(value_type=ValueType.ENUM, allowed_values=["a", "b"]), "a", "a"),
        (ValueDefinition(value_type=ValueType.CHOICE, allowed_values=["x"]), "x", "x"),
        (ValueDefinition(value_type=ValueType.LIST), ["a", "b"], ["a", "b"]),
        (
            ValueDefinition(value_type=ValueType.SET, allowed_values=["a", "b"]),
            ["a", "b"],
            ["a", "b"],
        ),
        (
            ValueDefinition(value_type=ValueType.RANGE),
            {"minimum": 1, "maximum": 2},
            {"minimum": 1, "maximum": 2},
        ),
        (ValueDefinition(value_type=ValueType.OBJECT), {"key": "value"}, {"key": "value"}),
        (ValueDefinition(value_type=ValueType.NOT_CONFIGURED), None, None),
    ],
)
def test_supported_value_types(definition: ValueDefinition, raw: object, expected: object) -> None:
    value, error = canonicalize_value(raw, definition)  # type: ignore[arg-type]
    assert error is None
    assert value == expected


def test_unknown_value_type_is_not_evaluable() -> None:
    value, error = canonicalize_value("enabled", ValueDefinition(value_type=ValueType.UNKNOWN))
    assert value == "enabled"
    assert error == "unknown_value_semantics"


@pytest.mark.parametrize("raw", [1.25, "1.25", True, "NaN", "Infinity"])
def test_integer_values_are_never_truncated_or_non_finite(raw: object) -> None:
    _, error = canonicalize_value(raw, ValueDefinition(value_type=ValueType.INTEGER))  # type: ignore[arg-type]
    assert error == "unknown_value_semantics"


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "1e10000", True])
def test_decimal_values_must_be_finite_numbers(raw: object) -> None:
    _, error = canonicalize_value(raw, ValueDefinition(value_type=ValueType.DECIMAL))  # type: ignore[arg-type]
    assert error == "unknown_value_semantics"


@pytest.mark.parametrize(
    "rule",
    [
        {"mode": "ordered", "ordered_values": []},
        {"mode": "numeric_minimum"},
        {"mode": "numeric_maximum"},
        {"mode": "numeric_range", "minimum": 2, "maximum": 1},
        {"mode": "custom"},
    ],
)
def test_comparison_modes_require_complete_parameters(rule: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ComparisonRule.model_validate(rule)


@pytest.mark.parametrize(
    ("configured", "baseline", "rule", "expected"),
    [
        (True, False, ComparisonRule(mode=ComparisonMode.EXACT), AlignmentStatus.DIFFERENT),
        ("block", "block", ComparisonRule(mode=ComparisonMode.EXACT), AlignmentStatus.ALIGNED),
        (
            "high",
            "medium",
            ComparisonRule(mode=ComparisonMode.ORDERED, ordered_values=["low", "medium", "high"]),
            AlignmentStatus.MORE_RESTRICTIVE,
        ),
        (
            "low",
            "medium",
            ComparisonRule(mode=ComparisonMode.ORDERED, ordered_values=["low", "medium", "high"]),
            AlignmentStatus.LESS_RESTRICTIVE,
        ),
        (
            15,
            10,
            ComparisonRule(mode=ComparisonMode.NUMERIC_MINIMUM, minimum=Decimal(10)),
            AlignmentStatus.MORE_RESTRICTIVE,
        ),
        (
            15,
            10,
            ComparisonRule(mode=ComparisonMode.NUMERIC_MAXIMUM, maximum=Decimal(10)),
            AlignmentStatus.LESS_RESTRICTIVE,
        ),
        (
            5,
            5,
            ComparisonRule(
                mode=ComparisonMode.NUMERIC_RANGE, minimum=Decimal(1), maximum=Decimal(10)
            ),
            AlignmentStatus.ALIGNED,
        ),
        (
            ["a", "b"],
            ["b", "a"],
            ComparisonRule(mode=ComparisonMode.SET_EQUALS),
            AlignmentStatus.ALIGNED,
        ),
        (
            ["a", "b", "c"],
            ["a", "b"],
            ComparisonRule(mode=ComparisonMode.SET_CONTAINS),
            AlignmentStatus.MORE_RESTRICTIVE,
        ),
        (
            ["a", "c"],
            ["a", "b"],
            ComparisonRule(mode=ComparisonMode.SET_CONTAINS),
            AlignmentStatus.DIFFERENT,
        ),
        (
            ["b", "a"],
            ["a", "b"],
            ComparisonRule(mode=ComparisonMode.LIST_EQUALS),
            AlignmentStatus.DIFFERENT,
        ),
        ("a", "b", ComparisonRule(mode=ComparisonMode.NOT_ORDERABLE), AlignmentStatus.DIFFERENT),
        (
            "a",
            "b",
            ComparisonRule(mode=ComparisonMode.CUSTOM, custom_rule_id="future"),
            AlignmentStatus.NOT_EVALUABLE,
        ),
    ],
)
def test_explicit_comparison_modes(
    configured: object,
    baseline: object,
    rule: ComparisonRule,
    expected: AlignmentStatus,
) -> None:
    assert compare_values(configured, baseline, rule) is expected  # type: ignore[arg-type]


def test_boolean_values_have_no_global_security_order() -> None:
    rule = ComparisonRule(mode=ComparisonMode.EXACT)
    assert compare_values(True, False, rule) is AlignmentStatus.DIFFERENT
    assert compare_values(False, True, rule) is AlignmentStatus.DIFFERENT
