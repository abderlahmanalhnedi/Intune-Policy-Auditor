#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_DIR/backend/.venv/bin/python"
URL="http://127.0.0.1:8765"

[[ -x "$PYTHON" ]] || { printf '%s\n' "Setup fehlt / Setup missing: scripts/setup.sh" >&2; exit 1; }
[[ -f "$PROJECT_DIR/frontend/dist/index.html" ]] || { printf '%s\n' "Build fehlt / Build missing: scripts/build.sh" >&2; exit 1; }

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(cd "$PROJECT_DIR/backend" && "$PYTHON" -m uvicorn intune_auditor.main:app --host 127.0.0.1 --port 8765) &
SERVER_PID=$!

READY=0
for _ in {1..60}; do
  if curl --silent --fail "$URL/api/v1/health" >/dev/null 2>&1; then READY=1; break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then break; fi
  sleep 0.25
done
[[ "$READY" -eq 1 ]] || { printf '%s\n' "Serverstart fehlgeschlagen / Server failed to start" >&2; exit 1; }

printf 'Intune Policy Auditor: %s\n' "$URL"
case "$(uname -s)" in
  Darwin) open "$URL" >/dev/null 2>&1 || true ;;
  Linux) command -v xdg-open >/dev/null 2>&1 && xdg-open "$URL" >/dev/null 2>&1 || true ;;
esac
wait "$SERVER_PID"

