import os
import time
import json
import socket
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any

# =========================
# 1) 需要你确认/修改的配置
# =========================
SERVER_IP = "101.245.88.55"
SERVER_PORT = 7000
TOKEN = "61a594e10edb340fe8b33fda29899567"

REMOTE_UDP_PORT = 9000          # 云端对外端口
LOCAL_IP = "127.0.0.1"          # 地面端落地 IP
LOCAL_PORT = 9999               # 地面端落地端口（你的 Python bind 这个）

# frpc.exe 的路径（推荐放在同目录）
FRPC_EXE = r".\frpc.exe"
FRPC_INI = r".\frpc.ini"

# 落盘目录
OUT_DIR = Path.cwd() / "out_s21"


# ==========================================
# 2) 写/更新 frpc.ini（你也可以选择不覆盖）
# ==========================================
def write_frpc_ini(path: str):
    content = f"""[common]
server_addr = {SERVER_IP}
server_port = {SERVER_PORT}
token = {TOKEN}

[groundudp]
type = udp
local_ip = {LOCAL_IP}
local_port = {LOCAL_PORT}
remote_port = {REMOTE_UDP_PORT}
"""
    Path(path).write_text(content, encoding="utf-8")
    print(f"[OK] frpc.ini written to: {Path(path).resolve()}", flush=True)


# ==========================================
# 3) 启动 frpc.exe（子进程）并持续打印它的输出
# ==========================================
def start_frpc():
    exe = Path(FRPC_EXE)
    ini = Path(FRPC_INI)

    if not exe.exists():
        raise FileNotFoundError(f"frpc.exe not found: {exe.resolve()}")
    if not ini.exists():
        raise FileNotFoundError(f"frpc.ini not found: {ini.resolve()}")

    # 用 list 方式传参，避免路径里空格导致的各种报错
    cmd = [str(exe), "-c", str(ini)]

    print(f"[OK] 正在启动 frpc: {' '.join(cmd)}", flush=True)

    # stdout/stderr 合并，便于你看到 login success 等日志
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    def pump():
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line:
                print(f"[FRPC] {line}", flush=True)

    t = threading.Thread(target=pump, daemon=True)
    t.start()

    return proc


# ==========================================
# 4) 你的接收+重组+落盘逻辑（对齐 ground_recv_test7）
#    - 同时兼容两种 type：ascan_s21_json / s21_real_u_csv
# ==========================================
RUN_TS = time.strftime("%Y%m%d_%H%M%S")
SAVE_INDEX = 0
buffers: Dict[str, Dict[str, Any]] = {}


def save_s21_csv(msg_id: str, s21_list):
    global SAVE_INDEX
    SAVE_INDEX += 1
    idx_str = f"{SAVE_INDEX:04d}"
    short_id = (msg_id or "noid")[:8]
    filename = f"{RUN_TS}_{idx_str}_{short_id}.csv"
    path = OUT_DIR / filename

    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("S21 Real(U)\n")
        for v in s21_list:
            f.write(f"{v}\n")

    print(f"[SAVE] {path}  (count={len(s21_list)}, msg_id={msg_id})", flush=True)


def cleanup_expired(ttl_sec: int = 60):
    now = time.time()
    dead = []
    for mid, info in buffers.items():
        if now - info.get("last_ts", now) > ttl_sec:
            dead.append(mid)
    for mid in dead:
        buffers.pop(mid, None)
        print(f"[CLEAN] drop expired msg_id={mid}", flush=True)


def run_receiver():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((LOCAL_IP, LOCAL_PORT))
    except Exception as e:
        print(f"[ERROR] bind {LOCAL_IP}:{LOCAL_PORT} failed: {e}", flush=True)
        raise

    print(f"[OK] Listening on {LOCAL_IP}:{LOCAL_PORT}", flush=True)
    print(f"[OK] Saving to {OUT_DIR.resolve()}", flush=True)

    while True:
        data, addr = sock.recvfrom(65535)  # UDP 一个“数据报”
        text = data.decode("utf-8", errors="replace").strip()

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            preview = text[:120].replace("\n", "\\n")
            print(f"[SKIP] non-json from {addr}, len={len(data)} preview='{preview}'", flush=True)
            continue

        msg_type = obj.get("type", "")

        # 兼容你之前用过的两种 type 名字
        if msg_type not in {"ascan_s21_json", "s21_real_u_csv"}:
            continue

        msg_id = obj.get("msg_id", "")
        part = int(obj.get("part", -1))
        total = int(obj.get("total_parts", -1))
        chunk = obj.get("data", [])

        if not msg_id or part < 0 or total <= 0:
            print(f"[WARN] bad packet fields from {addr}: {obj}", flush=True)
            continue

        info = buffers.setdefault(
            msg_id,
            {"total": total, "parts": {}, "meta": obj, "last_ts": time.time()},
        )
        info["total"] = total
        info["last_ts"] = time.time()
        info["parts"][part] = chunk

        got = len(info["parts"])
        print(f"[RX] msg_id={msg_id[:8]} part={part+1}/{total} (got={got}/{total})", flush=True)

        if got == total:
            all_data = []
            for p in range(total):
                all_data.extend(info["parts"].get(p, []))

            # 可选长度校验（如果发送端携带 n_samples）
            n_samples = int(info["meta"].get("n_samples", 0))
            if n_samples and len(all_data) != n_samples:
                print(f"[WARN] length mismatch: expect {n_samples}, got {len(all_data)}", flush=True)

            save_s21_csv(msg_id, all_data)
            buffers.pop(msg_id, None)

        cleanup_expired(ttl_sec=120)


def main():
    # 1) 写 ini（每次启动都保证一致）
    write_frpc_ini(FRPC_INI)

    # 2) 启动 frpc
    frpc_proc = start_frpc()

    try:
        # 3) 启动接收（主线程跑接收，Ctrl+C 结束）
        run_receiver()
    finally:
        # 退出时尽量关掉 frpc
        if frpc_proc and frpc_proc.poll() is None:
            print("[OK] stopping frpc...", flush=True)
            frpc_proc.terminate()


if __name__ == "__main__":
    main()
