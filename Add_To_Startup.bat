@echo off
set "SCRIPT_PATH=%~dp0Run_Hidden.vbs"
set "REG_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "APP_NAME=PCWebRemote"

echo Adding "%APP_NAME%" to startup...
reg add "%REG_KEY%" /v "%APP_NAME%" /t REG_SZ /d "\"%SCRIPT_PATH%\"" /f

if %ERRORLEVEL% equ 0 (
    echo Successfully added to startup! The PC Web Remote will launch silently when Windows starts.
) else (
    echo Failed to add to startup. Please try running this script as Administrator.
)
pause
