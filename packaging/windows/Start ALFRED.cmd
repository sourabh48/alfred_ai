@echo off
if not exist "%~dp0ALFRED Launcher.exe" (
  echo Extract the complete ALFRED ZIP before launching it.
  pause
  exit /b 1
)
start "" "%~dp0ALFRED Launcher.exe" start %*
