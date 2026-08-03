"""Strict JSON decoding that rejects ambiguous and non-standard values."""

from __future__ import annotations

import codecs
import json
from typing import Any, cast

_DEFAULT_MAX_NESTING_DEPTH = 500


def decode_supported_json_text(content: bytes | bytearray) -> str:
    """Decode JSON bytes from the explicitly supported, unambiguous encodings."""
    raw = bytes(content)
    if raw.startswith(codecs.BOM_UTF32_LE) or raw.startswith(codecs.BOM_UTF32_BE):
        raise ValueError("unsupported_encoding")
    if raw.startswith(codecs.BOM_UTF8):
        payload = raw[len(codecs.BOM_UTF8) :]
        encoding = "utf-8"
    elif raw.startswith(codecs.BOM_UTF16_LE):
        payload = raw[len(codecs.BOM_UTF16_LE) :]
        encoding = "utf-16-le"
    elif raw.startswith(codecs.BOM_UTF16_BE):
        payload = raw[len(codecs.BOM_UTF16_BE) :]
        encoding = "utf-16-be"
    else:
        payload = raw
        encoding = "utf-8"
    try:
        decoded = payload.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("unsupported_encoding") from exc
    if "\x00" in decoded:
        raise ValueError("unsupported_encoding")
    return decoded


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non_finite_json_number:{value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _validate_nesting_depth(content: str, maximum: int) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in content:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > maximum:
                raise ValueError("json_nesting_depth_exceeded")
        elif character in "]}":
            depth = max(depth - 1, 0)


def strict_json_loads(
    content: str | bytes | bytearray,
    *,
    max_nesting_depth: int = _DEFAULT_MAX_NESTING_DEPTH,
) -> object:
    """Decode standards-compliant JSON without silent duplicate-key replacement."""
    text = content if isinstance(content, str) else decode_supported_json_text(content)
    _validate_nesting_depth(text, max_nesting_depth)
    try:
        return cast(
            object,
            json.loads(
                text,
                parse_constant=_reject_non_finite,
                object_pairs_hook=_reject_duplicate_keys,
            ),
        )
    except RecursionError as exc:
        raise ValueError("json_nesting_depth_exceeded") from exc
