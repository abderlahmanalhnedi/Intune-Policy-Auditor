$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectDir "backend"
$FrontendDir = Join-Path $ProjectDir "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

function Fail-Bilingual([string]$Message) { Write-Error $Message; exit 1 }
function Assert-NativeSuccess([string]$Message) { if ($LASTEXITCODE -ne 0) { Fail-Bilingual $Message } }

$PythonExecutable = $null
$PythonArgs = @()
if (Test-Path $VenvPython) {
  $PythonExecutable = $VenvPython
} else {
  $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($PythonLauncher) {
    foreach ($Selector in @("-3.13", "-3.12", "-3.11")) {
      & $PythonLauncher.Source $Selector -c "import sys; raise SystemExit(sys.version_info < (3, 11))" 2>$null
      if ($LASTEXITCODE -eq 0) {
        $PythonExecutable = $PythonLauncher.Source
        $PythonArgs = @($Selector)
        break
      }
    }
  }
  if (-not $PythonExecutable) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) { $PythonExecutable = $PythonCommand.Source }
  }
}
if (-not $PythonExecutable) { Fail-Bilingual "Python 3.11 oder neuer wird benötigt. / Python 3.11 or newer is required." }
& $PythonExecutable @PythonArgs -c "import sys; raise SystemExit(sys.version_info < (3, 11))"
if ($LASTEXITCODE -ne 0) { Fail-Bilingual "Python 3.11 oder neuer wird benötigt. / Python 3.11 or newer is required." }

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail-Bilingual "Node.js fehlt. / Node.js is missing." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail-Bilingual "npm fehlt. / npm is missing." }
node -e 'const a=Number(process.versions.node.split(".")[0]);if(a!==24)process.exit(1)'
if ($LASTEXITCODE -ne 0) { Fail-Bilingual "Node.js 24 LTS wird benötigt. / Node.js 24 LTS is required." }

if (-not (Test-Path $VenvPython)) {
  & $PythonExecutable @PythonArgs -m venv (Join-Path $BackendDir ".venv")
  Assert-NativeSuccess "Python-Umgebung konnte nicht erstellt werden. / Python environment creation failed."
}
& $VenvPython -m pip install --upgrade pip
Assert-NativeSuccess "pip konnte nicht aktualisiert werden. / pip upgrade failed."
& $VenvPython -m pip install -e "$BackendDir[dev]"
Assert-NativeSuccess "Backend-Abhängigkeiten konnten nicht installiert werden. / Backend dependency installation failed."
if (-not (Test-Path (Join-Path $FrontendDir "package-lock.json"))) { Fail-Bilingual "package-lock.json fehlt. / package-lock.json is missing." }
Push-Location $FrontendDir
try {
  npm ci
  Assert-NativeSuccess "Frontend-Abhängigkeiten konnten nicht installiert werden. / Frontend dependency installation failed."
} finally { Pop-Location }
if (-not (Test-Path (Join-Path $BackendDir ".env"))) { Copy-Item (Join-Path $BackendDir ".env.example") (Join-Path $BackendDir ".env") }
Write-Host "Einrichtung abgeschlossen. / Setup complete."
