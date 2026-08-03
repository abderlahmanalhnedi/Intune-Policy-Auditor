from datetime import date

from intune_auditor.deviations.service import match_deviation
from intune_auditor.domain.enums import AlignmentStatus
from intune_auditor.domain.models import AcceptedDeviation


def deviation() -> AcceptedDeviation:
    return AcceptedDeviation(
        deviation_id="test",
        schema_version="1.0",
        canonical_setting_id="windows:test:device:value",
        policy_id="policy",
        accepted_value=10,
        reason="Synthetic test",
        owner="Synthetic owner",
        approver="Synthetic approver",
        ticket="TEST-1",
        valid_from=date(2026, 1, 1),
        valid_until=date(2026, 12, 31),
    )


def test_active_value_exact_deviation_changes_effective_status() -> None:
    status, matched = match_deviation(
        [deviation()], "windows:test:device:value", "policy", 10, date(2026, 8, 3)
    )
    assert status is AlignmentStatus.ACCEPTED_DEVIATION
    assert matched is not None


def test_expired_deviation_is_visible() -> None:
    status, _ = match_deviation(
        [deviation()], "windows:test:device:value", "policy", 10, date(2027, 1, 1)
    )
    assert status is AlignmentStatus.EXPIRED_DEVIATION


def test_different_value_never_suppresses() -> None:
    status, matched = match_deviation(
        [deviation()], "windows:test:device:value", "policy", 11, date(2026, 8, 3)
    )
    assert status is None
    assert matched is None
