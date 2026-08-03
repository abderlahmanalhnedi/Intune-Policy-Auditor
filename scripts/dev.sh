#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_DIR/backend/.venv/bin/python"

if ! command -v node >/dev/null 2>&1 && [[ -x "$PROJECT_DIR/.tools/node/bin/node" ]]; then
  export PATH="$PROJECT_DIR/.tools/node/bin:$PATH"
fi

[[ -x "$PYTHON" ]] || { printf '%s\n' "Setup fehlt / Setup missing: scripts/setup.sh" >&2; exit 1; }
[[ -d "$PROJECT_DIR/frontend/node_modules" ]] || { printf '%s\n' "Frontend-Abhängigkeiten fehlen / Frontend dependencies missing" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { printf '%s\n' "npm fehlt / npm is missing: scripts/setup.sh" >&2; exit 1; }

cleanup() {
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$PROJECT_DIR/backend" && "$PYTHON" -m uvicorn intune_auditor.main:app --host 127.0.0.1 --port 8765 --reload) &
BACKEND_PID=$!
(cd "$PROJECT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!
wait -n "$BACKEND_PID" "$FRONTEND_PID"
