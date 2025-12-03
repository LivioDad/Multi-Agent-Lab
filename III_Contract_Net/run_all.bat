@echo off
REM === Launch many machines + supervisor ===
setlocal EnableDelayedExpansion

set PROJ1=%~dp0..
set PROJ=%~dp0
set VENV=%PROJ1%\.venv\Scripts\activate.bat

if not exist "%VENV%" (
  echo Virtual env not found. Run setup_env.bat first.
  pause
  exit /b 1
)

REM --- Parameters ---
set BROKER=localhost
set PORT=1883
REM Capabilities format: job:seconds
set JOBS=cut,drill,paint,cut,drill,paint,cut,drill,paint,cut,drill,paint,cut,drill,paint
set DEADLINE=0.8
set WAIT_DONE=--wait-done

REM --- Machines (ID = capabilities) ---
set M01_ID=M01 & set M01_CAPS=cut:1.8,drill:4.5,paint:1.2
set M02_ID=M02 & set M02_CAPS=cut:2.4,drill:2.1,paint:2.0
set M03_ID=M03 & set M03_CAPS=cut:3.0,drill:1.9,paint:2.6
set M04_ID=M04 & set M04_CAPS=cut:2.2,drill:3.8,paint:1.4
set M05_ID=M05 & set M05_CAPS=cut:1.9,drill:4.2,paint:1.8
set M06_ID=M06 & set M06_CAPS=cut:2.8,drill:2.5,paint:1.6
set M07_ID=M07 & set M07_CAPS=cut:3.6,drill:1.7,paint:2.2
set M08_ID=M08 & set M08_CAPS=cut:2.1,drill:3.1,paint:1.3
set M09_ID=M09 & set M09_CAPS=cut:2.7,drill:2.3,paint:1.9
set M10_ID=M10 & set M10_CAPS=cut:3.2,drill:2.0,paint:2.1
set M11_ID=M11 & set M11_CAPS=cut:2.5,drill:2.7,paint:1.5
set M12_ID=M12 & set M12_CAPS=cut:1.7,drill:3.9,paint:1.7

REM --- Launch machines (12 windows) ---
start "Machine %M01_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M01_ID% --caps "%M01_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M02_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M02_ID% --caps "%M02_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M03_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M03_ID% --caps "%M03_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M04_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M04_ID% --caps "%M04_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M05_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M05_ID% --caps "%M05_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M06_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M06_ID% --caps "%M06_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M07_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M07_ID% --caps "%M07_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M08_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M08_ID% --caps "%M08_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M09_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M09_ID% --caps "%M09_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M10_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M10_ID% --caps "%M10_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M11_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M11_ID% --caps "%M11_CAPS%" --broker %BROKER% --port %PORT%
start "Machine %M12_ID%" cmd /k call "%VENV%" ^&^& python "%PROJ%\machine.py" --machine-id %M12_ID% --caps "%M12_CAPS%" --broker %BROKER% --port %PORT%

REM --- Supervisor (use supervisor.py or swap to supervisor_opt.py) ---
start "Supervisor" cmd /k call "%VENV%" ^&^& python "%PROJ%\supervisor.py" --jobs "%JOBS%" --deadline %DEADLINE% %WAIT_DONE% --broker %BROKER% --port %PORT%

echo Launched 12 machines + 1 supervisor.
pause
