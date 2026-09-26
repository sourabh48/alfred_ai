@echo off
if not exist "%~dp0ALFRED Launcher.exe" (
  echo ALFRED Launcher.exe is missing. Extract the complete ZIP again.
  pause
  exit /b 1
)
start "" "%~dp0ALFRED Launcher.exe" stop %*
