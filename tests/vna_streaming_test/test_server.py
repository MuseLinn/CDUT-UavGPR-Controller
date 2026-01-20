#!/usr/bin/env python
# coding: utf-8

# VNA实时数据流传输与处理系统 - 服务器端测试
# 功能：实现VNA设备的实时数据流读取、缓存、CSV写入和远程传输

import pyvisa as visa
import numpy as np
import time
import csv
import json
import socket
import threading
import uuid
from queue import Queue
from datetime import datetime
import os

class SimpleVNAController:
    """
    简化版矢网仪控制器类，用于读取A-Scan时域数据
    """
    def __init__(self):
        """
        初始化矢网仪控制器
        """
        self.rm = None
        self.vna = None
        self.current_channel = 1
        self.current_measurement = 1
        
        try:
            self.rm = visa.ResourceManager()
            print("VISA资源管理器初始化成功")
        except Exception as e:
            print(f"VISA资源管理器初始化失败: {e}")
            self.rm = None

    def list_devices(self):
        """
        列出所有连接的VISA设备
        """
        if not self.rm:
            print("资源管理器未初始化")
            return []
        try:
            resources = self.rm.list_resources()
            print(f"发现设备: {resources}")
            return resources
        except Exception as e:
            print(f"列出设备失败: {e}")
            return []

    def open_device(self, resource_name, timeout=30000):
        """
        打开VISA设备
        """
        if not self.rm:
            print("资源管理器未初始化")
            return False
        
        try:
            print(f"正在打开设备: {resource_name}")
            self.close_device()  # 确保之前的连接已关闭
            self.vna = self.rm.open_resource(resource_name)
            self.vna.timeout = timeout  # 增加超时时间到30秒
            self.vna.write_termination = '\n'
            self.vna.read_termination = '\n'
            
            # 检查设备ID
            idn = self.query("*IDN?")
            print(f"设备ID: {idn}")
            
            # 设置数据格式为二进制
            self.write("FORM:DATA REAL,32")  # 32位浮点数
            self.write("FORM:BORD NORM")     # 正常字节顺序
            
            return True
        except Exception as e:
            print(f"打开设备失败: {e}")
            self.vna = None
            return False

    def close_device(self):
        """
        关闭VISA设备
        """
        if self.vna:
            try:
                self.vna.close()
                print("设备已关闭")
            except Exception as e:
                print(f"关闭设备失败: {e}")
            finally:
                self.vna = None

    def write(self, command):
        """
        发送命令到设备
        """
        if not self.vna:
            print("设备未连接")
            return False
        try:
            self.vna.write(command)
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False

    def query(self, command):
        """
        发送查询命令并返回响应
        """
        if not self.vna:
            print("设备未连接")
            return None
        try:
            return self.vna.query(command).strip()
        except Exception as e:
            print(f"查询失败: {e}")
            return None

    def read_ascan_data(self):
        """
        直接读取VNA显示的A-Scan时域数据
        """
        if not self.vna:
            print("设备未连接")
            return None
        
        try:
            # 设置数据格式为ASCII
            self.write("FORM:DATA ASCII")
            
            # 使用FDATA获取显示的时域数据
            command = f"CALC{self.current_channel}:MEAS{self.current_measurement}:DATA:FDATA?"
            ascii_data = self.query(command)
            
            # 解析ASCII数据
            if ascii_data:
                # 分割数据并转换为浮点数
                data_points = ascii_data.split(',')
                float_data = [float(point) for point in data_points if point.strip()]
                np_data = np.array(float_data)
                return np_data
            
            return None
        except Exception as e:
            print(f"读取A-Scan数据失败: {e}")
            return None

class DataCache:
    """
    数据缓存类，用于缓存VNA读取的数据
    """
    def __init__(self, max_size=1000):
        """
        初始化数据缓存
        """
        self.cache = []
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def add_data(self, data, timestamp=None):
        """
        添加数据到缓存
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.cache.append((timestamp, data))
            # 如果缓存超过最大容量，删除最早的数据
            if len(self.cache) > self.max_size:
                self.cache.pop(0)
    
    def get_all_data(self):
        """
        获取所有缓存数据
        """
        with self.lock:
            return self.cache.copy()
    
    def get_latest_data(self):
        """
        获取最新的缓存数据
        """
        with self.lock:
            if self.cache:
                return self.cache[-1]
            return None
    
    def clear(self):
        """
        清空缓存
        """
        with self.lock:
            self.cache.clear()
    
    def size(self):
        """
        获取缓存大小
        """
        with self.lock:
            return len(self.cache)

class DataWriter:
    """
    数据写入类，用于将实时数据流以CSV格式持续写入文件
    """
    def __init__(self, output_dir="./data"):
        """
        初始化数据写入器
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 创建CSV文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = os.path.join(output_dir, f"vna_data_{timestamp}.csv")
        self.file = None
        self.writer = None
        self.lock = threading.Lock()
        
        # 打开文件并写入表头
        self._open_file()
    
    def _open_file(self):
        """
        打开文件并初始化写入器
        """
        try:
            self.file = open(self.csv_file, 'w', newline='', encoding='utf-8')
            self.writer = csv.writer(self.file)
            # 写入表头
            self.writer.writerow(["Timestamp", "Data"])
            print(f"CSV文件已创建: {self.csv_file}")
        except Exception as e:
            print(f"打开CSV文件失败: {e}")
    
    def write_data(self, data, timestamp=None):
        """
        写入数据到CSV文件
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            if self.writer:
                try:
                    # 写入时间戳和数据
                    data_str = ','.join(map(str, data))
                    self.writer.writerow([timestamp, data_str])
                    # 刷新文件缓冲区，确保数据立即写入
                    self.file.flush()
                except Exception as e:
                    print(f"写入CSV文件失败: {e}")
    
    def close(self):
        """
        关闭文件
        """
        with self.lock:
            if self.file:
                try:
                    self.file.close()
                    print(f"CSV文件已关闭: {self.csv_file}")
                except Exception as e:
                    print(f"关闭CSV文件失败: {e}")
                finally:
                    self.file = None
                    self.writer = None

class DataTransmitter:
    """
    数据传输类，用于将实时数据流传输至地面端
    """
    def __init__(self, server_ip, server_port, max_udp_bytes=1100):
        """
        初始化数据传输器
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.max_udp_bytes = max_udp_bytes
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.lock = threading.Lock()
    
    def chunk_by_max_bytes(self, base_obj, data_list):
        """
        把数据切成多片，使得每个JSON包尽量不超过max_bytes
        """
        chunks = []
        part = 0
        i = 0
        n = len(data_list)
        
        while i < n:
            # 先猜一个窗口大小，然后根据JSON长度缩放
            step = min(80, n - i)  # 初始猜测
            while True:
                candidate = data_list[i : i + step]
                obj = dict(base_obj)
                obj["part"] = part
                obj["data"] = candidate
                b = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                
                if len(b) <= self.max_udp_bytes:
                    # 尝试再多塞一点
                    if i + step >= n:
                        break
                    step2 = min(step + 20, n - i)
                    candidate2 = data_list[i : i + step2]
                    obj2 = dict(base_obj)
                    obj2["part"] = part
                    obj2["data"] = candidate2
                    b2 = json.dumps(obj2, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                    if len(b2) <= self.max_udp_bytes:
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
        
        # 组装成最终包对象列表
        total = len(chunks)
        out_packets = []
        for p, arr in enumerate(chunks):
            obj = dict(base_obj)
            obj["part"] = p
            obj["total_parts"] = total
            obj["data"] = arr
            out_packets.append(obj)
        return out_packets
    
    def send_data(self, data, timestamp=None):
        """
        发送数据到地面端
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            try:
                # 构建基础对象
                msg_id = uuid.uuid4().hex
                ts = time.strftime("%Y-%m-%dT%H:%M:%S")
                
                base_obj = {
                    "type": "ascan_s21_json",
                    "ts": ts,
                    "msg_id": msg_id,
                    "n_samples": len(data),
                    "timestamp": timestamp
                }
                
                # 分片数据
                packets = self.chunk_by_max_bytes(base_obj, data.tolist())
                
                # 发送数据包
                for packet in packets:
                    payload = json.dumps(packet, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                    self.socket.sendto(payload, (self.server_ip, self.server_port))
                    # 短暂延迟，避免网络拥塞
                    time.sleep(0.001)
                
                return True
            except Exception as e:
                print(f"发送数据失败: {e}")
                return False
    
    def close(self):
        """
        关闭socket
        """
        try:
            self.socket.close()
            print("数据传输socket已关闭")
        except Exception as e:
            print(f"关闭socket失败: {e}")

class VNAServer:
    """
    VNA服务器类，整合VNA数据读取、缓存、CSV写入和远程传输功能
    """
    def __init__(self, device_name, server_ip, server_port, acquisition_period_ms=80, max_cache_size=1000):
        """
        初始化VNA服务器
        """
        self.device_name = device_name
        self.server_ip = server_ip
        self.server_port = server_port
        self.acquisition_period_ms = acquisition_period_ms
        self.max_cache_size = max_cache_size
        
        # 初始化组件
        self.vna_controller = SimpleVNAController()
        self.data_cache = DataCache(max_size=max_cache_size)
        self.data_writer = DataWriter()
        self.data_transmitter = DataTransmitter(server_ip, server_port)
        
        # 线程控制
        self.is_running = False
        self.acquisition_thread = None
    
    def start(self):
        """
        启动VNA服务器
        """
        # 连接VNA设备
        if not self.vna_controller.open_device(self.device_name):
            print("无法打开VNA设备，服务器启动失败")
            return False
        
        # 启动数据采集线程
        self.is_running = True
        self.acquisition_thread = threading.Thread(target=self._acquisition_loop)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()
        
        print(f"VNA服务器已启动，采集周期: {self.acquisition_period_ms}ms")
        return True
    
    def stop(self):
        """
        停止VNA服务器
        """
        self.is_running = False
        if self.acquisition_thread:
            self.acquisition_thread.join(timeout=5.0)
        
        # 关闭组件
        self.vna_controller.close_device()
        self.data_writer.close()
        self.data_transmitter.close()
        
        print("VNA服务器已停止")
    
    def _acquisition_loop(self):
        """
        数据采集循环
        """
        while self.is_running:
            start_time = time.time()
            
            # 读取A-Scan数据
            ascan_data = self.vna_controller.read_ascan_data()
            
            if ascan_data is not None:
                # 添加数据到缓存
                self.data_cache.add_data(ascan_data)
                
                # 写入数据到CSV文件
                self.data_writer.write_data(ascan_data)
                
                # 直接传输数据到地面端，无需控制指令
                self.data_transmitter.send_data(ascan_data)
                
                # 打印采集信息
                print(f"采集到A-Scan数据，长度: {len(ascan_data)}，缓存大小: {self.data_cache.size()}")
            
            # 控制采集周期
            elapsed = time.time() - start_time
            wait_time = self.acquisition_period_ms / 1000 - elapsed
            if wait_time > 0:
                time.sleep(wait_time)

def main():
    """
    主函数
    """
    # 配置参数
    DEVICE_NAME = "TCPIP0::MagicbookPro16-Hunter::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR"
    SERVER_IP = "101.245.88.55"  # FRP服务器IP地址
    SERVER_PORT = 9000  # FRP服务器UDP端口
    ACQUISITION_PERIOD_MS = 80  # 采集周期（毫秒）
    
    # 创建并启动VNA服务器
    server = VNAServer(DEVICE_NAME, SERVER_IP, SERVER_PORT, ACQUISITION_PERIOD_MS)
    
    try:
        if server.start():
            print("VNA服务器已启动，按Ctrl+C停止...")
            # 运行服务器
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("用户中断，停止服务器")
    finally:
        server.stop()

if __name__ == "__main__":
    main()
