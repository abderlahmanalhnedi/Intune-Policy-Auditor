"""Spreadsheet formula-injection protection."""

from __future__ import annotations


def safe_csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    stripped = text.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text
