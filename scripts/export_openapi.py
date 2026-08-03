"""Export the FastAPI schema used to generate frontend contracts."""

from __future__ import annotations

import json
from pathlib import Path

from intune_auditor.main import create_app


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "backend" / "openapi.json"
    target.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
