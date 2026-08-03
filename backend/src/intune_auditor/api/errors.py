"""RFC 7807-compatible API exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProblemError(Exception):
    status: int
    title: str
    detail: str
    error_type: str = "about:blank"
    extensions: dict[str, Any] = field(default_factory=dict)
