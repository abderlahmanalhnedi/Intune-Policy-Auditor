$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectDir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Setup fehlt / Setup missing: scripts/setup.ps1" }
function Invoke-Checked([scriptblock]$Command) {
  & $Command
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Push-Location (Join-Path $ProjectDir "backend")
try {
  Invoke-Checked { & $Python -m compileall -q src }
  Invoke-Checked { & $Python -m ruff check . }
  Invoke-Checked { & $Python -m mypy src }
  Invoke-Checked { & $Python -m bandit -q -r src }
  Invoke-Checked { & $Python -m pytest -q }
} finally { Pop-Location }
Push-Location (Join-Path $ProjectDir "frontend")
try {
  Invoke-Checked { npm run lint }
  Invoke-Checked { npm run typecheck }
  Invoke-Checked { npm run test -- --run }
  Invoke-Checked { npm run build }
} finally { Pop-Location }
