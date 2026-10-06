@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Этот запуск заменён независимым узлом MESM L3. Ядро GENESIS не запускается.
call START_MESM_API.bat
