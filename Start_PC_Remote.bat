@echo off
cd /d "%~dp0"
echo Starting PC Web Remote...
python media_control_server.py
pause
