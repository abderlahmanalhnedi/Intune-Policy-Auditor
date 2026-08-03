import json

import pytest

from intune_auditor.domain.enums import EvidenceConfidence, Platform
from intune_auditor.domain.models import ParserResult
from intune_auditor.parsing.service import PolicyParser
from intune_auditor.security.limits import ProcessingLimits
from intune_auditor.security.uploads import ValidatedUpload


def _parse(document: object, limits: ProcessingLimits | None = None) -> ParserResult:
    return PolicyParser(limits or ProcessingLimits()).parse(
        [ValidatedUpload(filename="policy.json", content=json.dumps(document).encode())]
    )


def test_mixed_identified_and_unidentified_settings_remain_visible() -> None:
    result = _parse(
        {
            "id": "policy-a",
            "name": "Mixed policy",
            "platform": "windows",
            "scope": "device",
            "settings": [
                {"settingDefinitionId": "synthetic/known", "value": True},
                {"displayName": "Unidentified export value", "value": "retained"},
            ],
        }
    )
    settings = result.policies[0].settings
    assert len(settings) == 2
    assert settings[1].original_setting_id.startswith("unidentified/")
    assert settings[1].canonical_value == "retained"
    assert settings[1].extraction_confidence is EvidenceConfidence.UNKNOWN
    assert settings[1].diagnostics[0].code == "missing_setting_id"


def test_collection_value_wrapper_is_not_mistaken_for_an_unidentified_setting() -> None:
    result = _parse(
        {
            "id": "policy-a",
            "platform": "windows",
            "scope": "device",
            "settings": {
                "value": [
                    {"settingDefinitionId": "synthetic/one", "value": True},
                    {"settingDefinitionId": "synthetic/two", "value": False},
                ]
            },
        }
    )
    assert [item.original_setting_id for item in result.policies[0].settings] == [
        "synthetic/one",
        "synthetic/two",
    ]


def test_string_limit_applies_recursively() -> None:
    with pytest.raises(ValueError, match="maximum_string_length_exceeded"):
        _parse(
            {
                "id": "policy-a",
                "platform": "windows",
                "scope": "device",
                "settings": [
                    {"settingDefinitionId": "synthetic/known", "value": {"nested": "x" * 101}}
                ],
            },
            ProcessingLimits(maximum_string_length=100),
        )


@pytest.mark.parametrize(
    ("raw_platform", "expected"),
    [
        ("windows10AndLater", Platform.WINDOWS),
        ("macOS", Platform.MACOS),
        ("not-windows", Platform.UNKNOWN),
        (["windows", "macOS"], Platform.UNKNOWN),
    ],
)
def test_platform_mapping_requires_an_explicit_unambiguous_value(
    raw_platform: object, expected: Platform
) -> None:
    result = _parse(
        {
            "id": "platform-policy",
            "platform": raw_platform,
            "scope": "device",
            "settings": [{"settingDefinitionId": "synthetic/known", "value": True}],
        }
    )
    assert result.policies[0].platform is expected
