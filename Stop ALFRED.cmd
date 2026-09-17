@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" alfred_native.py stop %*
if errorlevel 1 pause
