# frp_helper.py
# -*- coding: utf-8 -*-
"""
frp_helper.py
-------------
用途：一行函数 run_frpc() 完成：
1) 自动生成 frpc 配置（INI / TOML）
2) 启动 frpc 进程
3) 实时把 frpc 的日志输出到控制台（可选）
4) 返回句柄 FrpcHandle，支持 stop() 优雅退出

适用场景：
- 你在 PyCharm 里调试，主程序启动时先起 frpc，再起 UDP 收发逻辑
"""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal

# 每个 proxy 的字典结构：
# {
#   "name": "uav_ctrl_in",
#   "type": "udp",
#   "local_ip": "127.0.0.1",
#   "local_port": 10001,
#   "remote_port": 9100
# }
Proxy = Dict[str, object]
FrpFmt = Literal["ini", "toml"]


def _ensure_dir(p: str) -> None:
    """确保输出目录存在（用于写 frpc 配置文件）"""
    os.makedirs(p, exist_ok=True)


def _write_frpc_ini(path: str, server_addr: str, server_port: int, token: str, proxies: List[Proxy]) -> None:
    """
    生成传统 frpc.ini 配置（0.52.x 这类版本通用）
    """
    lines = [
        "[common]",
        f"server_addr = {server_addr}",
        f"server_port = {server_port}",
        f"token = {token}",
    ]
    for p in proxies:
        lines += [
            "",
            f"[{p['name']}]",
            f"type = {p['type']}",
            f"local_ip = {p.get('local_ip', '127.0.0.1')}",
            f"local_port = {int(p['local_port'])}",
            f"remote_port = {int(p['remote_port'])}",
        ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_frpc_toml(path: str, server_addr: str, server_port: int, token: str, proxies: List[Proxy]) -> None:
    """
    生成 frpc.toml 配置（新版本常用）
    注意：TOML 字段名在不同版本会有细微差异，如 serverAddr/serverPort/auth 等
    """
    lines = [
        f'serverAddr = "{server_addr}"',
        f"serverPort = {server_port}",
        "",
        "[auth]",
        'method = "token"',
        f'token = "{token}"',
    ]
    for p in proxies:
        lines += [
            "",
            "[[proxies]]",
            f'name = "{p["name"]}"',
            f'type = "{p["type"]}"',
            f'localIP = "{p.get("local_ip", "127.0.0.1")}"',
            f"localPort = {int(p['local_port'])}",
            f"remotePort = {int(p['remote_port'])}",
        ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


@dataclass
class FrpcHandle:
    """
    保存 frpc 运行状态的句柄对象
    - proc: frpc 进程
    - cfg_path: 生成的配置文件路径
    - log_thread: 读日志线程
    """
    proc: subprocess.Popen
    cfg_path: str
    log_thread: threading.Thread

    def stop(self) -> None:
        """
        尝试优雅停止 frpc：
        - Windows：发送 CTRL_BREAK_EVENT（需要 CREATE_NEW_PROCESS_GROUP 才能生效）
        - 其他系统：terminate
        如果失败则 kill
        """
        if self.proc.poll() is not None:
            return

        try:
            if os.name == "nt":
                # Windows 下给子进程发“类似 Ctrl+C”的信号
                self.proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore
                time.sleep(0.8)
            else:
                self.proc.terminate()
                time.sleep(0.8)
        except Exception:
            pass

        # 如果还没退出，强制 kill
        if self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass


def run_frpc(
    frpc_path: str,
    server_addr: str,
    server_port: int,
    token: str,
    proxies: List[Proxy],
    out_dir: str = "frp_run",
    fmt: FrpFmt = "ini",
    name: str = "frpc",
    print_logs: bool = True,
) -> FrpcHandle:
    """
    一键启动 frpc：
    1) 写配置文件
    2) 启动 frpc
    3) 后台线程实时打印 frpc 日志

    参数说明：
    - frpc_path: frpc.exe 的完整路径
    - proxies: 代理列表（至少一个）
    - out_dir: 输出目录（存放生成的配置文件）
    - fmt: ini/toml
    - name: 日志前缀 & 配置文件名（frp_run/frpc_uav.ini 这种）
    - print_logs: 是否打印 frpc 输出
    """
    if not proxies:
        raise ValueError("proxies 不能为空（至少配置一个 UDP 代理）")

    # 先检查 frpc.exe 路径是否有效，避免 WinError 5/2 等诡异问题
    if not os.path.exists(frpc_path):
        raise FileNotFoundError(f"找不到 frpc 可执行文件：{frpc_path}")
    if not os.path.isfile(frpc_path):
        raise PermissionError(f"frpc_path 不是文件（可能传成了文件夹路径）：{frpc_path}")

    _ensure_dir(out_dir)

    # 生成配置文件路径：例如 frp_run/frpc_uav.ini
    cfg_path = os.path.join(out_dir, f"{name}.{fmt}")

    # 写配置
    if fmt == "ini":
        _write_frpc_ini(cfg_path, server_addr, server_port, token, proxies)
    else:
        _write_frpc_toml(cfg_path, server_addr, server_port, token, proxies)

    # Windows：创建新的进程组，方便后续发 CTRL_BREAK_EVENT 做优雅退出
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore

    # 启动 frpc
    proc = subprocess.Popen(
        [frpc_path, "-c", cfg_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )

    # 后台读日志线程：避免阻塞主线程
    def _log_pump():
        if not proc.stdout:
            return
        for line in proc.stdout:
            if print_logs:
                # 中文前缀输出
                print(f"[{name}][frpc日志]", line.rstrip("\n"))

    t = threading.Thread(target=_log_pump, daemon=True)
    t.start()

    # 中文提示信息
    print(f"[成功] 已生成 frpc 配置文件：{cfg_path}")
    print(f"[成功] 已启动 frpc：{frpc_path} -c {cfg_path}")

    # 小增强：如果 frpc 启动后立即退出，提前提示（一般是 token/端口冲突/配置项不兼容）
    time.sleep(0.2)
    if proc.poll() is not None:
        code = proc.returncode
        print(f"[错误] frpc 启动后立即退出，返回码={code}。请检查 token/端口占用/配置格式/安全组。")

    return FrpcHandle(proc=proc, cfg_path=cfg_path, log_thread=t)












# # frp_helper.py
# # -*- coding: utf-8 -*-
# import os
# import signal
# import subprocess
# import threading
# import time
# from dataclasses import dataclass
# from typing import List, Dict, Optional, Literal
#
# Proxy = Dict[str, object]
# FrpFmt = Literal["ini", "toml"]
#
# def _ensure_dir(p: str) -> None:
#     os.makedirs(p, exist_ok=True)
#
# def _write_frpc_ini(path: str, server_addr: str, server_port: int, token: str, proxies: List[Proxy]) -> None:
#     lines = [
#         "[common]",
#         f"server_addr = {server_addr}",
#         f"server_port = {server_port}",
#         f"token = {token}",
#     ]
#     for p in proxies:
#         lines += [
#             "",
#             f"[{p['name']}]",
#             f"type = {p['type']}",
#             f"local_ip = {p.get('local_ip', '127.0.0.1')}",
#             f"local_port = {int(p['local_port'])}",
#             f"remote_port = {int(p['remote_port'])}",
#         ]
#     with open(path, "w", encoding="utf-8") as f:
#         f.write("\n".join(lines) + "\n")
#
# def _write_frpc_toml(path: str, server_addr: str, server_port: int, token: str, proxies: List[Proxy]) -> None:
#     lines = [
#         f'serverAddr = "{server_addr}"',
#         f"serverPort = {server_port}",
#         "",
#         "[auth]",
#         'method = "token"',
#         f'token = "{token}"',
#     ]
#     for p in proxies:
#         lines += [
#             "",
#             "[[proxies]]",
#             f'name = "{p["name"]}"',
#             f'type = "{p["type"]}"',
#             f'localIP = "{p.get("local_ip", "127.0.0.1")}"',
#             f"localPort = {int(p['local_port'])}",
#             f"remotePort = {int(p['remote_port'])}",
#         ]
#     with open(path, "w", encoding="utf-8") as f:
#         f.write("\n".join(lines) + "\n")
#
# @dataclass
# class FrpcHandle:
#     proc: subprocess.Popen
#     cfg_path: str
#     log_thread: threading.Thread
#
#     def stop(self) -> None:
#         """Stop frpc process gracefully then force kill if needed."""
#         if self.proc.poll() is not None:
#             return
#         try:
#             if os.name == "nt":
#                 # ask nicely
#                 self.proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore
#                 time.sleep(0.8)
#             else:
#                 self.proc.terminate()
#                 time.sleep(0.8)
#         except Exception:
#             pass
#         if self.proc.poll() is None:
#             try:
#                 self.proc.kill()
#             except Exception:
#                 pass
#
# def run_frpc(
#     frpc_path: str,
#     server_addr: str,
#     server_port: int,
#     token: str,
#     proxies: List[Proxy],
#     out_dir: str = "frp_run",
#     fmt: FrpFmt = "ini",
#     name: str = "frpc",
#     print_logs: bool = True,
# ) -> FrpcHandle:
#     """
#     One-call: write frpc config + start frpc + stream logs.
#     proxies example:
#       [{"name":"ground_ascan","type":"udp","local_port":9999,"remote_port":9000,"local_ip":"127.0.0.1"}]
#     """
#     if not proxies:
#         raise ValueError("proxies 不能为空（至少一个 udp proxy）")
#     _ensure_dir(out_dir)
#
#     cfg_path = os.path.join(out_dir, f"{name}.{fmt}")
#     if fmt == "ini":
#         _write_frpc_ini(cfg_path, server_addr, server_port, token, proxies)
#     else:
#         _write_frpc_toml(cfg_path, server_addr, server_port, token, proxies)
#
#     creationflags = 0
#     if os.name == "nt":
#         creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore
#
#     proc = subprocess.Popen(
#         [frpc_path, "-c", cfg_path],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#         encoding="utf-8",
#         errors="replace",
#         creationflags=creationflags,
#     )
#
#     def _log_pump():
#         if not proc.stdout:
#             return
#         for line in proc.stdout:
#             if print_logs:
#                 print(f"[{name}]", line.rstrip("\n"))
#
#     t = threading.Thread(target=_log_pump, daemon=True)
#     t.start()
#
#     print(f"[OK] frpc config: {cfg_path}")
#     print(f"[OK] frpc started: {frpc_path} -c {cfg_path}")
#     return FrpcHandle(proc=proc, cfg_path=cfg_path, log_thread=t)
