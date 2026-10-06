@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
title MESM - Official data update

if not exist ".venv\Scripts\python.exe" (
    echo MESM virtual environment is missing.
    echo Run START_MESM.bat once first.
    if not defined MESM_NOPAUSE pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

python scripts\safe_update_official_data.py
set "RC=%errorlevel%"

if "%RC%"=="0" goto OK
if "%RC%"=="2" goto OFFLINE
goto FAILED

:OK
echo.
echo Official data update completed.
echo Source URLs and SHA-256 of downloaded files: data\manifest\source_manifest.csv
echo Snapshot checksums were rewritten:           data\manifest\snapshot_manifest.csv
if not defined MESM_NOPAUSE pause
exit /b 0

:OFFLINE
echo.
echo The official site is not reachable (or its page changed).
echo NOTHING was changed: MESM keeps working on the saved data snapshot.
if not defined MESM_NOPAUSE pause
exit /b 2

:FAILED
echo.
echo The update was rejected by the checks. The previous data snapshot was restored.
if not defined MESM_NOPAUSE pause
exit /b 1
