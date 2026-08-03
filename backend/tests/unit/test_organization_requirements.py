import json
from pathlib import Path

import pytest

from intune_auditor.organization.requirements import load_requirements, parse_requirements

ROOT = Path(__file__).resolve().parents[3]


def test_synthetic_organization_requirements_are_typed() -> None:
    requirements = load_requirements(ROOT / "organization" / "requirements.example.json")
    assert [item.requirement_id for item in requirements] == ["synthetic-pilot-required"]


def test_duplicate_organization_requirement_ids_are_rejected() -> None:
    source = json.loads(
        (ROOT / "organization" / "requirements.example.json").read_text(encoding="utf-8")
    )
    source["requirements"].append(source["requirements"][0])
    with pytest.raises(ValueError, match="duplicate_organization_requirement_id"):
        parse_requirements(json.dumps(source).encode())
