@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Сначала запустите START_MESM.bat для установки окружения.
 pause
 exit /b 1
)
.venv\Scripts\python.exe scripts\connect_genesis.py
pause
