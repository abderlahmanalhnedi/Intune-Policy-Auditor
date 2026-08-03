from intune_auditor.domain.enums import Platform, Scope
from intune_auditor.domain.identifiers import canonical_setting_id, normalize_setting_id


def test_normalizes_policy_csp_identifier_without_inferring_semantics() -> None:
    assert (
        normalize_setting_id("./Device/Vendor/MSFT/Policy/Config/Firewall/EnableFirewall")
        == "firewall/enablefirewall"
    )


def test_canonical_identity_keeps_platform_and_scope() -> None:
    identifier = canonical_setting_id("com.apple.applicationaccess", Platform.MACOS, Scope.DEVICE)
    assert identifier == "macos:intune:device:com.apple.applicationaccess"


def test_display_name_variants_are_not_merged() -> None:
    assert normalize_setting_id("Allow camera") != normalize_setting_id("Camera allowed")
