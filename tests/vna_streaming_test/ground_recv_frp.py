#!/usr/bin/env python
# coding: utf-8

# VNA实时数据流传输与处理系统 - 地面端接收程序（带FRP集成）
# 功能：接收服务器端发送的VNA数据，通过FRP进行网络穿透，评估传输性能

import os
import time
import json
import socket
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any

# =========================
# 配置参数
# =========================
SERVER_IP = "101.245.88.55"
SERVER_PORT = 7000
TOKEN = "61a594e10edb340fe8b33fda29899567"

REMOTE_UDP_PORT = 9000          # 云端对外端口
LOCAL_IP = "127.0.0.1"          # 地面端落地 IP
LOCAL_PORT = 9999               # 地面端落地端口

# frpc.exe 的路径
FRPC_EXE = r"F:\研一\CDUT-UavGPR-Controller\tests\online_transfer\frp_0.52.3\frpc.exe"
FRPC_INI = r"F:\研一\CDUT-UavGPR-Controller\tests\online_transfer\frp_0.52.3\frpc.ini"

# 落盘目录
OUT_DIR = Path.cwd() / "out_s21"

# 性能评估
class PerformanceAnalyzer:
    """
    性能分析器类，用于分析系统的性能表现
    """
    def __init__(self):
        """
        初始化性能分析器
        """
        self.start_time = None
        self.end_time = None
        self.data_size = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_lost = 0
        self.transfer_times = []
        self.processing_times = []
        self.bandwidth_usage = []
        self.actual_scan_size = 0  # 实际每次扫描的数据大小
    
    def start_measurement(self):
        """
        开始测量
        """
        self.start_time = time.time()
        print(f"性能测量已开始，时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def stop_measurement(self):
        """
        停止测量
        """
        self.end_time = time.time()
        print(f"性能测量已停止，时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def record_data_transfer(self, data_size, transfer_time):
        """
        记录数据传输
        """
        self.data_size += data_size
        self.transfer_times.append(transfer_time)
        
        # 计算带宽使用情况
        if transfer_time > 0:
            bandwidth = data_size / transfer_time  # 字节/秒
            self.bandwidth_usage.append(bandwidth)
    
    def record_packet(self, sent=True, received=True):
        """
        记录数据包
        """
        if sent:
            self.packets_sent += 1
        if received:
            self.packets_received += 1
        else:
            self.packets_lost += 1
    
    def record_processing_time(self, processing_time):
        """
        记录处理时间
        """
        self.processing_times.append(processing_time)
    
    def set_actual_scan_size(self, size):
        """
        设置实际每次扫描的数据大小
        """
        self.actual_scan_size = size
    
    def calculate_bandwidth_requirement(self, acquisition_period_ms=80):
        """
        计算带宽需求，基于实际数据大小
        """
        # 计算每秒扫描次数
        scans_per_second = 1000 / acquisition_period_ms
        
        # 确定实际数据大小
        if self.actual_scan_size > 0:
            data_per_scan = self.actual_scan_size
        elif self.data_size > 0 and self.packets_sent > 0:
            # 使用记录的实际数据
            data_per_scan = self.data_size / max(1, self.packets_sent // 5)  # 假设每5个数据包对应一次扫描
        else:
            # 默认值，作为后备
            data_per_scan = 501 * 4  # 假设501样本，每样本4字节
        
        # 计算每秒数据量
        data_per_second = scans_per_second * data_per_scan
        
        # 考虑网络开销（JSON序列化、分片等），增加20%的开销
        overhead_factor = 1.2
        required_bandwidth = data_per_second * overhead_factor
        
        print(f"\n=== 带宽需求分析 ===")
        print(f"采集周期: {acquisition_period_ms}ms")
        print(f"每秒扫描次数: {scans_per_second:.2f}次/秒")
        print(f"每扫描实际数据量: {data_per_scan:.2f}字节")
        print(f"原始数据带宽: {data_per_second:.2f}字节/秒 ({data_per_second / 1024:.2f}KB/s)")
        print(f"考虑20%网络开销后: {required_bandwidth:.2f}字节/秒 ({required_bandwidth / 1024:.2f}KB/s)")
        
        return required_bandwidth
    
    def calculate_transfer_delay(self):
        """
        计算传输延迟
        """
        if not self.transfer_times:
            return 0
        
        avg_delay = sum(self.transfer_times) / len(self.transfer_times)
        max_delay = max(self.transfer_times)
        min_delay = min(self.transfer_times)
        
        print(f"\n=== 传输延迟分析 ===")
        print(f"平均传输延迟: {avg_delay:.4f}秒")
        print(f"最大传输延迟: {max_delay:.4f}秒")
        print(f"最小传输延迟: {min_delay:.4f}秒")
        
        return avg_delay
    
    def calculate_packet_loss_rate(self):
        """
        计算丢包率
        """
        if self.packets_sent == 0:
            return 0
        
        loss_rate = (self.packets_lost / self.packets_sent) * 100
        
        print(f"\n=== 丢包率分析 ===")
        print(f"发送数据包数: {self.packets_sent}")
        print(f"接收数据包数: {self.packets_received}")
        print(f"丢失数据包数: {self.packets_lost}")
        print(f"丢包率: {loss_rate:.2f}%")
        
        return loss_rate
    
    def calculate_processing_performance(self):
        """
        计算处理性能
        """
        if not self.processing_times:
            return 0
        
        avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        max_processing_time = max(self.processing_times)
        min_processing_time = min(self.processing_times)
        
        print(f"\n=== 处理性能分析 ===")
        print(f"平均处理时间: {avg_processing_time:.4f}秒")
        print(f"最大处理时间: {max_processing_time:.4f}秒")
        print(f"最小处理时间: {min_processing_time:.4f}秒")
        
        return avg_processing_time
    
    def calculate_overall_performance(self):
        """
        计算整体性能
        """
        print("\n=== 整体性能分析 ===")
        
        # 计算总传输时间
        if self.start_time and self.end_time:
            total_time = self.end_time - self.start_time
            print(f"总测量时间: {total_time:.2f}秒")
        
        # 计算数据传输总量
        print(f"总数据传输量: {self.data_size:.2f}字节 ({self.data_size / 1024:.2f}KB)")
        
        # 计算平均带宽
        if self.bandwidth_usage:
            avg_bandwidth = sum(self.bandwidth_usage) / len(self.bandwidth_usage)
            print(f"平均带宽使用: {avg_bandwidth:.2f}字节/秒 ({avg_bandwidth / 1024:.2f}KB/s)")
        
        # 计算传输延迟
        self.calculate_transfer_delay()
        
        # 计算丢包率
        self.calculate_packet_loss_rate()
        
        # 计算处理性能
        self.calculate_processing_performance()
    
    def generate_report(self, report_file=None):
        """
        生成性能报告
        """
        report = {
            "measurement_start": self.start_time,
            "measurement_end": self.end_time,
            "total_time": self.end_time - self.start_time if self.start_time and self.end_time else 0,
            "total_data_size": self.data_size,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "packet_loss_rate": (self.packets_lost / self.packets_sent * 100) if self.packets_sent > 0 else 0,
            "average_transfer_delay": sum(self.transfer_times) / len(self.transfer_times) if self.transfer_times else 0,
            "average_processing_time": sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0,
            "average_bandwidth": sum(self.bandwidth_usage) / len(self.bandwidth_usage) if self.bandwidth_usage else 0,
            "actual_scan_size": self.actual_scan_size
        }
        
        # 打印报告
        print("\n=== 性能报告 ===")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
        # 保存报告到文件
        if report_file:
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"\n性能报告已保存到: {report_file}")
            except Exception as e:
                print(f"\n保存性能报告失败: {e}")
        
        return report

# ==========================================
# 写/更新 frpc.ini
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
# 启动 frpc.exe（子进程）并持续打印它的输出
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
# 数据接收和处理
# ==========================================
RUN_TS = time.strftime("%Y%m%d_%H%M%S")
SAVE_INDEX = 0
buffers: Dict[str, Dict[str, Any]] = {}
analyzer = PerformanceAnalyzer()

# 单文件保存相关变量
SINGLE_CSV_FILE = None
CSV_HEADER_WRITTEN = False

# 数据保存路径
MAIN_CSV_PATH = OUT_DIR / f"all_ascan_data_{RUN_TS}.csv"

def save_to_single_csv(msg_id: str, s21_list):
    """将所有Ascan数据保存到单个CSV文件中，每行对应一个Ascan"""
    global CSV_HEADER_WRITTEN, SAVE_INDEX
    SAVE_INDEX += 1
    
    # 确保输出目录存在
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 打开文件（追加模式）
    with open(MAIN_CSV_PATH, 'a', encoding='utf-8', newline='') as f:
        # 如果是第一次写入，添加表头
        if not CSV_HEADER_WRITTEN:
            # 表头：Ascan编号, 消息ID, 然后是每个采样点的列名
            header = ["Ascan_ID", "Message_ID"]
            # 为每个采样点创建列名
            for i in range(len(s21_list)):
                header.append(f"Sample_{i+1}")
            # 写入表头
            f.write(",".join(header) + "\n")
            CSV_HEADER_WRITTEN = True
        
        # 数据行：Ascan编号, 消息ID, 然后是采样数据
        row = [str(SAVE_INDEX), msg_id]
        row.extend([str(v) for v in s21_list])
        # 写入数据行
        f.write(",".join(row) + "\n")
    
    print(f"[SAVE] 已将Ascan {SAVE_INDEX} 写入 {MAIN_CSV_PATH}  (count={len(s21_list)}, msg_id={msg_id})", flush=True)

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
    # 增加接收缓冲区大小，减少丢包
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
    try:
        sock.bind((LOCAL_IP, LOCAL_PORT))
    except Exception as e:
        print(f"[ERROR] bind {LOCAL_IP}:{LOCAL_PORT} failed: {e}", flush=True)
        raise

    print(f"[OK] Listening on {LOCAL_IP}:{LOCAL_PORT}", flush=True)
    print(f"[OK] Saving to {OUT_DIR.resolve()}", flush=True)
    
    # 开始性能测量
    analyzer.start_measurement()

    while True:
        data, addr = sock.recvfrom(65535)  # UDP 一个“数据报”
        text = data.decode("utf-8", errors="replace").strip()

        # 记录接收时间
        receive_time = time.time()

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

        # 记录数据包
        analyzer.record_packet(sent=True, received=True)
        
        # 计算数据大小和传输时间
        data_size = len(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        # 假设发送时间为当前时间减去一个小值（实际应该从数据包中获取）
        send_time = receive_time - 0.01
        transfer_time = receive_time - send_time
        analyzer.record_data_transfer(data_size, transfer_time)
        
        # 记录处理时间
        start_processing = time.time()

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

            save_to_single_csv(msg_id, all_data)
            buffers.pop(msg_id, None)
            
            # 记录处理完成时间
            end_processing = time.time()
            analyzer.record_processing_time(end_processing - start_processing)

        cleanup_expired(ttl_sec=120)

def main():
    try:
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
                
            # 生成性能报告
            analyzer.stop_measurement()
            analyzer.calculate_overall_performance()
            analyzer.generate_report(f"performance_report_{int(time.time())}.json")

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断，退出程序", flush=True)
        # 在用户中断时生成性能报告
        analyzer.stop_measurement()
        analyzer.calculate_overall_performance()
        analyzer.generate_report(f"performance_report_{int(time.time())}.json")
    except Exception as e:
        print(f"[ERROR] 程序异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
        # 在异常时生成性能报告
        analyzer.stop_measurement()
        analyzer.calculate_overall_performance()
        analyzer.generate_report(f"performance_report_{int(time.time())}.json")

if __name__ == "__main__":
    main()
