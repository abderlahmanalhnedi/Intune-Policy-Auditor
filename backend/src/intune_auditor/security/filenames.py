"""Portable filename validation for uploaded and generated content."""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath

_SAFE_GENERATED = re.compile(r"[^A-Za-z0-9._-]+")
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_upload_name(filename: str) -> str:
    normalized = unicodedata.normalize("NFC", filename).strip()
    if not normalized or len(normalized) > 255 or "\x00" in normalized:
        raise ValueError("malformed_filename")
    path = PurePosixPath(normalized.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("unsafe_filename_path")
    leaf = path.name
    if leaf.upper().split(".")[0] in _WINDOWS_RESERVED:
        raise ValueError("reserved_filename")
    return leaf


def safe_report_filename(name: str, suffix: str) -> str:
    base = _SAFE_GENERATED.sub("-", unicodedata.normalize("NFKC", name)).strip(".-_")
    if not base:
        base = "intune-policy-audit"
    return f"{base[:100]}.{suffix.lstrip('.').lower()}"
