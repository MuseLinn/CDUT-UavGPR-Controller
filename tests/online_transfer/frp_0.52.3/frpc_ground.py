# frpc_test2.py  （地面端：按Enter切换发送 START/STOP + 接收A-Scan打印）
# -*- coding: utf-8 -*-
import argparse
import json
import socket
import struct
import threading
import time
import uuid

# 解析 UAV A-Scan 分片头（和 UAV 一致）
MAGIC = b"ASCN"
HDR_FMT = "!4sIHHQ"
HDR_SIZE = struct.calcsize(HDR_FMT)


def send_ctrl_once(server_ip: str, ctrl_port: int, cmd: str, interval_ms: int):
    """发送一次 CTRL JSON 到云端 ctrl_port（9100）"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (server_ip, ctrl_port)

    payload = {
        "type": "CTRL",
        "cmd": cmd,
        "interval_ms": interval_ms,          # START 时可用于告诉 UAV 发送间隔
        "msg_id": uuid.uuid4().hex[:12],
        "ts_ms": int(time.time() * 1000),
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sock.sendto(data, addr)
    sock.close()

    print(f"[GROUND][TX] -> {server_ip}:{ctrl_port} cmd={cmd} interval_ms={interval_ms} len={len(data)}")


def ascan_rx_print_loop(stop_evt: threading.Event, bind_ip: str, bind_port: int):
    """
    监听本地 A-Scan 入口（一般是 frpc 映射：云端9000 -> 本地9999）
    这里不做重组，只打印收到的分片头信息，方便确认“确实在收数据”
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_ip, bind_port))
    sock.settimeout(0.5)
    print(f"[GROUND][RX] A-Scan 监听中：{bind_ip}:{bind_port}")

    while not stop_evt.is_set():
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[GROUND][RX][错误] {e}")
            continue

        ts = time.strftime("%H:%M:%S")
        print(f"\n[{ts}] [GROUND][RX] 来自 {addr} len={len(data)} bytes")

        # 尝试解析分片头
        if len(data) >= HDR_SIZE:
            try:
                magic, msg_id, part_idx, part_cnt, send_ts_ms = struct.unpack(HDR_FMT, data[:HDR_SIZE])
                if magic == MAGIC:
                    print(f"[GROUND][RX] ASCN 分片：msg_id={msg_id} part={part_idx+1}/{part_cnt} send_ts_ms={send_ts_ms}")
                else:
                    print("[GROUND][RX] 非 ASCN 数据（magic 不匹配）")
            except Exception as e:
                print(f"[GROUND][RX] 解析头失败：{e}")

    try:
        sock.close()
    except Exception:
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--server_ip", default="101.245.88.55")
    ap.add_argument("--ctrl_port", type=int, default=9100)

    # 你地面端用于收 A-Scan 的本地端口（frpc：9000 -> 9999）
    ap.add_argument("--listen_ip", default="127.0.0.1")
    ap.add_argument("--listen_port", type=int, default=9999)

    # START 时告诉 UAV 的发送间隔
    ap.add_argument("--interval_ms", type=int, default=50)

    args = ap.parse_args()

    stop_evt = threading.Event()

    # 后台线程：接收 A-Scan 并打印
    t_rx = threading.Thread(
        target=ascan_rx_print_loop,
        args=(stop_evt, args.listen_ip, args.listen_port),
        daemon=True
    )
    t_rx.start()

    sending = False  # 当前是否“认为 UAV 正在发”（由你按键切换）

    print("\n[GROUND] 操作说明：")
    print("  - 直接按 Enter：切换发送命令（START <-> STOP）")
    print("  - 输入 q 回车：退出\n")

    try:
        while True:
            s = input(">>> ")
            if s.strip().lower() == "q":
                break

            # 每次 Enter 切换一次命令并只发一次
            if not sending:
                send_ctrl_once(args.server_ip, args.ctrl_port, cmd="ASCAN_START", interval_ms=args.interval_ms)
                sending = True
                print("[GROUND] 已发送 START（让 UAV 开始发 A-Scan）")
            else:
                send_ctrl_once(args.server_ip, args.ctrl_port, cmd="ASCAN_STOP", interval_ms=args.interval_ms)
                sending = False
                print("[GROUND] 已发送 STOP（让 UAV 停止发 A-Scan）")

    finally:
        stop_evt.set()
        time.sleep(0.2)
