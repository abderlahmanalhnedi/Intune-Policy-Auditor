from pathlib import Path

import pytest

import intune_auditor.version as version
from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.enums import AlignmentStatus
from intune_auditor.domain.models import AuditConfiguration, AuditContext

ROOT = Path(__file__).resolve().parents[3]


def test_limited_analysis_keeps_every_setting_not_evaluable() -> None:
    service = AuditService(ROOT)
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    result = service.audit_uploads(
        [(policy.name, policy.read_bytes())],
        AuditConfiguration(active_pack_ids=[]),
    )

    assert result.selected_pack_manifests == []
    assert result.policies
    assert all(
        setting.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
        for policy_result in result.policies
        for setting in policy_result.settings
    )


def test_unknown_selected_baseline_is_rejected() -> None:
    service = AuditService(ROOT)
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    with pytest.raises(ValueError, match="missing_baseline"):
        service.audit_uploads(
            [(policy.name, policy.read_bytes())],
            AuditConfiguration(active_pack_ids=["missing.pack"]),
        )


def test_inactive_pack_cannot_be_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AuditService(ROOT)
    inactive = service.installed_packs()[0].model_copy(update={"active": False})
    policy = ROOT / "samples" / "policies" / "01-core-device-security.json"
    monkeypatch.setattr(service, "installed_packs", lambda: [inactive])

    with pytest.raises(ValueError, match="missing_baseline"):
        service.audit_uploads(
            [(policy.name, policy.read_bytes())],
            AuditConfiguration(active_pack_ids=[inactive.manifest.pack_id]),
        )


def test_runtime_privacy_defaults_are_respected_without_persistence() -> None:
    preferences = AuditService(
        ROOT,
        retention_days=45,
        history_enabled=True,
        save_reports=True,
    ).preferences()
    assert preferences["history_enabled"] is True
    assert preferences["save_reports"] is True
    assert preferences["retention_days"] == 45


def test_cache_key_covers_trust_inputs_but_not_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AuditService(ROOT)
    pack = service.installed_packs()[0]
    base_configuration = AuditConfiguration(
        language="de",
        active_pack_ids=[pack.manifest.pack_id],
        context=AuditContext(physical_device=True),
    )
    key = service.cache_key("a" * 64, [pack], "b" * 64, base_configuration)

    assert (
        service.cache_key(
            "a" * 64,
            [pack],
            "b" * 64,
            base_configuration.model_copy(update={"language": "en"}),
        )
        == key
    )
    assert service.cache_key("c" * 64, [pack], "b" * 64, base_configuration) != key
    assert service.cache_key("a" * 64, [pack], "d" * 64, base_configuration) != key
    changed_pack = pack.model_copy(
        update={"manifest": pack.manifest.model_copy(update={"data_sha256": "e" * 64})}
    )
    assert service.cache_key("a" * 64, [changed_pack], "b" * 64, base_configuration) != key
    changed_context = base_configuration.model_copy(
        update={"context": AuditContext(physical_device=False)}
    )
    assert service.cache_key("a" * 64, [pack], "b" * 64, changed_context) != key

    monkeypatch.setattr(version, "PARSER_VERSION", "test-parser-version")
    assert service.cache_key("a" * 64, [pack], "b" * 64, base_configuration) != key
