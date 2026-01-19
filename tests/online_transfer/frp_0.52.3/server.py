import csv
import json
import socket
import time
import uuid
from typing import Dict, List, Tuple, Optional


def extract_params_and_ascans(
    csv_path: str,
    data_col_index: int = 3,
    delimiter: str = ",",
    header_rows: int = 4\4-9/
) -> Tuple[Dict[str, float], List[List[float]]]:
    """
    1) 前4行第一列: 解析 'xxx = value' -> params
    2) 后面数据区: 取 data_col_index 列，按 Number of Samples(=501) 分段成多条 A-scan
    """
    def parse_kv(line: str) -> Optional[Tuple[str, float]]:
        if "=" not in line:
            return None
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            return None
        try:
            return k, float(v)
        except ValueError:
            return None

    params: Dict[str, float] = {}
    ascans: List[List[float]] = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)

        # ---- 读前4行参数 ----
        header_lines: List[str] = []
        for _ in range(header_rows):
            row = next(reader, None)
            if not row:
                break
            header_lines.append(row[0].strip())

        for line in header_lines:
            kv = parse_kv(line)
            if kv:
                k, val = kv
                params[k] = val

        if "Number of Samples" not in params:
            raise ValueError("没解析到 'Number of Samples'，请检查 CSV 前4行第一列格式。")

        n_samples = int(params["Number of Samples"])

        # ---- 读数据区，按 n_samples 分段 ----
        current: List[float] = []
        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            if len(row) <= data_col_index:
                continue

            cell = row[data_col_index].strip()
            if cell == "":
                continue

            try:
                v = float(cell)  # 注意：这里就是“正常浮点数”float64（Python float）
            except ValueError:
                continue

            current.append(v)
            if len(current) == n_samples:
                ascans.append(current)
                current = []

    return params, ascans


def chunk_by_max_bytes(
    base_obj: dict,
    data_list: List[float],
    max_bytes: int = 1100,
) -> List[dict]:
    """
    把 data_list 切成多片，使得每个 JSON 包尽量不超过 max_bytes（保守一点避开 1500 MTU）
    """
    chunks = []
    part = 0
    i = 0
    n = len(data_list)

    while i < n:
        # 先猜一个窗口大小，然后根据 JSON 长度缩放
        step = min(80, n - i)  # 初始猜测（后面会调整）
        while True:
            candidate = data_list[i : i + step]
            obj = dict(base_obj)
            obj["part"] = part
            obj["data"] = candidate
            b = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

            if len(b) <= max_bytes:
                # 尝试再多塞一点（尽量利用带宽）
                if i + step >= n:
                    break
                step2 = min(step + 20, n - i)
                candidate2 = data_list[i : i + step2]
                obj2 = dict(base_obj)
                obj2["part"] = part
                obj2["data"] = candidate2
                b2 = json.dumps(obj2, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                if len(b2) <= max_bytes:
                    step = step2
                    continue
                break
            else:
                # 太大就减小
                if step <= 1:
                    break
                step = max(1, step // 2)

        final_candidate = data_list[i : i + step]
        chunks.append(final_candidate)
        i += step
        part += 1

    # 组装成最终包对象列表（把 total_parts 填进去）
    total = len(chunks)
    out_packets = []
    for p, arr in enumerate(chunks):
        obj = dict(base_obj)
        obj["part"] = p
        obj["total_parts"] = total
        obj["data"] = arr
        out_packets.append(obj)
    return out_packets


def main():
    # ======= 你需要改的参数 =======
    CSV_PATH = r"C:\Users\17844\Desktop\测线main_40dbm_普通飞高.csv"
    DATA_COL_INDEX = 3  # 你图里“雷达反射波”在第4列 -> index=3
    SERVER_IP = "101.245.88.55"
    SERVER_PORT = 9000
    MAX_UDP_BYTES = 1100  # 非常关键：小于 1500，避免被截断
    SEND_INTERVAL = 0.01  # 两包间隔（秒），避免 4G/NAT 抖动；可调大一点

    # params： 前四行的参数   ascans： 每行都是一道501点的ascan
    params, ascans = extract_params_and_ascans(
        CSV_PATH,
        data_col_index=DATA_COL_INDEX,
    )

    if not ascans:
        raise RuntimeError("没有提取到任何 A-scan（ascans 为空），请检查 CSV 格式/列索引。")

    # 这里只发第一条 A-scan 作为测试，你也可以循环发多条
    s21 = ascans[0]
    msg_id = uuid.uuid4().hex
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    base_obj = {
        "type": "ascan_s21_json",
        "ts": ts,
        "msg_id": msg_id,
        "n_samples": int(params["Number of Samples"]),
        # params 也可以带上（可选）
        "params": params,
    }

    packets = chunk_by_max_bytes(base_obj, s21, max_bytes=MAX_UDP_BYTES)

    print(f"[OK] A-scan points = {len(s21)}")
    print(f"[OK] will send {len(packets)} packets, msg_id={msg_id}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = (SERVER_IP, SERVER_PORT)

    for obj in packets:
        payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        sock.sendto(payload, server)
        time.sleep(SEND_INTERVAL)

    sock.close()
    print("[DONE] all packets sent.")


if __name__ == "__main__":
    main()
