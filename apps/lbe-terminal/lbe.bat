@echo off
set "LBE_ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%LBE_ROOT%\launch-lbe.ps1" %*
exit /b %ERRORLEVEL%
