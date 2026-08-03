$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectDir "backend\.venv\Scripts\python.exe"
$Index = Join-Path $ProjectDir "frontend\dist\index.html"
$Url = "http://127.0.0.1:8765"
if (-not (Test-Path $Python)) { throw "Setup fehlt / Setup missing: scripts/setup.ps1" }
if (-not (Test-Path $Index)) { throw "Build fehlt / Build missing: scripts/build.ps1" }
$Server = Start-Process -PassThru -NoNewWindow $Python -WorkingDirectory (Join-Path $ProjectDir "backend") -ArgumentList "-m", "uvicorn", "intune_auditor.main:app", "--host", "127.0.0.1", "--port", "8765"
try {
  $Ready = $false
  foreach ($Attempt in 1..60) {
    try { Invoke-WebRequest "$Url/api/v1/health" -UseBasicParsing | Out-Null; $Ready = $true; break } catch { Start-Sleep -Milliseconds 250 }
    if ($Server.HasExited) { break }
  }
  if (-not $Ready) { throw "Serverstart fehlgeschlagen / Server failed to start" }
  Write-Host "Intune Policy Auditor: $Url"
  Start-Process $Url
  Wait-Process -Id $Server.Id
} finally { Stop-Process -Id $Server.Id -ErrorAction SilentlyContinue }

