@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Сначала запустите START_MESM.bat для установки окружения.
 pause
 exit /b 1
)
if not defined MESM_API_TOKEN (
 for /f "delims=" %%T in ('.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"') do set "MESM_API_TOKEN=%%T"
)
echo Локальный токен для клиента ИИ: %MESM_API_TOKEN%
echo Не публикуйте токен. API доступен только на этом ПК.
set "PYTHONPATH=%CD%\src"
.venv\Scripts\python.exe -m mesm.access.server
pause
