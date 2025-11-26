@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

set "PYTHON=C:\Users\livio\AppData\Local\Programs\Python\Python313\python.exe"

for %%S in (S*.py) do (
    echo ----------------------------------------
    echo Starting %%S ...
    echo ----------------------------------------
    start "" /B "%PYTHON%" "%%S"
    timeout /t 1 >nul
)

for %%A in (AA*.py) do (
    echo ----------------------------------------
    echo Starting %%A ...
    echo ----------------------------------------
    start "" /B "%PYTHON%" "%%A"
    timeout /t 1 >nul
)

pause
