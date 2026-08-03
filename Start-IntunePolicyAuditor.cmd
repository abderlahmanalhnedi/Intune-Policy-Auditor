@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-IntunePolicyAuditor.ps1"
exit /b %ERRORLEVEL%

