@echo off
setlocal

echo [MASTER] Starting ping client...
start /b python Script1v2.py
timeout /t 1 >nul

echo [MASTER] Starting pong client...
start /b python Script2v2.py

echo [MASTER] Both clients started. Press Ctrl+C to stop.
echo.

:loop
timeout /t 5 >nul
goto loop
