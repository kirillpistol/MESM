@echo off
setlocal
cd /d "%~dp0"

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

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto ERROR

    call ".venv\Scripts\activate.bat"

    echo [2/4] Updating pip...
    python -m pip install --upgrade pip
    if errorlevel 1 goto ERROR

    echo [3/4] Installing MESM dependencies...
    python -m pip install -e ".[dashboard,dev,yaml,research,changepoint,excel]"
    if errorlevel 1 goto ERROR
) else (
    echo [1/4] Virtual environment already exists.
    call ".venv\Scripts\activate.bat"
    echo [2/4] Using installed dependencies.
    echo [3/4] Using current MESM build.
)

echo [4/4] Validating MESM data...
python scripts\build_fiscal_reference_panel.py
if errorlevel 1 goto ERROR

python scripts\validate_project.py
if errorlevel 1 goto ERROR

echo Checking dashboard dependencies and cash calculations...
python scripts\smoke_dashboard.py
if errorlevel 1 goto ERROR

echo.
echo MESM is ready. Opening local interface...
echo Browser URL: http://127.0.0.1:8501
echo To stop MESM, return to this window and press Ctrl+C.
echo.

python -m streamlit run dashboard\app.py --server.address 127.0.0.1
goto END

:NO_PYTHON
echo.
echo Python was not found.
echo Install Python 3.11 or newer and enable Add Python to PATH.
pause
goto END

:OLD_PYTHON
echo.
echo Python 3.11 or newer is required.
%PY_CMD% --version
pause
goto END

:ERROR
echo.
echo MESM failed to start.
echo Copy the last error lines from this window and send them to the chat.
pause

:END
endlocal
