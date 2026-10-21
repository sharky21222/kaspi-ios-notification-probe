@echo off
setlocal
title Kaspi Probe - Read-only Apple account check
echo This check does not install apps or create/revoke certificates.
echo Enter Apple credentials only at the hidden local prompts below.
"%~dp0kaspi-probe-signer.exe" check-account
set "result=%ERRORLEVEL%"
echo.
echo Finished with exit code %result%.
pause
exit /b %result%
