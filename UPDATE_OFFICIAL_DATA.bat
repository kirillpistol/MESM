@echo off
setlocal
cd /d "%~dp0"
title MESM - Official data update

if not exist ".venv\Scripts\python.exe" (
    echo MESM virtual environment is missing.
    echo Run START_MESM.bat once first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo [1/4] Downloading official Surgut budget source files...
python scripts\fetch_official_sources.py surgut_budget_adopted_2025_2027
if errorlevel 1 goto ERROR

echo [2/4] Rebuilding processed budget datasets...
python scripts\build_surgut_official_budget.py
if errorlevel 1 goto ERROR

echo [3/4] Rebuilding Fiscal Reference Panel...
python scripts\build_fiscal_reference_panel.py
if errorlevel 1 goto ERROR

echo [4/4] Validating project...
python scripts\validate_project.py
if errorlevel 1 goto ERROR

echo.
echo Official data update completed.
echo Check data\manifest\source_manifest.csv for URLs and SHA-256 hashes.
pause
exit /b 0

:ERROR
echo.
echo Official data update failed. Existing processed snapshots were not deleted.
pause
exit /b 1
