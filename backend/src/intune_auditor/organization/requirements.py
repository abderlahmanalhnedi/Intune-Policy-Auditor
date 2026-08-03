"""Validate organization-requirement JSON without assigning security meaning."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from intune_auditor.domain.models import OrganizationRequirement
from intune_auditor.security.json_safety import strict_json_loads


class OrganizationRequirementFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    requirements: list[OrganizationRequirement]


def parse_requirements(content: bytes) -> list[OrganizationRequirement]:
    try:
        document = OrganizationRequirementFile.model_validate(strict_json_loads(content))
    except (ValidationError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid_organization_requirement_file") from exc
    if document.schema_version != "1.0":
        raise ValueError("unsupported_organization_requirement_schema")
    identifiers = [item.requirement_id for item in document.requirements]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate_organization_requirement_id")
    return document.requirements


def load_requirements(path: Path) -> list[OrganizationRequirement]:
    try:
        return parse_requirements(path.read_bytes())
    except OSError as exc:
        raise ValueError("invalid_organization_requirement_file") from exc
