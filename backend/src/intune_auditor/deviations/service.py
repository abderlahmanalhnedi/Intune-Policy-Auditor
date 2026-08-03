"""Load and match versioned deviations without hiding raw alignment."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from intune_auditor.domain.enums import AlignmentStatus
from intune_auditor.domain.models import AcceptedDeviation, JsonValue
from intune_auditor.security.json_safety import strict_json_loads


class DeviationFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    deviations: list[AcceptedDeviation]


def load_deviations(path: Path) -> list[AcceptedDeviation]:
    try:
        return parse_deviations(path.read_bytes())
    except OSError as exc:
        raise ValueError("invalid_deviation_file") from exc


def parse_deviations(content: bytes) -> list[AcceptedDeviation]:
    try:
        model = DeviationFile.model_validate(strict_json_loads(content))
    except (ValidationError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid_deviation_file") from exc
    if model.schema_version != "1.0":
        raise ValueError("unsupported_deviation_schema")
    identifiers = [item.deviation_id for item in model.deviations]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate_deviation_id")
    return model.deviations


def match_deviation(
    deviations: list[AcceptedDeviation],
    canonical_setting_id: str,
    policy_id: str,
    configured_value: JsonValue,
    on_date: date,
) -> tuple[AlignmentStatus | None, AcceptedDeviation | None]:
    for deviation in deviations:
        if deviation.canonical_setting_id != canonical_setting_id:
            continue
        if deviation.policy_id is not None and deviation.policy_id != policy_id:
            continue
        if deviation.accepted_value != configured_value:
            continue
        if deviation.valid_from <= on_date <= deviation.valid_until:
            return AlignmentStatus.ACCEPTED_DEVIATION, deviation
        if on_date > deviation.valid_until:
            return AlignmentStatus.EXPIRED_DEVIATION, deviation
    return None, None
