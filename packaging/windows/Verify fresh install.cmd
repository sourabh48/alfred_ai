@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify_windows_acceptance.ps1" -Executable "%LOCALAPPDATA%\Programs\ALFRED\ALFRED.exe" -Phase Fresh
set "proof_exit=%ERRORLEVEL%"
pause
exit /b %proof_exit%
