@echo off
cd /d "%~dp0"
echo Launching Capsule Console...
poetry run python tools/capsule_console/main.py
pause
