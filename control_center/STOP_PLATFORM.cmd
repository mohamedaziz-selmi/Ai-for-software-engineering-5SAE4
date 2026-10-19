@echo off
rem Stops every running module (the platform last) and the control center.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_platform.ps1" %*
