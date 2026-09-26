@echo off
cd /d "%~dp0"
if exist "dist\ALFRED\ALFRED Launcher.exe" (
  start "" "dist\ALFRED\ALFRED Launcher.exe" stop --data-dir "%~dp0." %*
  exit /b 0
)
if exist "dist\ALFRED\ALFRED.exe" (
  "dist\ALFRED\ALFRED.exe" stop --data-dir "%~dp0." %*
  if errorlevel 1 pause
  exit /b
)
".venv\Scripts\python.exe" alfred_native.py stop %*
if errorlevel 1 pause
