#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if ! command -v node >/dev/null 2>&1 && [[ -x "$PROJECT_DIR/.tools/node/bin/node" ]]; then
  export PATH="$PROJECT_DIR/.tools/node/bin:$PATH"
fi

[[ -d "$PROJECT_DIR/frontend/node_modules" ]] || { printf '%s\n' "Setup fehlt / Setup missing: scripts/setup.sh" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { printf '%s\n' "npm fehlt / npm is missing: scripts/setup.sh" >&2; exit 1; }
(cd "$PROJECT_DIR/frontend" && npm run build)
printf '%s\n' "Produktions-Build erstellt. / Production build created."
