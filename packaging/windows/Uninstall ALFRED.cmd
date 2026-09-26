@echo off
if not exist "%~dp0unins000.exe" (
  echo ALFRED's uninstaller is missing. Reinstall ALFRED in this folder and try again.
  pause
  exit /b 1
)
"%~dp0unins000.exe" %*
exit /b %ERRORLEVEL%
