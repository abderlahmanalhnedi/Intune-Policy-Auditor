#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

if ! command -v node >/dev/null 2>&1 && [[ -x "$PROJECT_DIR/.tools/node/bin/node" ]]; then
  export PATH="$PROJECT_DIR/.tools/node/bin:$PATH"
fi

say() { printf '%s\n' "$1"; }
fail() { say "Fehler / Error: $1" >&2; exit 1; }

PYTHON_BIN="${IPA_PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" && -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
elif [[ -z "$PYTHON_BIN" && -x "$PROJECT_DIR/.tools/python/cpython-3.13-macos-aarch64-none/bin/python3" ]]; then
  PYTHON_BIN="$PROJECT_DIR/.tools/python/cpython-3.13-macos-aarch64-none/bin/python3"
fi
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>/dev/null; then
        PYTHON_BIN="$candidate"
        break
      fi
    fi
  done
fi
[[ -n "$PYTHON_BIN" ]] || fail "Python 3.11 oder neuer wird benötigt. / Python 3.11 or newer is required."

command -v node >/dev/null 2>&1 || fail "Node.js fehlt (aktive LTS-Version erforderlich). / Node.js is missing (active LTS required)."
command -v npm >/dev/null 2>&1 || fail "npm fehlt. / npm is missing."
node -e 'const major=Number(process.versions.node.split(".")[0]); if (major !== 24) process.exit(1)' \
  || fail "Node.js 24 LTS wird benötigt. / Node.js 24 LTS is required."

if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  say "Erstelle isolierte Python-Umgebung / Creating isolated Python environment"
  "$PYTHON_BIN" -m venv "$BACKEND_DIR/.venv"
fi

VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
if "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -e "$BACKEND_DIR[dev]"
else
  UV_BIN="${IPA_UV_BIN:-}"
  if [[ -z "$UV_BIN" ]] && command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
  elif [[ -z "$UV_BIN" && -x "$PROJECT_DIR/.tools/bin/uv" ]]; then
    UV_BIN="$PROJECT_DIR/.tools/bin/uv"
  fi
  [[ -n "$UV_BIN" && -x "$UV_BIN" ]] \
    || fail "Diese Python-Umgebung enthält kein pip; uv wird benötigt. / This Python environment has no pip; uv is required."
  "$UV_BIN" pip install --python "$VENV_PYTHON" -e "$BACKEND_DIR[dev]"
fi

if [[ ! -f "$FRONTEND_DIR/package-lock.json" ]]; then
  fail "package-lock.json fehlt. / package-lock.json is missing."
fi
(cd "$FRONTEND_DIR" && npm ci)

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  say "backend/.env erstellt / backend/.env created"
fi

say "Einrichtung abgeschlossen. / Setup complete."
