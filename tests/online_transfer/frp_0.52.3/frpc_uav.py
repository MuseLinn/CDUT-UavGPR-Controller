# main_uav.py
import csv
import json
import socket
import struct
import threading
import time
from typing import List, Tuple, Iterable, Optional

from frpc_helper import run_frpc

SERVER_IP = "101.245.88.55"
REMOTE_ASCAN_PORT = 9000          # UAV 发 A-Scan 到云端的 UDP 端口
LOCAL_CTRL_PORT = 10001           # UAV 本地接收 CTRL 的端口（frpc 映射到这里）
CSV_PATH = r"C:\Users\17844\Desktop\all_ascan_data_20260121_143629.csv"

DEFAULT_INTERVAL_MS = 50          # 默认发送间隔
UDP_SAFE_PAYLOAD = 1000           # 单包数据部分大小（不含头），避免 MTU 问题
LOOP_CSV = True                   # CSV 发完是否循环


# ========== A-Scan 分片头（与你之前一致） ==========
MAGIC = b"ASCN"
HDR_FMT = "!4sIHHQ"  # magic, msg_id, part_idx, part_cnt, send_ts_ms
HDR_SIZE = struct.calcsize(HDR_FMT)


def pack_samples_float32(samples: List[float]) -> bytes:
    """把 samples 打包成 float32 二进制（小端），更接近“采集数据流”"""
    return struct.pack("<%sf" % len(samples), *samples)


def send_fragmented(sock: socket.socket, addr: Tuple[str, int], msg_id: int, payload: bytes,
                    chunk_size: int = UDP_SAFE_PAYLOAD) -> int:
    """应用层分片：HDR + chunk，返回分片数"""
    send_ts_ms = int(time.time() * 1000)
    chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)]
    if not chunks:
        chunks = [b""]

    part_cnt = len(chunks)
    for part_idx, ch in enumerate(chunks):
        hdr = struct.pack(HDR_FMT, MAGIC, msg_id & 0xFFFFFFFF, part_idx, part_cnt, send_ts_ms)
        sock.sendto(hdr + ch, addr)
    return part_cnt


def ctrl_recv_loop(stop_evt: threading.Event,
                   send_enable: threading.Event,
                   interval_ms_ref: dict,
                   bind_ip: str = "127.0.0.1",
                   bind_port: int = LOCAL_CTRL_PORT):
    """
    UAV 端接收 CTRL（通过 frpc 映射到本地 10001），解析 JSON 命令：
      - ASCAN_START：send_enable.set()，可选 interval_ms
      - ASCAN_STOP ：send_enable.clear()
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_ip, bind_port))
    sock.settimeout(0.5)

    print(f"[UAV][CTRL] 监听中：{bind_ip}:{bind_port}（等待地面端 CTRL）")

    while not stop_evt.is_set():
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[UAV][CTRL][错误] {e}")
            continue

        text = data.decode("utf-8", errors="replace")
        ts = time.strftime("%H:%M:%S")
        print(f"\n[{ts}] [UAV][CTRL] 来自 {addr} len={len(data)} TEXT={text}")

        try:
            obj = json.loads(text)
        except Exception:
            print("[UAV][CTRL] 非 JSON，忽略。")
            continue

        cmd = str(obj.get("cmd", "")).upper().strip()

        if cmd == "ASCAN_START":
            # 可选：允许地面端传 interval_ms
            if "interval_ms" in obj:
                try:
                    interval_ms_ref["value"] = int(obj["interval_ms"])
                except Exception:
                    pass

            send_enable.set()
            print(f"[UAV][TX] ✅ 收到 START：开始发送 A-Scan（interval={interval_ms_ref['value']}ms）")

        elif cmd == "ASCAN_STOP":
            send_enable.clear()
            print("[UAV][TX] ⛔ 收到 STOP：停止发送 A-Scan")

        else:
            print(f"[UAV][CTRL] 未识别 cmd={cmd}，已忽略。")

    try:
        sock.close()
    except Exception:
        pass


def ascan_send_loop(stop_evt: threading.Event,
                    send_enable: threading.Event,
                    interval_ms_ref: dict,
                    csv_path: str = CSV_PATH,
                    server_ip: str = SERVER_IP,
                    server_port: int = REMOTE_ASCAN_PORT,
                    loop_csv: bool = LOOP_CSV):
    """
    UAV 端“边采边发”线程：
    - 平时阻塞等待 send_enable
    - 被 START 打开后：持续读 CSV → 分片 → 发到云端 9000
    - 被 STOP 关闭后：立刻暂停（不继续读 CSV）
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (server_ip, server_port)

    print(f"[UAV][TX] 发送目标 -> {server_ip}:{server_port} | CSV={csv_path}")
    print("[UAV][TX] 初始状态：停止发送（等待地面端 ASCAN_START）")

    msg_id = 0

    # 打开文件并保持 reader 状态，方便 STOP 后再 START 时“继续往下读”
    try:
        f = open(csv_path, "r", encoding="utf-8", errors="replace", newline="")
    except Exception as e:
        print(f"[UAV][TX][错误] 打开 CSV 失败：{e}")
        return

    reader = csv.reader(f)
    header = next(reader, None)  # 跳过表头

    while not stop_evt.is_set():
        # 没收到 START 就睡眠等待
        if not send_enable.is_set():
            time.sleep(0.05)
            continue

        # 读下一行（只有在 START 状态下才会推进 CSV）
        try:
            row = next(reader)
        except StopIteration:
            if loop_csv:
                print("[UAV][TX] CSV 已到末尾，循环重读（持续采集模拟）")
                f.seek(0)
                reader = csv.reader(f)
                _ = next(reader, None)  # skip header
                continue
            else:
                print("[UAV][TX] CSV 已发送完毕，自动停止发送")
                send_enable.clear()
                continue

        if len(row) < 3:
            continue

        # samples 从第 3 列开始（Sample_1...Sample_501）
        samples: List[float] = []
        for x in row[2:]:
            try:
                samples.append(float(x))
            except Exception:
                samples.append(0.0)

        payload = pack_samples_float32(samples)

        try:
            parts = send_fragmented(sock, addr, msg_id=msg_id, payload=payload, chunk_size=UDP_SAFE_PAYLOAD)
        except OSError as e:
            print(f"[UAV][TX][错误] sendto 失败 msg_id={msg_id}: {e}")
            time.sleep(0.2)
            continue

        if msg_id % 20 == 0:
            print(f"[UAV][TX] msg_id={msg_id} samples={len(samples)} bytes={len(payload)} parts={parts}")

        msg_id += 1

        # 动态间隔（可由地面端 ASCAN_START 带 interval_ms 调整）
        interval_s = max(0, int(interval_ms_ref["value"])) / 1000.0
        if interval_s > 0:
            time.sleep(interval_s)

    try:
        f.close()
    except Exception:
        pass


if __name__ == "__main__":
    stop_evt = threading.Event()
    send_enable = threading.Event()          # 是否允许发送 A-Scan（由 CTRL 控制）
    interval_ms_ref = {"value": DEFAULT_INTERVAL_MS}  # 可动态修改的发送间隔

    # 1) UAV 启动 frpc：云端9100/udp -> 本地10001（CTRL）
    h = run_frpc(
        frpc_path=r"frpc.exe",
        server_addr=SERVER_IP,
        server_port=7000,
        token="61a594e10edb340fe8b33fda29899567",
        proxies=[
            {"name": "uav_ctrl_in", "type": "udp", "local_ip": "127.0.0.1", "local_port": LOCAL_CTRL_PORT, "remote_port": 9100},
        ],
        out_dir="frp_run",
        fmt="ini",
        name="frpc_uav",
    )

    # 2) CTRL 接收线程（控制 START/STOP）
    t_ctrl = threading.Thread(
        target=ctrl_recv_loop,
        args=(stop_evt, send_enable, interval_ms_ref, "127.0.0.1", LOCAL_CTRL_PORT),
        daemon=True
    )
    t_ctrl.start()

    # 3) A-Scan 发送线程（被 send_enable 控制）
    t_tx = threading.Thread(
        target=ascan_send_loop,
        args=(stop_evt, send_enable, interval_ms_ref, CSV_PATH, SERVER_IP, REMOTE_ASCAN_PORT, LOOP_CSV),
        daemon=True
    )
    t_tx.start()

    try:
        input("UAV 已运行：等待地面端按 Enter 发送 START/STOP。按回车退出 UAV...\n")
    finally:
        stop_evt.set()
        h.stop()
