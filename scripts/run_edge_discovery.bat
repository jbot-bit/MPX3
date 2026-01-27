@echo off
REM ===================================================================
REM EDGE DISCOVERY - AUTO-RUNNING, AUTO-RESTARTING
REM ===================================================================

REM Change to the project directory (where this batch file lives)
cd /d "%~dp0"

echo.
echo ===================================================================
echo EDGE DISCOVERY ENGINE - STARTING
echo ===================================================================
echo.
echo Project directory: %CD%
echo.
echo This will run continuously and auto-restart if needed.
echo.
echo Results: edge_discovery_results/
echo Log: edge_discovery_live.log
echo.
echo Press Ctrl+C to stop.
echo.
echo ===================================================================
echo.

:loop
echo [%TIME%] Starting edge discovery iteration...
python edge_discovery_live.py
if errorlevel 1 (
    echo.
    echo [%TIME%] [ERROR] Discovery crashed. Restarting in 5 seconds...
    timeout /t 5 /nobreak
    goto loop
)
echo.
echo [%TIME%] Discovery completed normally.
pause
