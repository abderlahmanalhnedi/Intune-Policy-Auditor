"""Deterministic setting identifier normalization."""

from __future__ import annotations

import re

from intune_auditor.domain.enums import Platform, Scope

_MULTI_SEPARATOR = re.compile(r"[\\/]+")
_SAFE_PART = re.compile(r"[^a-z0-9._-]+")


def normalize_setting_id(identifier: str) -> str:
    """Normalize syntax only; never infer meaning or merge display-name lookalikes."""

    value = identifier.strip().replace("\\", "/")
    if value.lower().startswith("./device/vendor/msft/policy/config/"):
        value = value[len("./Device/Vendor/MSFT/Policy/Config/") :]
    value = _MULTI_SEPARATOR.sub("/", value).strip("/").lower()
    return "/".join(_SAFE_PART.sub("_", part).strip("_") for part in value.split("/"))


def canonical_setting_id(
    identifier: str,
    platform: Platform,
    scope: Scope,
    namespace: str = "intune",
) -> str:
    normalized = normalize_setting_id(identifier)
    return f"{platform.value}:{namespace.lower()}:{scope.value}:{normalized}"
