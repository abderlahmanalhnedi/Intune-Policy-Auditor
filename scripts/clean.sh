#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

rm -rf "$PROJECT_DIR/frontend/dist" "$PROJECT_DIR/frontend/playwright-report" "$PROJECT_DIR/frontend/test-results"
find "$PROJECT_DIR/backend" -type d -name __pycache__ -prune -exec rm -rf {} +
rm -rf "$PROJECT_DIR/backend/.pytest_cache" "$PROJECT_DIR/backend/.mypy_cache" "$PROJECT_DIR/backend/.ruff_cache" "$PROJECT_DIR/backend/htmlcov"
rm -f "$PROJECT_DIR/backend/.coverage"
printf '%s\n' "Generierte Artefakte entfernt. / Generated artifacts removed."

