"""Parser for common Intune export shapes without display-name inference."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from intune_auditor.domain.enums import (
    AssignmentTargetType,
    DiagnosticSeverity,
    EvidenceConfidence,
    FilterMode,
    Platform,
    PolicyKind,
    Scope,
)
from intune_auditor.domain.identifiers import canonical_setting_id, normalize_setting_id
from intune_auditor.domain.models import (
    AssignmentFilter,
    AssignmentTarget,
    JsonValue,
    ParserDiagnostic,
    ParserResult,
    PolicyDocument,
    SettingObservation,
    UploadedSource,
)
from intune_auditor.security.json_safety import strict_json_loads
from intune_auditor.security.limits import ProcessingLimits
from intune_auditor.security.uploads import ValidatedUpload
from intune_auditor.version import PARSER_VERSION

_SETTING_ID_KEYS = (
    "settingDefinitionId",
    "setting_definition_id",
    "definitionId",
    "definition_id",
    "omaUri",
    "oma_uri",
)
_VALUE_CONTAINER_KEYS = (
    "simpleSettingValue",
    "choiceSettingValue",
    "simpleSettingCollectionValue",
    "choiceSettingCollectionValue",
)


def _json_depth(value: object, limit: int, maximum_string_length: int) -> int:
    stack: list[tuple[object, int]] = [(value, 1)]
    maximum = 0
    while stack:
        current, depth = stack.pop()
        maximum = max(maximum, depth)
        if maximum > limit:
            raise ValueError("json_nesting_depth_exceeded")
        if isinstance(current, dict):
            if any(len(str(key)) > maximum_string_length for key in current):
                raise ValueError("maximum_string_length_exceeded")
            stack.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
        elif isinstance(current, str) and len(current) > maximum_string_length:
            raise ValueError("maximum_string_length_exceeded")
    return maximum


def _platform(value: object) -> Platform:
    aliases = {
        "windows": Platform.WINDOWS,
        "windows10": Platform.WINDOWS,
        "windows11": Platform.WINDOWS,
        "windows10andlater": Platform.WINDOWS,
        "windows11andlater": Platform.WINDOWS,
        "windows10x": Platform.WINDOWS,
        "macos": Platform.MACOS,
        "osx": Platform.MACOS,
        "ios": Platform.IOS,
        "ipados": Platform.IPADOS,
        "android": Platform.ANDROID,
        "androidenterprise": Platform.ANDROID,
        "androiddeviceadministrator": Platform.ANDROID,
        "androidforwork": Platform.ANDROID,
        "androidworkprofile": Platform.ANDROID,
        "androidaosp": Platform.ANDROID,
        "aosp": Platform.ANDROID,
        "linux": Platform.LINUX,
    }
    values = value if isinstance(value, list) else [value]
    matched = {
        aliases[normalized]
        for item in values
        if (normalized := re.sub(r"[^a-z0-9]", "", str(item or "").casefold())) in aliases
    }
    return matched.pop() if len(matched) == 1 else Platform.UNKNOWN


def _policy_kind(value: object) -> PolicyKind:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "settingscatalog": PolicyKind.SETTINGS_CATALOG,
        "settings_catalog": PolicyKind.SETTINGS_CATALOG,
        "endpointsecurity": PolicyKind.ENDPOINT_SECURITY,
        "endpoint_security": PolicyKind.ENDPOINT_SECURITY,
        "securitybaseline": PolicyKind.SECURITY_BASELINE,
        "security_baseline": PolicyKind.SECURITY_BASELINE,
        "deviceconfiguration": PolicyKind.DEVICE_CONFIGURATION,
        "device_configuration": PolicyKind.DEVICE_CONFIGURATION,
        "compliance": PolicyKind.COMPLIANCE,
        "administrativetemplates": PolicyKind.ADMINISTRATIVE_TEMPLATES,
        "administrative_templates": PolicyKind.ADMINISTRATIVE_TEMPLATES,
        "custom": PolicyKind.CUSTOM,
    }
    return aliases.get(normalized, PolicyKind.UNKNOWN)


def _scope(value: object) -> Scope:
    lowered = str(value or "").lower()
    if lowered == "device":
        return Scope.DEVICE
    if lowered == "user":
        return Scope.USER
    if lowered == "both":
        return Scope.BOTH
    return Scope.UNKNOWN


def _first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _extract_value(setting: dict[str, Any]) -> JsonValue:
    if "value" in setting:
        return setting["value"]  # type: ignore[no-any-return]
    for container_key in _VALUE_CONTAINER_KEYS:
        container = setting.get(container_key)
        if isinstance(container, dict):
            if "value" in container:
                return container["value"]  # type: ignore[no-any-return]
            if "values" in container:
                return container["values"]  # type: ignore[no-any-return]
        if isinstance(container, list):
            values: list[JsonValue] = []
            for item in container:
                values.append(item.get("value") if isinstance(item, dict) else item)
            return values
    return None


def _setting_candidates(
    value: object, path: str = "$", inside_identified_setting: bool = False
) -> Iterator[tuple[dict[str, Any], str]]:
    if isinstance(value, dict):
        has_identifier = any(key in value for key in _SETTING_ID_KEYS)
        collection_wrapper = (
            isinstance(value.get("value"), list)
            and all(isinstance(item, dict) for item in value["value"])
            and not any(key in value for key in ("displayName", "name", "settingName"))
        )
        looks_like_unidentified_setting = not inside_identified_setting and (
            ("value" in value and not collection_wrapper)
            or any(key in value for key in _VALUE_CONTAINER_KEYS)
        )
        if has_identifier or looks_like_unidentified_setting:
            yield value, path
        for key, child in value.items():
            yield from _setting_candidates(
                child,
                f"{path}.{key}",
                inside_identified_setting or has_identifier,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _setting_candidates(child, f"{path}[{index}]", inside_identified_setting)


def _assignment_target(raw: dict[str, Any], platform: Platform) -> AssignmentTarget:
    target = raw.get("target", raw)
    if not isinstance(target, dict):
        return AssignmentTarget(target_type=AssignmentTargetType.UNKNOWN)
    odata_type = str(target.get("@odata.type", "")).lower()
    explicit_type = str(target.get("type", target.get("targetType", ""))).lower()
    if "alldevices" in odata_type or explicit_type in {"all_devices", "alldevices"}:
        target_type = AssignmentTargetType.ALL_DEVICES
        scope = Scope.DEVICE
    elif (
        "alllicensedusers" in odata_type
        or "allusers" in odata_type
        or explicit_type
        in {
            "all_users",
            "allusers",
        }
    ):
        target_type = AssignmentTargetType.ALL_USERS
        scope = Scope.USER
    elif "exclusion" in odata_type or explicit_type in {"exclude_group", "exclusion_group"}:
        target_type = AssignmentTargetType.EXCLUSION_GROUP
        scope = _scope(target.get("scope"))
    elif target.get("groupId") or explicit_type == "group" or "groupassignmenttarget" in odata_type:
        target_type = AssignmentTargetType.GROUP
        scope = _scope(target.get("scope"))
    else:
        target_type = AssignmentTargetType.UNKNOWN
        scope = Scope.UNKNOWN

    raw_filter_mode = target.get("deviceAndAppManagementAssignmentFilterType") or target.get(
        "filterMode"
    )
    filter_model = None
    if raw_filter_mode:
        filter_platform = _platform(
            target.get("filterPlatform") or target.get("assignmentFilterPlatform")
        )
        filter_model = AssignmentFilter(
            filter_id=target.get("deviceAndAppManagementAssignmentFilterId")
            or target.get("filterId"),
            display_name=target.get("filterDisplayName"),
            mode=FilterMode.EXCLUDE
            if str(raw_filter_mode).lower() == "exclude"
            else FilterMode.INCLUDE,
            rule=target.get("filterRule"),
            platform=filter_platform,
            definition_available=bool(target.get("filterRule")),
        )
    return AssignmentTarget(
        target_type=target_type,
        target_id=target.get("groupId") or target.get("id"),
        display_name=target.get("displayName"),
        scope=scope,
        filter=filter_model,
    )


class PolicyParser:
    """Parse validated sources into typed policies while retaining unknown content diagnostics."""

    def __init__(self, limits: ProcessingLimits) -> None:
        self.limits = limits

    def parse(self, sources: list[ValidatedUpload]) -> ParserResult:
        policies: list[PolicyDocument] = []
        diagnostics: list[ParserDiagnostic] = []
        digest = hashlib.sha256()
        for source in sources:
            digest.update(source.filename.encode())
            digest.update((source.archive_member or "").encode())
            digest.update(source.content)
            parsed = self._decode(source)
            _json_depth(
                parsed,
                self.limits.json_nesting_depth,
                self.limits.maximum_string_length,
            )
            candidates = self._policy_roots(parsed)
            for candidate_index, policy_raw in enumerate(candidates):
                if len(policies) >= self.limits.maximum_policies:
                    raise ValueError("maximum_policies_exceeded")
                policy, policy_diagnostics = self._parse_policy(policy_raw, source, candidate_index)
                policies.append(policy)
                diagnostics.extend(policy_diagnostics)
                if sum(len(item.settings) for item in policies) > self.limits.maximum_settings:
                    raise ValueError("maximum_settings_exceeded")
        if not policies:
            raise ValueError("no_policies_detected")
        return ParserResult(
            policies=policies,
            diagnostics=diagnostics,
            input_sha256=digest.hexdigest(),
            parser_version=PARSER_VERSION,
        )

    def _decode(self, source: ValidatedUpload) -> object:
        try:
            text = source.content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("unsupported_encoding") from exc
        if len(text) > self.limits.maximum_string_length * 100:
            raise ValueError("json_text_too_large")
        try:
            return strict_json_loads(text, max_nesting_depth=self.limits.json_nesting_depth)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed_json:{exc.lineno}:{exc.colno}") from exc

    @staticmethod
    def _policy_roots(parsed: object) -> list[dict[str, Any]]:
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if not isinstance(parsed, dict):
            return []
        for key in ("policies", "value", "items"):
            value = parsed.get(key)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
        return [parsed]

    def _parse_policy(
        self,
        raw: dict[str, Any],
        source: ValidatedUpload,
        index: int,
    ) -> tuple[PolicyDocument, list[ParserDiagnostic]]:
        source_name = source.archive_member or source.filename
        source_hash = hashlib.sha256(source.content).hexdigest()
        policy_id = str(
            raw.get("id") or raw.get("policyId") or uuid5(NAMESPACE_URL, f"{source_name}:{index}")
        )
        name = str(raw.get("name") or raw.get("displayName") or f"Unnamed policy {index + 1}")
        platform = _platform(raw.get("platform") or raw.get("platforms") or raw.get("technologies"))
        kind = _policy_kind(raw.get("policyKind") or raw.get("type") or raw.get("templateType"))
        scope = _scope(raw.get("scope") or raw.get("settingScope"))
        if scope is Scope.UNKNOWN and platform is not Platform.UNKNOWN:
            scope = Scope.DEVICE
        diagnostics: list[ParserDiagnostic] = []
        observations: list[SettingObservation] = []
        settings_root = raw.get("settings", raw.get("configurationSettings", []))
        for setting_index, (setting_raw, json_path) in enumerate(
            _setting_candidates(settings_root, "$.settings")
        ):
            raw_id = _first(setting_raw, _SETTING_ID_KEYS)
            identifier_known = isinstance(raw_id, str) and bool(raw_id.strip())
            if not identifier_known:
                raw_id = f"unidentified/{uuid5(NAMESPACE_URL, f'{source_name}:{json_path}')}"
            original_value = _extract_value(setting_raw)
            if (
                isinstance(original_value, str)
                and len(original_value) > self.limits.maximum_string_length
            ):
                raise ValueError("maximum_string_length_exceeded")
            normalized = normalize_setting_id(raw_id)
            canonical = canonical_setting_id(raw_id, platform, scope)
            diagnostic_items: list[ParserDiagnostic] = []
            if not identifier_known:
                diagnostic = ParserDiagnostic(
                    source_file=source_name,
                    policy=name,
                    json_path=json_path,
                    code="missing_setting_id",
                    severity=DiagnosticSeverity.WARNING,
                    reason="A setting-shaped value has no supported exact identifier.",
                    suggested_action="Export the canonical setting definition ID or add a documented parser mapping.",
                )
                diagnostics.append(diagnostic)
                diagnostic_items.append(diagnostic)
            if original_value is None:
                diagnostic = ParserDiagnostic(
                    source_file=source_name,
                    policy=name,
                    json_path=json_path,
                    code="unknown_value_shape",
                    severity=DiagnosticSeverity.WARNING,
                    reason="The parser found an identifier but no supported value representation.",
                    suggested_action="Inspect the technical JSON path and add a deterministic parser mapping.",
                )
                diagnostics.append(diagnostic)
                diagnostic_items.append(diagnostic)
            observations.append(
                SettingObservation(
                    observation_id=str(
                        uuid5(NAMESPACE_URL, f"{policy_id}:{json_path}:{setting_index}")
                    ),
                    original_setting_id=raw_id,
                    normalized_setting_id=normalized,
                    canonical_setting_id=canonical,
                    definition_id=setting_raw.get("settingDefinitionId")
                    or setting_raw.get("definitionId"),
                    choice_id=setting_raw.get("choiceId"),
                    value_definition_id=setting_raw.get("valueDefinitionId"),
                    original_value=original_value,
                    canonical_value=original_value,
                    display_value=json.dumps(original_value, ensure_ascii=False, sort_keys=True),
                    technical_json_path=json_path,
                    source_policy_id=policy_id,
                    source_policy_name=name,
                    source_file=source_name,
                    platform=platform,
                    scope=scope,
                    extraction_confidence=EvidenceConfidence.EXACT
                    if identifier_known
                    else EvidenceConfidence.UNKNOWN,
                    parser_name="generic_intune_json",
                    parser_version=PARSER_VERSION,
                    diagnostics=diagnostic_items,
                )
            )
        if not observations:
            diagnostics.append(
                ParserDiagnostic(
                    source_file=source_name,
                    policy=name,
                    json_path="$.settings",
                    code="no_supported_settings_found",
                    severity=DiagnosticSeverity.WARNING,
                    reason="No supported setting instances were detected; the policy remains visible.",
                    suggested_action="Use Expert Mode to inspect the export shape.",
                )
            )
        assignments_raw = raw.get("assignments", [])
        assignments = (
            [
                _assignment_target(item, platform)
                for item in assignments_raw
                if isinstance(item, dict)
            ]
            if isinstance(assignments_raw, list)
            else []
        )
        uploaded_source = UploadedSource(
            source_id=source_hash,
            filename=source.filename,
            content_type="application/json",
            size_bytes=len(source.content),
            sha256=source_hash,
            archive_member=source.archive_member,
        )
        return (
            PolicyDocument(
                policy_id=policy_id,
                name=name,
                description=str(raw.get("description")) if raw.get("description") else None,
                platform=platform,
                kind=kind,
                scope=scope,
                source=uploaded_source,
                settings=observations,
                assignments=assignments,
                diagnostics=diagnostics.copy(),
                is_synthetic=raw.get("isSynthetic") is True,
            ),
            diagnostics,
        )
