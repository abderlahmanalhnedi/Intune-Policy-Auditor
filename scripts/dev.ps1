$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectDir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Setup fehlt / Setup missing: scripts/setup.ps1" }
$Backend = Start-Process -PassThru -NoNewWindow $Python -WorkingDirectory (Join-Path $ProjectDir "backend") -ArgumentList "-m", "uvicorn", "intune_auditor.main:app", "--host", "127.0.0.1", "--port", "8765", "--reload"
$Frontend = Start-Process -PassThru -NoNewWindow npm -WorkingDirectory (Join-Path $ProjectDir "frontend") -ArgumentList "run", "dev"
try { Wait-Process -Id $Backend.Id, $Frontend.Id } finally { Stop-Process -Id $Backend.Id, $Frontend.Id -ErrorAction SilentlyContinue }

