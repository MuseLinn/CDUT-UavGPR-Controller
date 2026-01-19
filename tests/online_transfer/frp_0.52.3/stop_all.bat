@echo off
taskkill /F /IM frpc.exe >nul 2>nul
taskkill /F /IM python.exe >nul 2>nul
echo Stopped frpc + python (if they were running).
pause
