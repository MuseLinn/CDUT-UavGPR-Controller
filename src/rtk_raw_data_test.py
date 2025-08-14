#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK原始数据读取测试脚本
用于打印RTK模块输出的原始NMEA数据帧，以便确认数据格式和解析正确性
作者: MuseLinn
日期: 2025-09-17
"""

import serial
import time
import config

class RTKRawDataTest:
    def __init__(self):
        # 从配置文件读取串口设置
        self.port = 'com11'
        self.baudrate = 115200
        self.ser = None
        self.log_file = None
        
    def connect_serial(self):
        """连接RTK串口"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"成功连接到串口 {self.port}")
            return True
        except Exception as e:
            print(f"串口连接失败: {e}")
            return False

    def read_raw_data(self):
        """读取并打印原始数据"""
        print("开始读取RTK原始数据...")
        print("按 Ctrl+C 停止读取")
        print("-" * 50)
        
        # 打开日志文件用于保存原始数据
        log_filename = f"rtk_raw_data_{int(time.time())}.txt"
        self.log_file = open(log_filename, "w", encoding="utf-8")
        print(f"原始数据将保存到文件: {log_filename}")
        
        buffer = b''
        try:
            while True:
                # 从串口读取数据
                if self.ser.in_waiting > 0:
                    new_data = self.ser.read(self.ser.in_waiting)
                    buffer += new_data
                    
                    # 处理完整的行
                    while b'\n' in buffer:
                        line_end = buffer.find(b'\n') + 1
                        line = buffer[:line_end].decode('utf-8', errors='ignore')
                        buffer = buffer[line_end:]
                        
                        # 获取时间戳
                        timestamp = time.time()
                        
                        # 打印原始数据到控制台
                        print(f"[{timestamp:.6f}] {repr(line.strip())}")
                        
                        # 保存原始数据到文件
                        self.log_file.write(f"[{timestamp:.6f}] {line}")
                        self.log_file.flush()  # 确保数据立即写入文件
                        
                        # 检查常见的NMEA语句类型
                        if line.startswith('$'):
                            nmea_type = line.split(',')[0]
                            print(f"  -> 检测到NMEA语句类型: {nmea_type}")
                        elif line.startswith('#'):
                            proprietary_type = line.split(',')[0]
                            print(f"  -> 检测到私有语句类型: {proprietary_type}")
                
                time.sleep(0.01)  # 10ms延迟
                
        except KeyboardInterrupt:
            print("\n用户中断，正在停止...")
        except Exception as e:
            print(f"读取数据时出错: {e}")

    def run(self):
        """运行测试"""
        print("RTK原始数据格式测试")
        print("=" * 50)
        
        # 连接串口
        if not self.connect_serial():
            return
            
        try:
            # 发送配置命令以启用数据输出
            self.ser.write(b'#A GNGGA 1\r\n')
            time.sleep(0.1)
            self.ser.write(b'#A GNRMC 1\r\n')
            time.sleep(0.1)
            # self.ser.write(b'#A GPGSA 1\r\n')
            # time.sleep(0.1)
            # self.ser.write(b'#A GPGSV 1\r\n')
            print("已发送配置命令，启用GNGGA和GNRMC数据输出")
            print("-" * 50)
            
            # 读取数据
            self.read_raw_data()
            
        finally:
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")
            
        if self.log_file:
            self.log_file.close()
            print("日志文件已关闭")

if __name__ == "__main__":
    tester = RTKRawDataTest()
    tester.run()