$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectDir "frontend"
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) { throw "Setup fehlt / Setup missing: scripts/setup.ps1" }
Push-Location $FrontendDir
try { npm run build; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } finally { Pop-Location }

