"""Validated JSON knowledge-pack loader."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError

from intune_auditor.domain.enums import (
    ComparisonMode,
    EvidenceConfidence,
    EvidenceType,
    FindingSeverity,
    KnowledgePackStatus,
    ValueType,
)
from intune_auditor.domain.models import EvidenceSource, KnowledgePackManifest, KnowledgeSetting
from intune_auditor.security.json_safety import strict_json_loads
from intune_auditor.version import KNOWLEDGE_PACK_SCHEMA_VERSION

_OFFICIAL_DOMAINS = {
    "learn.microsoft.com",
    "microsoft.com",
    "download.microsoft.com",
    "graph.microsoft.com",
    "github.com",
    "support.apple.com",
    "developer.apple.com",
}

_MICROSOFT_BASELINE_EVIDENCE_TYPES = {
    EvidenceType.MICROSOFT_SECURITY_BASELINE,
    EvidenceType.MICROSOFT_CSP_DOCUMENTATION,
    EvidenceType.MICROSOFT_INTUNE_DOCUMENTATION,
    EvidenceType.MICROSOFT_GRAPH_METADATA,
    EvidenceType.MICROSOFT_SECURITY_COMPLIANCE_TOOLKIT,
}


def official_reference_allowed(reference: object) -> bool:
    parsed = urlparse(str(reference))
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if host == "github.com":
        owner = parsed.path.strip("/").split("/", maxsplit=1)[0].lower()
        return owner in {"microsoft", "microsoftdocs"}
    return (
        host
        in {
            "learn.microsoft.com",
            "download.microsoft.com",
            "graph.microsoft.com",
            "support.apple.com",
            "developer.apple.com",
        }
        or host == "microsoft.com"
        or host.endswith(".microsoft.com")
    )


def official_domain_allowed(domain: str) -> bool:
    normalized = domain.lower().rstrip(".")
    return (
        normalized in _OFFICIAL_DOMAINS
        or normalized == "github.com"
        or normalized.endswith(".microsoft.com")
    )


def source_domain_matches_reference(domain: str, reference: object) -> bool:
    declared = domain.casefold().rstrip(".")
    referenced = (urlparse(str(reference)).hostname or "").casefold().rstrip(".")
    return bool(declared) and declared == referenced


def exact_official_evidence_allowed(vendor: str, evidence: EvidenceSource) -> bool:
    """Return whether evidence can support an exact vendor-baseline judgment."""
    if (
        not evidence.is_official
        or evidence.confidence is not EvidenceConfidence.EXACT
        or not official_domain_allowed(evidence.source_domain)
        or not official_reference_allowed(evidence.source_reference)
        or not source_domain_matches_reference(evidence.source_domain, evidence.source_reference)
    ):
        return False
    normalized_vendor = " ".join(vendor.casefold().split())
    if normalized_vendor in {"microsoft", "microsoft corporation"}:
        return evidence.evidence_type in _MICROSOFT_BASELINE_EVIDENCE_TYPES
    if normalized_vendor in {"apple", "apple inc", "apple inc."}:
        return evidence.evidence_type is EvidenceType.APPLE_PLATFORM_DOCUMENTATION
    return False


def _has_exact_value_semantics(manifest: KnowledgePackManifest, setting: KnowledgeSetting) -> bool:
    evidence_is_exact = (
        any(item.confidence is EvidenceConfidence.EXACT for item in setting.evidence_sources)
        if manifest.status is KnowledgePackStatus.SYNTHETIC
        else any(
            exact_official_evidence_allowed(manifest.vendor, item)
            for item in setting.evidence_sources
        )
    )
    return (
        evidence_is_exact
        and setting.value_definition.value_type is not ValueType.UNKNOWN
        and setting.comparison_rule.mode is not ComparisonMode.CUSTOM
    )


def _serialized_json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class PackValidationIssue(BaseModel):
    code: str
    path: str
    message: str


class PackValidationReport(BaseModel):
    valid: bool
    pack_id: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    calculated_data_sha256: str | None = None
    issues: list[PackValidationIssue] = Field(default_factory=list)


class LoadedKnowledgePack(BaseModel):
    manifest: KnowledgePackManifest
    settings: list[KnowledgeSetting]
    path: Path
    active: bool = True

    model_config = {"arbitrary_types_allowed": True}

    @property
    def by_canonical_id(self) -> dict[str, KnowledgeSetting]:
        return {setting.canonical_setting_id: setting for setting in self.settings}

    @property
    def alias_index(self) -> dict[str, KnowledgeSetting]:
        return {alias.lower(): setting for setting in self.settings for alias in setting.aliases}

    @property
    def age_days(self) -> int:
        return max((date.today() - self.manifest.verified_at).days, 0)


class KnowledgePackLoader:
    @staticmethod
    def bundled_setting_schema() -> Path:
        return (
            Path(__file__).resolve().parents[4]
            / "knowledge-packs"
            / "schema"
            / "setting.schema.json"
        )

    def validate(self, path: Path) -> PackValidationReport:
        issues: list[PackValidationIssue] = []
        manifest_path = path / "manifest.json"
        if not manifest_path.is_file():
            return PackValidationReport(
                valid=False,
                issues=[
                    PackValidationIssue(
                        code="missing_manifest",
                        path="manifest.json",
                        message="Manifest file is missing.",
                    )
                ],
            )
        try:
            manifest_raw = strict_json_loads(manifest_path.read_text(encoding="utf-8"))
            manifest = KnowledgePackManifest.model_validate(manifest_raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            return PackValidationReport(
                valid=False,
                issues=[
                    PackValidationIssue(
                        code="invalid_manifest", path="manifest.json", message=str(exc)
                    )
                ],
            )
        if manifest.schema_version != KNOWLEDGE_PACK_SCHEMA_VERSION:
            issues.append(
                PackValidationIssue(
                    code="unsupported_schema_version",
                    path="schema_version",
                    message="Unsupported knowledge-pack schema version.",
                )
            )
        if not manifest.baseline_version.strip():
            issues.append(
                PackValidationIssue(
                    code="missing_baseline_version",
                    path="baseline_version",
                    message="A baseline version is required.",
                )
            )

        settings_path = (path / manifest.settings_file).resolve()
        try:
            settings_path.relative_to(path.resolve())
        except ValueError:
            issues.append(
                PackValidationIssue(
                    code="unsafe_settings_path",
                    path="settings_file",
                    message="Settings file leaves the pack directory.",
                )
            )
            return PackValidationReport(valid=False, pack_id=manifest.pack_id, issues=issues)
        if not settings_path.is_file():
            issues.append(
                PackValidationIssue(
                    code="missing_settings_file",
                    path=manifest.settings_file,
                    message="Settings file is missing.",
                )
            )
            return PackValidationReport(valid=False, pack_id=manifest.pack_id, issues=issues)

        raw_bytes = settings_path.read_bytes()
        calculated_hash = hashlib.sha256(raw_bytes).hexdigest()
        if calculated_hash != manifest.data_sha256:
            issues.append(
                PackValidationIssue(
                    code="hash_mismatch",
                    path="data_sha256",
                    message="Settings SHA-256 does not match the manifest.",
                )
            )
        schema_path = self.bundled_setting_schema()
        if schema_path.is_file():
            calculated_schema_hash = hashlib.sha256(schema_path.read_bytes()).hexdigest()
            if calculated_schema_hash != manifest.schema_sha256:
                issues.append(
                    PackValidationIssue(
                        code="schema_hash_mismatch",
                        path="schema_sha256",
                        message="Setting schema SHA-256 does not match the bundled schema.",
                    )
                )
        try:
            raw_settings = strict_json_loads(raw_bytes.decode("utf-8"))
            if not isinstance(raw_settings, list):
                raise ValueError("settings root must be an array")
            settings = [KnowledgeSetting.model_validate(item) for item in raw_settings]
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            issues.append(
                PackValidationIssue(
                    code="invalid_settings", path=manifest.settings_file, message=str(exc)
                )
            )
            return PackValidationReport(
                valid=False,
                pack_id=manifest.pack_id,
                calculated_data_sha256=calculated_hash,
                issues=issues,
            )

        if len(settings) != manifest.setting_count:
            issues.append(
                PackValidationIssue(
                    code="setting_count_mismatch",
                    path="setting_count",
                    message="Manifest setting count does not match the settings file.",
                )
            )
        canonical_owners = {
            setting.canonical_setting_id.casefold(): setting.canonical_setting_id
            for setting in settings
        }
        seen_ids: dict[str, str] = {}
        alias_owners: dict[str, str] = {}
        # Deliberately imported here so the pack loader remains usable while the
        # evaluation package initializes its engine, which itself consumes packs.
        from intune_auditor.evaluation.value_comparators import canonicalize_value

        for index, setting in enumerate(settings):
            prefix = f"settings[{index}]"
            normalized_id = setting.canonical_setting_id.casefold()
            if normalized_id in seen_ids:
                issues.append(
                    PackValidationIssue(
                        code="duplicate_canonical_identifier",
                        path=f"{prefix}.canonical_setting_id",
                        message="Canonical setting identifier is duplicated.",
                    )
                )
            seen_ids[normalized_id] = setting.canonical_setting_id
            aliases_in_setting: set[str] = set()
            for alias in setting.aliases:
                normalized_alias = alias.casefold()
                owner = alias_owners.get(normalized_alias)
                canonical_owner = canonical_owners.get(normalized_alias)
                if (
                    normalized_alias in aliases_in_setting
                    or owner is not None
                    or canonical_owner is not None
                ):
                    collision_owner = canonical_owner or owner or setting.canonical_setting_id
                    issues.append(
                        PackValidationIssue(
                            code="alias_collision",
                            path=f"{prefix}.aliases",
                            message=f"Alias collides with {collision_owner}.",
                        )
                    )
                else:
                    alias_owners[normalized_alias] = setting.canonical_setting_id
                aliases_in_setting.add(normalized_alias)
            if setting.comparison_rule.mode is ComparisonMode.ORDERED:
                serialized = [
                    json.dumps(value, sort_keys=True)
                    for value in setting.comparison_rule.ordered_values
                ]
                if len(serialized) != len(set(serialized)):
                    issues.append(
                        PackValidationIssue(
                            code="duplicate_ordered_values",
                            path=f"{prefix}.comparison_rule",
                            message="Ordered comparison contains duplicate values.",
                        )
                    )
            if not setting.evidence_sources:
                issues.append(
                    PackValidationIssue(
                        code="missing_evidence",
                        path=f"{prefix}.evidence_sources",
                        message="At least one evidence source is required.",
                    )
                )
            for evidence_index, evidence in enumerate(setting.evidence_sources):
                if evidence.is_official and not official_domain_allowed(evidence.source_domain):
                    issues.append(
                        PackValidationIssue(
                            code="invalid_source_domain",
                            path=f"{prefix}.evidence_sources[{evidence_index}]",
                            message="Official evidence domain is not allowed.",
                        )
                    )
                if evidence.is_official and not official_reference_allowed(
                    evidence.source_reference
                ):
                    issues.append(
                        PackValidationIssue(
                            code="invalid_source_reference",
                            path=f"{prefix}.evidence_sources[{evidence_index}]",
                            message="Official evidence URL is not on an allowed source path.",
                        )
                    )
                if evidence.is_official and not source_domain_matches_reference(
                    evidence.source_domain, evidence.source_reference
                ):
                    issues.append(
                        PackValidationIssue(
                            code="source_domain_reference_mismatch",
                            path=f"{prefix}.evidence_sources[{evidence_index}]",
                            message="Declared source domain does not match the evidence URL.",
                        )
                    )
            if manifest.status is not KnowledgePackStatus.SYNTHETIC and not any(
                exact_official_evidence_allowed(manifest.vendor, evidence)
                for evidence in setting.evidence_sources
            ):
                issues.append(
                    PackValidationIssue(
                        code="missing_exact_official_evidence",
                        path=f"{prefix}.evidence_sources",
                        message="A non-synthetic setting requires exact official evidence.",
                    )
                )
            if setting.severity_if_less_restrictive is FindingSeverity.CRITICAL and not any(
                exact_official_evidence_allowed(manifest.vendor, evidence)
                for evidence in setting.evidence_sources
            ):
                issues.append(
                    PackValidationIssue(
                        code="critical_without_exact_evidence",
                        path=f"{prefix}.severity_if_less_restrictive",
                        message="Critical impact requires exact official evidence.",
                    )
                )
            definition_without_mappings = setting.value_definition.model_copy(
                update={"allowed_values": [], "semantic_mapping": {}}
            )
            canonical_baseline, baseline_error = canonicalize_value(
                setting.baseline_value, definition_without_mappings
            )
            baseline_semantics_valid = baseline_error is None and _serialized_json_value(
                canonical_baseline
            ) == _serialized_json_value(setting.baseline_value)
            allowed = {
                _serialized_json_value(item) for item in setting.value_definition.allowed_values
            }
            if isinstance(setting.baseline_value, list) and setting.value_definition.value_type in {
                ValueType.LIST,
                ValueType.SET,
            }:
                baseline_allowed = all(
                    _serialized_json_value(item) in allowed for item in setting.baseline_value
                )
            else:
                baseline_allowed = _serialized_json_value(setting.baseline_value) in allowed
            if not baseline_semantics_valid or (allowed and not baseline_allowed):
                issues.append(
                    PackValidationIssue(
                        code="invalid_canonical_value",
                        path=f"{prefix}.baseline_value",
                        message="Baseline value is not in the allowed canonical values.",
                    )
                )
            comparison_valid = True
            rule = setting.comparison_rule
            if rule.mode is ComparisonMode.ORDERED:
                comparison_valid = _serialized_json_value(setting.baseline_value) in {
                    _serialized_json_value(item) for item in rule.ordered_values
                }
            elif rule.mode is ComparisonMode.NUMERIC_MINIMUM:
                try:
                    comparison_valid = Decimal(str(canonical_baseline)) == rule.minimum
                except (InvalidOperation, TypeError, ValueError):
                    comparison_valid = False
            elif rule.mode is ComparisonMode.NUMERIC_MAXIMUM:
                try:
                    comparison_valid = Decimal(str(canonical_baseline)) == rule.maximum
                except (InvalidOperation, TypeError, ValueError):
                    comparison_valid = False
            elif rule.mode in {
                ComparisonMode.SET_EQUALS,
                ComparisonMode.SET_CONTAINS,
                ComparisonMode.LIST_EQUALS,
            }:
                comparison_valid = isinstance(setting.baseline_value, list)
            if not comparison_valid:
                issues.append(
                    PackValidationIssue(
                        code="invalid_comparison_rule",
                        path=f"{prefix}.comparison_rule",
                        message="Comparison parameters do not match the canonical baseline value.",
                    )
                )
        calculated_exact_values = sum(
            _has_exact_value_semantics(manifest, setting) for setting in settings
        )
        if calculated_exact_values != manifest.exact_value_count:
            issues.append(
                PackValidationIssue(
                    code="exact_value_count_mismatch",
                    path="exact_value_count",
                    message="Manifest exact value count does not match validated settings.",
                )
            )
        if manifest.status is not KnowledgePackStatus.SYNTHETIC and not official_domain_allowed(
            manifest.source_domain
        ):
            issues.append(
                PackValidationIssue(
                    code="invalid_source_domain",
                    path="source_domain",
                    message="Non-synthetic packs require an approved official source domain.",
                )
            )
        if manifest.status is not KnowledgePackStatus.SYNTHETIC and not official_reference_allowed(
            manifest.source_reference
        ):
            issues.append(
                PackValidationIssue(
                    code="invalid_source_reference",
                    path="source_reference",
                    message="Non-synthetic pack source URL is not allowed.",
                )
            )
        if (
            manifest.status is not KnowledgePackStatus.SYNTHETIC
            and not source_domain_matches_reference(
                manifest.source_domain, manifest.source_reference
            )
        ):
            issues.append(
                PackValidationIssue(
                    code="source_domain_reference_mismatch",
                    path="source_domain",
                    message="Declared pack source domain does not match the source URL.",
                )
            )
        return PackValidationReport(
            valid=not issues,
            pack_id=manifest.pack_id,
            calculated_data_sha256=calculated_hash,
            issues=issues,
        )

    def load(self, path: Path) -> LoadedKnowledgePack:
        report = self.validate(path)
        if not report.valid:
            messages = "; ".join(issue.code for issue in report.issues)
            raise ValueError(f"invalid_knowledge_pack:{messages}")
        manifest = KnowledgePackManifest.model_validate(
            strict_json_loads((path / "manifest.json").read_text(encoding="utf-8"))
        )
        settings_raw = strict_json_loads(
            (path / manifest.settings_file).read_text(encoding="utf-8")
        )
        if not isinstance(settings_raw, list):
            raise ValueError("invalid_knowledge_pack:invalid_settings")
        settings = [KnowledgeSetting.model_validate(item) for item in settings_raw]
        return LoadedKnowledgePack(manifest=manifest, settings=settings, path=path.resolve())
