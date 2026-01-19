@echo off
setlocal
cd /d "%~dp0"

echo [1/2] Start frpc...
start "FRPC" /D "%~dp0" "%~dp0frpc.exe" -c "%~dp0frpc.ini"

echo [2/2] Start ground_recv...
start "GROUND_RECV" /D "%~dp0" "E:\anaconda3\python.exe" "%~dp0ground_recv.py"

echo Done. Two windows should be running now.
pause
