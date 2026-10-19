@echo off
rem Starts the control center and the project's front end (gateway, facade, dashboard), then opens the browser.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_platform.ps1" %*
if errorlevel 1 (echo. & echo The platform could not start. Read the message above. & pause & exit /b 1)
