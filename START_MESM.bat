@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"

title MESM

echo.
echo ==========================================
echo   MESM - Municipal Economic Shock Monitor
echo ==========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 goto NO_PYTHON
    set "PY_CMD=python"
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto OLD_PYTHON

rem Stamp = hash of pyproject.toml. It is written only after a SUCCESSFUL install,
rem so an interrupted first run is repeated automatically on the next start.
set "WANT="
for /f "delims=" %%H in ('%PY_CMD% scripts\env_stamp.py') do set "WANT=%%H"
if not defined WANT goto ERROR

set "HAVE="
if exist ".venv\.mesm_stamp" set /p HAVE=<".venv\.mesm_stamp"

if exist ".venv\Scripts\python.exe" if "%HAVE%"=="%WANT%" goto READY_ENV

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto ERROR
) else (
    echo [1/4] Virtual environment found, refreshing dependencies...
)

call ".venv\Scripts\activate.bat"

echo [2/4] Updating pip...
python -m pip install --upgrade pip
if errorlevel 1 goto ERROR

echo [3/4] Installing MESM dependencies - the first run takes a few minutes...
python -m pip install -e ".[dashboard,dev,yaml,research,changepoint,excel]"
if errorlevel 1 goto ERROR

>".venv\.mesm_stamp" echo %WANT%
goto CHECKS

:READY_ENV
echo [1-3/4] Environment is up to date.
call ".venv\Scripts\activate.bat"

:CHECKS
echo [4/4] Validating MESM data...
python scripts\snapshot_manifest.py --verify

python scripts\build_fiscal_reference_panel.py
if errorlevel 1 goto ERROR

python scripts\validate_project.py
if errorlevel 1 goto ERROR

echo Checking dashboard dependencies and cash calculations...
python scripts\smoke_dashboard.py
if errorlevel 1 goto ERROR

set "MESM_PORT=8501"
for /f "delims=" %%P in ('python scripts\find_free_port.py') do set "MESM_PORT=%%P"

echo.
echo MESM is ready. Opening local interface...
echo Browser URL: http://127.0.0.1:%MESM_PORT%
echo To stop MESM, return to this window and press Ctrl+C.
echo.

python -m streamlit run dashboard\app.py --server.address 127.0.0.1 --server.port %MESM_PORT% --browser.gatherUsageStats false
goto END

:NO_PYTHON
echo.
echo Python was not found.
echo Install Python 3.11 or newer and enable Add Python to PATH.
if not defined MESM_NOPAUSE pause
goto END

:OLD_PYTHON
echo.
echo Python 3.11 or newer is required.
%PY_CMD% --version
if not defined MESM_NOPAUSE pause
goto END

:ERROR
echo.
echo MESM failed to start.
echo If the error is about pip or network, check the internet connection and run
echo START_MESM.bat again - the installation is repeated automatically.
echo Otherwise copy the last error lines from this window and send them to the chat.
if not defined MESM_NOPAUSE pause

:END
endlocal
