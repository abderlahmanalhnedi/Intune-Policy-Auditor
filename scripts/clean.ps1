$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Targets = @(
  (Join-Path $ProjectDir "frontend\dist"),
  (Join-Path $ProjectDir "frontend\playwright-report"),
  (Join-Path $ProjectDir "frontend\test-results"),
  (Join-Path $ProjectDir "backend\.pytest_cache"),
  (Join-Path $ProjectDir "backend\.mypy_cache"),
  (Join-Path $ProjectDir "backend\.ruff_cache"),
  (Join-Path $ProjectDir "backend\htmlcov")
)
foreach ($Target in $Targets) { if (Test-Path $Target) { Remove-Item -Recurse -Force $Target } }
Get-ChildItem (Join-Path $ProjectDir "backend") -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Remove-Item (Join-Path $ProjectDir "backend\.coverage") -Force -ErrorAction SilentlyContinue
Write-Host "Generierte Artefakte entfernt. / Generated artifacts removed."

