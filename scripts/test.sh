#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_DIR/backend/.venv/bin/python"

if ! command -v node >/dev/null 2>&1 && [[ -x "$PROJECT_DIR/.tools/node/bin/node" ]]; then
  export PATH="$PROJECT_DIR/.tools/node/bin:$PATH"
fi

[[ -x "$PYTHON" ]] || { printf '%s\n' "Setup fehlt / Setup missing: scripts/setup.sh" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { printf '%s\n' "npm fehlt / npm is missing: scripts/setup.sh" >&2; exit 1; }
(cd "$PROJECT_DIR/backend" && "$PYTHON" -m compileall -q src)
(cd "$PROJECT_DIR/backend" && "$PYTHON" -m ruff check .)
(cd "$PROJECT_DIR/backend" && "$PYTHON" -m mypy src)
(cd "$PROJECT_DIR/backend" && "$PYTHON" -m bandit -q -r src)
(cd "$PROJECT_DIR/backend" && "$PYTHON" -m pytest -q)
(cd "$PROJECT_DIR/frontend" && npm run lint)
(cd "$PROJECT_DIR/frontend" && npm run typecheck)
(cd "$PROJECT_DIR/frontend" && npm run test -- --run)
(cd "$PROJECT_DIR/frontend" && npm run build)
