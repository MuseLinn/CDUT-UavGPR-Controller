#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK数据采集测试脚本
用于验证RTK模块功能，包括NTRIP配置、数据解析和存储
作者: MuseLinn
日期: 2025-09-16
"""

import base64
import csv
import socket
import sys
import time
from datetime import datetime

import serial


class RTKTester:
    def __init__(self):
        # 串口配置
        self.port = "COM11"  # Windows下的串口端口，根据实际情况修改
        self.baudrate = 115200
        self.ser = None
        
        # NTRIP配置
        self.ntrip_server = "203.107.45.154"
        self.ntrip_port = 8003
        self.ntrip_username = "qxykhy009245"
        self.ntrip_password = "a72a12f"
        self.ntrip_mountpoint = "AUTO"
        self.ntrip_socket = None
        self.ntrip_connected = False
        
        # 数据存储
        self.data_file = "rtk_test_data.csv"
        self.gga_data = ""
        self.last_gga_time = 0
        
        # 初始化数据文件
        self.init_data_file()

    def init_data_file(self):
        """初始化数据文件，写入表头"""
        with open(self.data_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'latitude', 'longitude', 'altitude', 'quality', 'satellites', 'hdop'])

    def connect_serial(self):
        """连接RTK串口"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"成功连接到串口 {self.port}")
            
            # 发送配置命令
            self.ser.write(b'UNLOG\r\n')
            time.sleep(1)
            self.ser.write(b'#A GNGGA 0.05\r\n')  # 设置GNGGA输出频率为20Hz (0.05秒)
            time.sleep(1)
            print("已配置RTK模块输出频率为20Hz")
            self.ser.write(b'#A GNRMC 1\r\n') # 启用GNRMC数据，默认输出频率为1Hz
            time.sleep(1)
            print("已配置RTK模块输出GNRMC数据")
            return True
        except Exception as e:
            print(f"串口连接失败: {e}")
            return False

    def connect_ntrip(self):
        """连接NTRIP服务器"""
        try:
            self.ntrip_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ntrip_socket.connect((self.ntrip_server, self.ntrip_port))
            
            # 构造认证字符串
            auth_str = f"{self.ntrip_username}:{self.ntrip_password}"
            auth_bytes = auth_str.encode('utf-8')
            auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            # 发送HTTP请求
            request = (
                f"GET /{self.ntrip_mountpoint} HTTP/1.0\r\n"
                f"User-Agent: NTRIP RTKTester/1.0\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n"
                f"Authorization: Basic {auth_base64}\r\n"
                f"\r\n"
            )
            
            self.ntrip_socket.send(request.encode('utf-8'))
            
            # 检查响应
            response = self.ntrip_socket.recv(1024)
            if b"ICY 200 OK" in response:
                self.ntrip_connected = True
                print("成功连接到NTRIP服务器")
                return True
            else:
                print(f"NTRIP服务器连接失败: {response}")
                return False
        except Exception as e:
            print(f"NTRIP连接失败: {e}")
            return False

    def send_gga_to_ntrip(self):
        """发送GGA数据到NTRIP服务器"""
        if not self.ntrip_connected or not self.ntrip_socket:
            return
            
        try:
            if self.gga_data and time.time() - self.last_gga_time > 1:  # 每秒发送一次
                self.ntrip_socket.send(self.gga_data.encode('utf-8') + b"\r\n")
                self.last_gga_time = time.time()
                print(f"发送GGA数据到NTRIP服务器: {self.gga_data.strip()}")
        except Exception as e:
            print(f"发送GGA数据失败: {e}")

    def parse_gga_data(self, data):
        """解析GGA数据"""
        if "$GPGGA" in data or "$GNGGA" in data:
            fields = data.split(',')
            
            if len(fields) >= 14:
                try:
                    # 提取关键数据
                    utc_time = fields[1]  # UTC时间
                    latitude = fields[2]  # 纬度
                    lat_dir = fields[3]   # 纬度方向
                    longitude = fields[4] # 经度
                    lon_dir = fields[5]   # 经度方向
                    quality = fields[6]   # 定位质量
                    satellites = fields[7] # 使用的卫星数
                    hdop = fields[8]      # 水平精度因子
                    altitude = fields[9]  # 海拔高度
                    
                    # 格式化纬度和经度
                    if latitude and longitude:
                        lat_deg = int(latitude[:2])
                        lat_min = float(latitude[2:])
                        lat_decimal = lat_deg + lat_min / 60
                        if lat_dir == 'S':
                            lat_decimal = -lat_decimal
                            
                        lon_deg = int(longitude[:3])
                        lon_min = float(longitude[3:])
                        lon_decimal = lon_deg + lon_min / 60
                        if lon_dir == 'W':
                            lon_decimal = -lon_decimal
                    
                        # 保存GGA数据用于发送到NTRIP
                        self.gga_data = data
                        
                        # 保存到CSV文件
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        with open(self.data_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                timestamp,
                                f"{lat_decimal:.8f}" if latitude else "",
                                f"{lon_decimal:.8f}" if longitude else "",
                                altitude,
                                quality,
                                satellites,
                                hdop
                            ])
                        
                        print(f"[{timestamp}] 纬度: {lat_decimal:.8f}, 经度: {lon_decimal:.8f}, 海拔: {altitude}m, 质量: {quality}, 卫星数: {satellites}")
                        return True
                except (ValueError, IndexError) as e:
                    print(f"解析GGA数据出错: {e}")
                    return False
        return False

    def run(self):
        """运行RTK数据采集"""
        print("开始RTK数据采集测试...")
        print("按 Ctrl+C 停止采集")
        
        # 连接串口
        if not self.connect_serial():
            return
            
        # 连接NTRIP
        self.connect_ntrip()
        
        buffer = bytearray()
        try:
            while True:
                # 从串口读取数据
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(data)
                    
                    # 处理完整的行
                    while b'\n' in buffer:
                        line_end = buffer.find(b'\n') + 1
                        line = buffer[:line_end].decode('utf-8', errors='ignore')
                        buffer = buffer[line_end:]
                        
                        # 解析GGA数据
                        if '$GPGGA' in line or '$GNGGA' in line:
                            self.parse_gga_data(line)
                
                # 发送GGA数据到NTRIP服务器
                self.send_gga_to_ntrip()
                
                # 从NTRIP服务器接收RTCM数据并发送到RTK模块
                if self.ntrip_connected and self.ntrip_socket:
                    try:
                        # 根据操作系统选择不同的非阻塞接收方式
                        if sys.platform.startswith('win'):
                            # Windows平台设置socket为非阻塞模式
                            self.ntrip_socket.setblocking(False)
                            try:
                                rtcm_data = self.ntrip_socket.recv(4096)
                            except BlockingIOError:
                                rtcm_data = None
                            finally:
                                # 恢复阻塞模式
                                self.ntrip_socket.setblocking(True)
                        else:
                            # Unix/Linux平台使用MSG_DONTWAIT
                            rtcm_data = self.ntrip_socket.recv(4096, socket.MSG_DONTWAIT)
                        
                        if rtcm_data:
                            self.ser.write(rtcm_data)
                    except BlockingIOError:
                        # 没有数据可读
                        pass
                    except Exception as e:
                        print(f"接收RTCM数据出错: {e}")
                
                time.sleep(0.01)  # 10ms延迟
                
        except KeyboardInterrupt:
            print("\n用户中断，正在停止...")
        except Exception as e:
            print(f"运行时出错: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")
            
        if self.ntrip_socket:
            self.ntrip_socket.close()
            print("NTRIP连接已关闭")
            
        print(f"数据已保存到 {self.data_file}")


if __name__ == "__main__":
    tester = RTKTester()
    tester.run()