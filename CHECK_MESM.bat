@echo off
setlocal
cd /d "%~dp0"

title MESM Check

if not exist ".venv\Scripts\python.exe" (
    echo Run START_MESM.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Rebuilding Fiscal Reference Panel...
python scripts\build_fiscal_reference_panel.py
if errorlevel 1 goto ERROR

echo Running tests...
python -m pytest
if errorlevel 1 goto ERROR

echo Validating project structure...
python scripts\validate_project.py
if errorlevel 1 goto ERROR

echo.
echo All MESM checks passed.
pause
exit /b 0

:ERROR
echo.
echo MESM check failed.
pause
exit /b 1
