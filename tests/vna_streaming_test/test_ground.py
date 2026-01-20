#!/usr/bin/env python
# coding: utf-8

# VNA实时数据流传输与处理系统 - 地面端测试
# 功能：实现数据接收、CSV存储和B-Scan实时绘制功能

import json
import socket
import threading
import time
import csv
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pathlib import Path
from datetime import datetime
import os

class DataReceiver:
    """
    数据接收类，用于接收服务器端传输的实时数据流
    """
    def __init__(self, local_ip, local_port, buffer_size=65535):
        """
        初始化数据接收器
        """
        self.local_ip = local_ip
        self.local_port = local_port
        self.buffer_size = buffer_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.is_running = False
        self.receive_thread = None
        self.data_callback = None
        self.buffers = {}  # 用于重组分片数据
        self.lock = threading.Lock()
    
    def set_data_callback(self, callback):
        """
        设置数据回调函数
        """
        self.data_callback = callback
    
    def start(self):
        """
        启动数据接收器
        """
        try:
            self.socket.bind((self.local_ip, self.local_port))
            print(f"数据接收器已启动，监听: {self.local_ip}:{self.local_port}")
            
            self.is_running = True
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"启动数据接收器失败: {e}")
            return False
    
    def stop(self):
        """
        停止数据接收器
        """
        self.is_running = False
        if self.receive_thread:
            self.receive_thread.join(timeout=5.0)
        
        try:
            self.socket.close()
            print("数据接收器已停止")
        except Exception as e:
            print(f"关闭socket失败: {e}")
    
    def _receive_loop(self):
        """
        数据接收循环
        """
        while self.is_running:
            try:
                data, addr = self.socket.recvfrom(self.buffer_size)
                text = data.decode("utf-8", errors="replace").strip()
                
                # 解析JSON数据
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    preview = text[:120].replace("\n", "\\n")
                    print(f"跳过非JSON数据，长度: {len(data)}，预览: '{preview}'")
                    continue
                
                # 处理数据
                self._process_data(obj)
                
                # 清理过期数据
                self._cleanup_expired(ttl_sec=60)
                
            except Exception as e:
                print(f"接收数据失败: {e}")
                # 短暂延迟，避免异常导致CPU占用过高
                time.sleep(0.01)
    
    def _process_data(self, obj):
        """
        处理接收到的数据
        """
        msg_type = obj.get("type", "")
        
        # 检查数据类型
        if msg_type not in {"ascan_s21_json", "s21_real_u_csv"}:
            return
        
        msg_id = obj.get("msg_id", "")
        part = int(obj.get("part", -1))
        total = int(obj.get("total_parts", -1))
        chunk = obj.get("data", [])
        
        # 检查必要字段
        if not msg_id or part < 0 or total <= 0:
            print(f"跳过字段不完整的数据包: {obj}")
            return
        
        # 存储分片数据
        with self.lock:
            info = self.buffers.setdefault(
                msg_id,
                {"total": total, "parts": {}, "meta": obj, "last_ts": time.time()},
            )
            info["total"] = total
            info["last_ts"] = time.time()
            info["parts"][part] = chunk
        
        # 检查是否接收完所有分片
        got = len(info["parts"])
        print(f"接收数据包: msg_id={msg_id[:8]} part={part+1}/{total} (已接收: {got}/{total})")
        
        if got == total:
            # 重组数据
            all_data = []
            for p in range(total):
                all_data.extend(info["parts"].get(p, []))
            
            # 验证数据长度
            n_samples = int(info["meta"].get("n_samples", 0))
            if n_samples and len(all_data) != n_samples:
                print(f"数据长度不匹配: 期望 {n_samples}，实际 {len(all_data)}")
            
            # 调用回调函数处理完整数据
            if self.data_callback:
                try:
                    timestamp = info["meta"].get("timestamp", time.time())
                    self.data_callback(np.array(all_data), timestamp)
                except Exception as e:
                    print(f"处理数据失败: {e}")
            
            # 从缓冲区中删除已处理的数据
            with self.lock:
                self.buffers.pop(msg_id, None)
    
    def _cleanup_expired(self, ttl_sec=60):
        """
        清理过期数据
        """
        now = time.time()
        dead = []
        
        with self.lock:
            for mid, info in self.buffers.items():
                if now - info.get("last_ts", now) > ttl_sec:
                    dead.append(mid)
            
            for mid in dead:
                self.buffers.pop(mid, None)
                print(f"清理过期数据: msg_id={mid[:8]}")

class DataStorage:
    """
    数据存储类，用于将接收到的数据以CSV格式持续写入文件
    """
    def __init__(self, output_dir="./data"):
        """
        初始化数据存储
        """
        self.output_dir = Path(output_dir)
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建CSV文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = self.output_dir / f"vna_data_{timestamp}.csv"
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
    
    def store_data(self, data, timestamp=None):
        """
        存储数据到CSV文件
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

class BScanPlotter:
    """
    B-Scan绘制类，用于实时绘制B-Scan图像
    """
    def __init__(self, num_traces=300):
        """
        初始化B-Scan绘制器
        """
        self.num_traces = num_traces
        self.bscan_data = []
        
        # 创建pyqtgraph窗口
        self.win = pg.GraphicsLayoutWidget(show=True, title=f'实时B-Scan图像 ({num_traces}道)')
        self.win.resize(1200, 800)
        
        # 添加绘图项
        self.plot = self.win.addPlot(title='B-Scan图像')
        self.plot.setLabel('bottom', '道数')
        self.plot.setLabel('left', '采样点')
        
        # 创建图像项
        self.img = pg.ImageItem(axisOrder='row-major')
        self.plot.addItem(self.img)
        
        # 设置坐标轴方向（时深关系）
        self.plot.invertY(True)
        
        # 使用seismic颜色映射
        cmap = pg.colormap.getFromMatplotlib('seismic')
        self.img.setLookupTable(cmap.getLookupTable())
        
        # 添加颜色条
        self.cbar = pg.ColorBarItem(label='幅度')
        self.cbar.setImageItem(self.img)
        self.win.addItem(self.cbar, row=0, col=1)
        
        # 禁用自动范围调整，避免图像闪烁
        self.plot.disableAutoRange()
    
    def update_bscan(self, ascan_data):
        """
        更新B-Scan图像
        """
        # 添加新数据
        self.bscan_data.append(ascan_data)
        
        # 限制数据长度
        if len(self.bscan_data) > self.num_traces:
            self.bscan_data.pop(0)
        
        # 转换为numpy数组并转置
        bscan_array = np.array(self.bscan_data).T
        
        # 更新图像
        self.img.setImage(bscan_array, axisOrder='row-major')
        self.img.setRect(QtCore.QRectF(0, 0, bscan_array.shape[1], bscan_array.shape[0]))
        
        # 更新颜色条范围
        min_val = np.min(bscan_array)
        max_val = np.max(bscan_array)
        self.cbar.setLevels((min_val, max_val))
        
        # 更新坐标轴范围
        self.plot.setXRange(0, bscan_array.shape[1])
        self.plot.setYRange(0, bscan_array.shape[0])
    
    def clear(self):
        """
        清空B-Scan数据
        """
        self.bscan_data.clear()
        # 更新图像
        self.img.setImage(np.array([]))

class VNAGroundStation:
    """
    VNA地面站类，整合数据接收、存储和B-Scan绘制功能
    """
    def __init__(self, local_ip="127.0.0.1", local_port=9999, num_traces=300):
        """
        初始化VNA地面站
        """
        self.local_ip = local_ip
        self.local_port = local_port
        self.num_traces = num_traces
        
        # 初始化组件
        self.data_receiver = DataReceiver(local_ip, local_port)
        self.data_storage = DataStorage()
        self.bscan_plotter = BScanPlotter(num_traces=num_traces)
        
        # 设置数据回调
        self.data_receiver.set_data_callback(self._data_callback)
    
    def start(self):
        """
        启动VNA地面站
        """
        return self.data_receiver.start()
    
    def stop(self):
        """
        停止VNA地面站
        """
        self.data_receiver.stop()
        self.data_storage.close()
    
    def _data_callback(self, data, timestamp):
        """
        数据回调函数
        """
        # 存储数据
        self.data_storage.store_data(data, timestamp)
        
        # 更新B-Scan图像
        self.bscan_plotter.update_bscan(data)
        
        print(f"处理数据: 长度={len(data)}, 时间戳={timestamp}")

def main():
    """
    主函数
    """
    # 确保有QApplication实例
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    
    # 配置参数
    LOCAL_IP = "127.0.0.1"  # 本地IP地址
    LOCAL_PORT = 9999  # 本地端口
    NUM_TRACES = 300  # 绘制的道数
    
    # 创建并启动VNA地面站
    ground_station = VNAGroundStation(local_ip=LOCAL_IP, local_port=LOCAL_PORT, num_traces=NUM_TRACES)
    
    try:
        if ground_station.start():
            print("VNA地面站已启动，等待接收数据...")
            print("按Ctrl+C停止...")
            # 运行QApplication事件循环
            app.exec()
    except KeyboardInterrupt:
        print("用户中断，停止地面站")
    finally:
        ground_station.stop()
        print("VNA地面站已停止")

if __name__ == "__main__":
    main()
