@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ALFRED's Python environment is missing. Install ALFRED-Setup.exe instead.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" alfred_native.py start %*
if errorlevel 1 pause
