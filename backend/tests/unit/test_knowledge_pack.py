import hashlib
import json
from pathlib import Path

from intune_auditor.knowledge.loader import KnowledgePackLoader, official_reference_allowed

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "knowledge-packs" / "synthetic" / "test-baseline"


def write_pack(
    target: Path,
    settings: list[dict[str, object]],
    manifest_updates: dict[str, object] | None = None,
) -> None:
    target.mkdir()
    settings_bytes = json.dumps(settings, separators=(",", ":")).encode()
    (target / "settings.json").write_bytes(settings_bytes)
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    manifest["data_sha256"] = hashlib.sha256(settings_bytes).hexdigest()
    if manifest_updates:
        manifest.update(manifest_updates)
    (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_synthetic_pack_is_valid_and_hash_bound() -> None:
    report = KnowledgePackLoader().validate(PACK)
    assert report.valid, report.issues
    assert report.calculated_data_sha256 is not None


def test_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "pack"
    target.mkdir()
    (target / "manifest.json").write_bytes((PACK / "manifest.json").read_bytes())
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[0]["baseline_value"] = "audit"
    (target / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    report = KnowledgePackLoader().validate(target)
    assert not report.valid
    assert "hash_mismatch" in {issue.code for issue in report.issues}


def test_non_synthetic_pack_requires_exact_allowlisted_evidence(tmp_path: Path) -> None:
    target = tmp_path / "pack"
    target.mkdir()
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[0]["evidence_sources"] = [
        {
            "evidence_type": "microsoft_intune_documentation",
            "title": "Untrusted reference",
            "source_reference": "https://example.invalid/not-official",
            "source_domain": "learn.microsoft.com",
            "verified_at": "2026-08-03",
            "confidence": "partial",
            "is_official": True,
        }
    ]
    settings_bytes = json.dumps(settings, separators=(",", ":")).encode()
    (target / "settings.json").write_bytes(settings_bytes)
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "verified",
            "source_domain": "learn.microsoft.com",
            "source_reference": "https://example.invalid/not-official",
            "data_sha256": hashlib.sha256(settings_bytes).hexdigest(),
        }
    )
    (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = KnowledgePackLoader().validate(target)
    codes = {issue.code for issue in report.issues}
    assert "invalid_source_reference" in codes
    assert "missing_exact_official_evidence" in codes


def test_non_synthetic_pack_rejects_organizational_evidence_marked_official(
    tmp_path: Path,
) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    for setting in settings:
        setting["evidence_sources"] = [
            {
                "evidence_type": "organizational_requirement",
                "title": "Not Microsoft baseline evidence",
                "source_reference": "https://learn.microsoft.com/en-us/intune/",
                "source_domain": "learn.microsoft.com",
                "verified_at": "2026-08-03",
                "confidence": "exact",
                "is_official": True,
            }
        ]
    target = tmp_path / "wrong-evidence-type"
    write_pack(
        target,
        settings,
        {
            "vendor": "Microsoft",
            "status": "verified",
            "source_domain": "learn.microsoft.com",
            "source_reference": "https://learn.microsoft.com/en-us/intune/",
        },
    )

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "missing_exact_official_evidence" in codes
    assert "exact_value_count_mismatch" in codes


def test_alias_cannot_shadow_a_canonical_identifier(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[0]["aliases"] = [settings[1]["canonical_setting_id"]]
    target = tmp_path / "canonical-alias-collision"
    write_pack(target, settings)

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "alias_collision" in codes


def test_duplicate_alias_and_exact_value_count_mismatch_are_rejected(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[0]["aliases"] = ["same-alias", "SAME-ALIAS"]
    target = tmp_path / "duplicate-alias"
    write_pack(target, settings, {"exact_value_count": 6})

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "alias_collision" in codes
    assert "exact_value_count_mismatch" in codes


def test_critical_impact_requires_exact_official_evidence(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[0]["severity_if_less_restrictive"] = "critical"
    target = tmp_path / "critical-with-synthetic-evidence"
    write_pack(target, settings)

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "critical_without_exact_evidence" in codes


def test_only_verified_microsoft_github_owners_are_allowed() -> None:
    assert official_reference_allowed("https://github.com/microsoft/example")
    assert official_reference_allowed("https://github.com/MicrosoftDocs/example")
    assert not official_reference_allowed("https://github.com/intune/example")
    assert not official_reference_allowed("https://github.com/microsoft-lookalike/example")


def test_declared_official_domain_must_match_reference(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    for setting in settings:
        setting["evidence_sources"] = [
            {
                "evidence_type": "microsoft_intune_documentation",
                "title": "Official evidence with false declared domain",
                "source_reference": "https://learn.microsoft.com/en-us/intune/",
                "source_domain": "graph.microsoft.com",
                "verified_at": "2026-08-03",
                "confidence": "exact",
                "is_official": True,
            }
        ]
    target = tmp_path / "source-domain-mismatch"
    write_pack(
        target,
        settings,
        {
            "vendor": "Microsoft",
            "status": "verified",
            "source_domain": "graph.microsoft.com",
            "source_reference": "https://learn.microsoft.com/en-us/intune/",
        },
    )

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "source_domain_reference_mismatch" in codes
    assert "missing_exact_official_evidence" in codes


def test_vendor_name_cannot_spoof_microsoft_evidence(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    for setting in settings:
        setting["evidence_sources"] = [
            {
                "evidence_type": "microsoft_intune_documentation",
                "title": "Microsoft documentation",
                "source_reference": "https://learn.microsoft.com/en-us/intune/",
                "source_domain": "learn.microsoft.com",
                "verified_at": "2026-08-03",
                "confidence": "exact",
                "is_official": True,
            }
        ]
    target = tmp_path / "vendor-spoof"
    write_pack(
        target,
        settings,
        {
            "vendor": "Not Microsoft",
            "status": "verified",
            "source_domain": "learn.microsoft.com",
            "source_reference": "https://learn.microsoft.com/en-us/intune/",
        },
    )

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "missing_exact_official_evidence" in codes
    assert "exact_value_count_mismatch" in codes


def test_baseline_value_must_have_canonical_type_and_allowed_value(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[0]["baseline_value"] = 1
    target = tmp_path / "invalid-canonical-baseline"
    write_pack(target, settings)

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "invalid_canonical_value" in codes


def test_numeric_comparison_parameter_must_match_baseline(tmp_path: Path) -> None:
    settings = json.loads((PACK / "settings.json").read_text(encoding="utf-8"))
    settings[1]["comparison_rule"] = {"mode": "numeric_minimum", "minimum": 12}
    target = tmp_path / "comparison-baseline-mismatch"
    write_pack(target, settings)

    codes = {issue.code for issue in KnowledgePackLoader().validate(target).issues}
    assert "invalid_comparison_rule" in codes
