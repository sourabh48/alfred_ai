@echo off
cd /d "%~dp0"
if exist "dist\ALFRED\ALFRED Launcher.exe" (
  start "" "dist\ALFRED\ALFRED Launcher.exe" start --data-dir "%~dp0." %*
  exit /b 0
)
if exist "dist\ALFRED\ALFRED.exe" (
  "dist\ALFRED\ALFRED.exe" start --data-dir "%~dp0." %*
  if errorlevel 1 pause
  exit /b
)
if not exist ".venv\Scripts\python.exe" (
  echo ALFRED's Python environment is missing. Install ALFRED-Setup.exe instead.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" alfred_native.py start %*
if errorlevel 1 pause
