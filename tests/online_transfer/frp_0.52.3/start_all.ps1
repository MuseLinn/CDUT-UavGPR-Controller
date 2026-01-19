# start_all.ps1  —— 一键启动 frpc + ground_recv（兼容路径含空格）

$base = Split-Path -Parent $MyInvocation.MyCommand.Path

$frpcExe = Join-Path $base "frpc.exe"
$frpcIni = Join-Path $base "frpc.ini"
$pyExe   = "E:\anaconda3\python.exe"
$recvPy  = Join-Path $base "ground_recv.py"

# 启动 frpc（新窗口）
Start-Process -FilePath "powershell.exe" `
  -WorkingDirectory $base `
  -ArgumentList @("-NoExit","-Command", "`"$frpcExe`" -c `"$frpcIni`"")

# 启动 ground_recv（新窗口）
Start-Process -FilePath "powershell.exe" `
  -WorkingDirectory $base `
  -ArgumentList @("-NoExit","-Command", "`"$pyExe`" `"$recvPy`"")

Write-Host "Started frpc + ground_recv."
