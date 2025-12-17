@echo off
cd /d "%~dp0"
setlocal

echo [MASTER] Starting ping client
start /b python Agent1.py
timeout /t 1 >nul

echo [MASTER] Starting pong client
start /b python Agent2.py

echo [MASTER] Both clients started.
echo.

:loop
timeout /t 5 >nul
goto loop