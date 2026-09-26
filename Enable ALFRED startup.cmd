@echo off
setlocal
if not exist "%~dp0scripts\set_windows_autostart.ps1" (
  echo ALFRED's startup configuration script is missing.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_windows_autostart.ps1" -Action Enable
if errorlevel 1 (
  echo.
  echo Automatic startup could not be enabled. See the message above.
  pause
  exit /b 1
)
echo.
echo You can close this window. ALFRED will start after your next Windows sign-in.
pause
