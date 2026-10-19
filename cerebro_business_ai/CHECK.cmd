@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0portable\cerebro.ps1" -Action Check %*
pause
