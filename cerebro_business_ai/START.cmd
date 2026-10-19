@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0portable\cerebro.ps1" -Action Start %*
if errorlevel 1 (echo. & echo Cerebro could not start. & pause & exit /b 1)
