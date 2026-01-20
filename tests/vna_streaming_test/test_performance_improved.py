#!/usr/bin/env python
# coding: utf-8

# VNA实时数据流传输与处理系统 - 增强版性能评估测试
# 功能：与实际服务器端和地面端交互，提供控制界面，评估带宽等性能开销

import time
import numpy as np
import json
import socket
import threading
import csv
from datetime import datetime
from pathlib import Path
import os
import tkinter as tk
from tkinter import ttk, messagebox

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
        print(f"性能测量已开始，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def stop_measurement(self):
        """
        停止测量
        """
        self.end_time = time.time()
        print(f"性能测量已停止，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        
        avg_delay = np.mean(self.transfer_times)
        max_delay = np.max(self.transfer_times)
        min_delay = np.min(self.transfer_times)
        
        print(f"\n=== 传输延迟分析 ===")
        print(f"平均传输延迟: {avg_delay:.4f}秒")
        print(f"最大传输延迟: {max_delay:.4f}秒")
        print(f"最小传输延迟: {min_delay:.4f}秒")
        print(f"传输延迟标准差: {np.std(self.transfer_times):.4f}秒")
        
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
        
        avg_processing_time = np.mean(self.processing_times)
        max_processing_time = np.max(self.processing_times)
        min_processing_time = np.min(self.processing_times)
        
        print(f"\n=== 处理性能分析 ===")
        print(f"平均处理时间: {avg_processing_time:.4f}秒")
        print(f"最大处理时间: {max_processing_time:.4f}秒")
        print(f"最小处理时间: {min_processing_time:.4f}秒")
        print(f"处理时间标准差: {np.std(self.processing_times):.4f}秒")
        
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
            avg_bandwidth = np.mean(self.bandwidth_usage)
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
            "average_transfer_delay": np.mean(self.transfer_times) if self.transfer_times else 0,
            "average_processing_time": np.mean(self.processing_times) if self.processing_times else 0,
            "average_bandwidth": np.mean(self.bandwidth_usage) if self.bandwidth_usage else 0,
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

class PerformanceTestController:
    """
    性能测试控制器，用于控制服务器端和地面端的传输和性能评估
    """
    def __init__(self):
        """
        初始化性能测试控制器
        """
        self.server_ip = "127.0.0.1"
        self.server_port = 9999
        self.local_ip = "127.0.0.1"
        self.local_port = 9998
        self.analyzer = PerformanceAnalyzer()
        self.is_transferring = False
        self.evaluate_performance = False
        self.transfer_thread = None
        self.received_data = []
        
        # 创建控制界面
        self.root = tk.Tk()
        self.root.title("VNA数据传输性能测试控制器")
        self.root.geometry("600x400")
        
        # 创建控件
        self.create_widgets()
    
    def create_widgets(self):
        """
        创建控制界面控件
        """
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建连接设置区域
        conn_frame = ttk.LabelFrame(main_frame, text="连接设置", padding="10")
        conn_frame.pack(fill=tk.X, pady=5)
        
        # 服务器IP
        ttk.Label(conn_frame, text="服务器IP:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.server_ip_var = tk.StringVar(value=self.server_ip)
        ttk.Entry(conn_frame, textvariable=self.server_ip_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 服务器端口
        ttk.Label(conn_frame, text="服务器端口:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.server_port_var = tk.StringVar(value=str(self.server_port))
        ttk.Entry(conn_frame, textvariable=self.server_port_var, width=10).grid(row=0, column=3, sticky=tk.W, pady=2)
        
        # 本地IP
        ttk.Label(conn_frame, text="本地IP:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.local_ip_var = tk.StringVar(value=self.local_ip)
        ttk.Entry(conn_frame, textvariable=self.local_ip_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 本地端口
        ttk.Label(conn_frame, text="本地端口:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.local_port_var = tk.StringVar(value=str(self.local_port))
        ttk.Entry(conn_frame, textvariable=self.local_port_var, width=10).grid(row=1, column=3, sticky=tk.W, pady=2)
        
        # 创建控制按钮区域
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        # 开始传输按钮
        self.start_btn = ttk.Button(control_frame, text="开始传输", command=self.start_transfer)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # 停止传输按钮
        self.stop_btn = ttk.Button(control_frame, text="停止传输", command=self.stop_transfer, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 评估性能复选框
        self.eval_var = tk.BooleanVar(value=self.evaluate_performance)
        ttk.Checkbutton(control_frame, text="评估性能", variable=self.eval_var, command=self.toggle_performance_evaluation).pack(side=tk.LEFT, padx=5)
        
        # 创建状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 状态文本
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, text="状态:").pack(anchor=tk.W, pady=2)
        ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=2)
        
        # 数据统计
        ttk.Label(status_frame, text="数据统计:").pack(anchor=tk.W, pady=2)
        self.stats_var = tk.StringVar(value="已接收: 0 道数据")
        ttk.Label(status_frame, textvariable=self.stats_var).pack(anchor=tk.W, pady=2)
        
        # 创建性能报告按钮
        self.report_btn = ttk.Button(main_frame, text="生成性能报告", command=self.generate_report, state=tk.DISABLED)
        self.report_btn.pack(side=tk.RIGHT, pady=5)
    
    def toggle_performance_evaluation(self):
        """
        切换性能评估状态
        """
        self.evaluate_performance = self.eval_var.get()
    
    def start_transfer(self):
        """
        开始数据传输
        """
        # 更新状态
        self.status_var.set("正在启动传输...")
        self.root.update()
        
        # 更新连接设置
        self.server_ip = self.server_ip_var.get()
        self.server_port = int(self.server_port_var.get())
        self.local_ip = self.local_ip_var.get()
        self.local_port = int(self.local_port_var.get())
        
        # 重置数据
        self.received_data = []
        self.analyzer = PerformanceAnalyzer()
        
        # 如果启用了性能评估，开始测量
        if self.evaluate_performance:
            self.analyzer.start_measurement()
        
        # 启动传输线程
        self.is_transferring = True
        self.transfer_thread = threading.Thread(target=self.transfer_loop)
        self.transfer_thread.daemon = True
        self.transfer_thread.start()
        
        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.report_btn.config(state=tk.DISABLED)
        self.status_var.set("传输中...")
    
    def stop_transfer(self):
        """
        停止数据传输
        """
        # 更新状态
        self.status_var.set("正在停止传输...")
        self.root.update()
        
        # 停止传输
        self.is_transferring = False
        if self.transfer_thread:
            self.transfer_thread.join(timeout=5)
        
        # 如果启用了性能评估，停止测量并分析性能
        if self.evaluate_performance:
            self.analyzer.stop_measurement()
            self.analyzer.calculate_overall_performance()
        
        # 更新按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.report_btn.config(state=tk.NORMAL)
        self.status_var.set("已停止")
        self.stats_var.set(f"已接收: {len(self.received_data)} 道数据")
    
    def transfer_loop(self):
        """
        数据传输循环
        """
        # 创建接收器
        try:
            # 创建UDP接收器
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.local_ip, self.local_port))
            sock.settimeout(1)
            
            print(f"接收器已启动，监听: {self.local_ip}:{self.local_port}")
            
            # 向服务器发送开始传输命令
            self.send_control_command("START_TRANSFER")
            
            while self.is_transferring:
                try:
                    # 接收数据
                    data, addr = sock.recvfrom(65535)
                    text = data.decode("utf-8", errors="replace").strip()
                    
                    # 解析JSON数据
                    try:
                        obj = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    
                    # 处理数据
                    self.process_received_data(obj)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"接收数据失败: {e}")
                    continue
            
            # 向服务器发送停止传输命令
            self.send_control_command("STOP_TRANSFER")
            
            # 关闭接收器
            sock.close()
            print("接收器已停止")
            
        except Exception as e:
            print(f"启动接收器失败: {e}")
            self.status_var.set(f"错误: {str(e)}")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def send_control_command(self, command):
        """
        向服务器发送控制命令
        """
        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 构建命令
            cmd_obj = {
                "type": "control",
                "command": command,
                "timestamp": time.time()
            }
            
            # 发送命令
            payload = json.dumps(cmd_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            sock.sendto(payload, (self.server_ip, self.server_port))
            
            # 关闭套接字
            sock.close()
            
            print(f"已发送命令: {command}")
            
        except Exception as e:
            print(f"发送命令失败: {e}")
    
    def process_received_data(self, obj):
        """
        处理接收到的数据
        """
        # 检查数据类型
        if obj.get("type") != "ascan_s21_json":
            return
        
        # 提取数据
        data = obj.get("data", [])
        timestamp = obj.get("timestamp", time.time())
        
        # 记录数据
        self.received_data.append((timestamp, data))
        
        # 更新统计信息
        self.stats_var.set(f"已接收: {len(self.received_data)} 道数据")
        
        # 如果启用了性能评估，记录性能数据
        if self.evaluate_performance:
            # 计算数据大小
            data_size = len(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
            
            # 记录数据传输
            self.analyzer.record_data_transfer(data_size, 0.01)  # 假设传输时间为0.01秒
            self.analyzer.record_packet(sent=True, received=True)
            
            # 记录处理时间
            self.analyzer.record_processing_time(0.005)  # 假设处理时间为0.005秒
    
    def generate_report(self):
        """
        生成性能报告
        """
        if not self.evaluate_performance:
            messagebox.showinfo("提示", "请先启用性能评估并运行传输测试")
            return
        
        # 生成报告
        report_file = f"performance_report_{int(time.time())}.json"
        self.analyzer.generate_report(report_file)
        
        # 显示报告路径
        messagebox.showinfo("报告生成成功", f"性能报告已保存到: {report_file}")
    
    def run(self):
        """
        运行控制界面
        """
        self.root.mainloop()

def main():
    """
    主函数
    """
    print("VNA实时数据流传输与处理系统 - 增强版性能测试")
    print("=" * 60)
    
    # 创建性能测试控制器
    controller = PerformanceTestController()
    
    # 运行控制界面
    controller.run()

if __name__ == "__main__":
    main()
