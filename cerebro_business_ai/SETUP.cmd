@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0portable\cerebro.ps1" -Action Setup %*
if errorlevel 1 (echo. & echo Setup did not finish. Read the error above. & pause & exit /b 1)
echo.
echo Setup finished. Use START.cmd next time.
pause
