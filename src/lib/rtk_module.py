#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK模块处理类（优化版）
用于处理RTK模块的数据读取、解析和存储，采用乒乓缓存机制优化性能
作者: Linn
日期: 2025-09-18
"""

import serial
import time
import csv
import threading
import re
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from queue import Queue, Empty
import collections


class RTKModule(QObject):
    """RTK模块处理类（优化版）"""

    # 定义信号，用于向GUI发送数据
    rtk_data_updated = pyqtSignal(dict)  # 发送解析后的RTK数据
    rtk_error_occurred = pyqtSignal(str)  # 发送错误信息
    rtk_module_info_received = pyqtSignal(dict)  # 发送模块信息

    # 常用波特率列表
    BAUDRATES = [4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

    def __init__(self, port="COM11", baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.buffer = b''
        self.running = False
        self.read_thread = None
        self.write_thread = None
        self.storage_frequency = 1  # 存储频率(Hz)
        self.data_file = None
        self.csv_writer = None
        # 添加串口参数默认值
        self.bytesize = serial.EIGHTBITS
        self.stopbits = serial.STOPBITS_ONE
        self.parity = serial.PARITY_NONE
        self.module_info = {}  # 存储模块信息
        
        # 添加存储控制选项
        self.store_location_data = True  # 控制是否存储位置数据（经纬度）
        self.store_altitude_data = True  # 控制是否存储海拔数据
        
        # 简化缓存机制
        self.data_queue = Queue(maxsize=1000)  # 限制队列大小防止内存溢出
        self.cache_buffer = collections.deque()
        self.buffer_lock = threading.Lock()
        
        # 控制标志
        self.writing_enabled = False

    def connect(self):
        """连接RTK模块"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                stopbits=self.stopbits,
                parity=self.parity,
                timeout=0.1  # 减少超时时间
            )

            # 获取模块信息
            self.get_module_info()
            time.sleep(0.1)
            
            # 先发送停止所有输出的命令
            self.ser.write(b'UNLOG\r\n')
            time.sleep(0.1)
            # 发送配置命令
            self.ser.write(b'#A GNGGA 0.1\r\n')   # 启用GNGGA数据，10Hz频率
            time.sleep(0.1)
            self.ser.write(b'#A GNRMC 0.1\r\n')   # 启用GNRMC数据，10Hz频率
            time.sleep(0.1)
            self.ser.write(b'#A GPGSA 1\r\n')     # 启用GPGSA数据，1Hz频率
            time.sleep(0.1)
            self.ser.write(b'MODE ROVER\r\n')     # 设置流动站模式
            time.sleep(0.1)
            self.ser.write(b'SAVECONFIG\r\n')     # 保存配置
            time.sleep(0.1)

            return True
        except Exception as e:
            self.rtk_error_occurred.emit(f"RTK模块连接失败: {str(e)}")
            return False

    def get_module_info(self):
        """获取RTK模块信息"""
        try:
            # 发送VERSIONA命令
            self.ser.write(b'VERSIONA\r\n')
            time.sleep(0.05)  # 减少等待时间

            # 读取响应数据
            buffer = b''
            start_time = time.time()

            # 等待最多1秒的响应数据
            while time.time() - start_time < 1:
                if self.ser.in_waiting > 0:
                    new_data = self.ser.read(self.ser.in_waiting)
                    buffer += new_data

                    # 检查是否收到完整的行
                    while b'\n' in buffer:
                        line_end = buffer.find(b'\n') + 1
                        line = buffer[:line_end].decode('utf-8', errors='ignore')
                        buffer = buffer[line_end:]

                        # 检查是否是VERSIONA响应
                        if '#VERSIONA' in line:
                            self.parse_versiona_data(line.strip())
                            return

                time.sleep(0.005)  # 减少等待时间

            self.rtk_error_occurred.emit("未收到RTK模块的VERSIONA响应")
        except Exception as e:
            self.rtk_error_occurred.emit(f"获取RTK模块信息时出错: {str(e)}")

    def parse_versiona_data(self, data):
        """解析VERSIONA数据，只提取已知信息"""
        try:
            # 移除行尾的换行符和回车符
            data = data.strip()

            # 解析数据
            # 格式: #VERSIONA,86,GPS,FINE,2384,308534000,0,0,18,21;"UM982","R4.10Build11826","HRPT00-S10C-P","2310415000012-LR23A1224521473","ff3be298a90a76fb","2023/11/24"*fa882d29
            if data.startswith('#VERSIONA,'):
                # 分离校验和部分
                if '*' in data:
                    data_parts = data.split('*')
                    versiona_data = data_parts[0]
                else:
                    versiona_data = data

                # 查找引号内的模块型号和固件版本
                quoted_parts = versiona_data.split('"')
                info_parts = [part for i, part in enumerate(quoted_parts) if i % 2 == 1]

                # 提取已知信息
                if len(info_parts) >= 2:
                    self.module_info['model'] = info_parts[0]
                    self.module_info['firmware'] = info_parts[1]
                    # 发送模块信息信号
                    self.rtk_module_info_received.emit(self.module_info)
        except Exception as e:
            self.rtk_error_occurred.emit(f"解析VERSIONA数据时出错: {str(e)}")

    def disconnect(self):
        """断开RTK模块连接"""
        self.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None

    def start(self):
        """开始读取RTK数据"""
        if not self.ser or not self.ser.is_open:
            if not self.connect():
                return False

        self.running = True
        self.writing_enabled = (self.data_file is not None)
        
        # 启动读取线程
        self.read_thread = threading.Thread(target=self._read_data, daemon=True)
        self.read_thread.start()
        
        # 启动写入线程（如果需要存储数据）
        if self.writing_enabled:
            self.write_thread = threading.Thread(target=self._write_data, daemon=True)
            self.write_thread.start()
            
        return True

    def stop(self):
        """停止读取RTK数据"""
        self.running = False
        
        # 等待读取线程结束
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)  # 设置超时避免无限等待
            
        # 等待写入线程结束
        if self.write_thread and self.write_thread.is_alive():
            self.write_thread.join(timeout=2.0)
            
        # 确保所有缓存数据都被写入
        if self.writing_enabled:
            self._flush_remaining_data()  # 写入剩余数据

    def set_storage_frequency(self, frequency):
        """设置数据存储频率"""
        self.storage_frequency = frequency
        # 发送命令设置RTK模块输出频率
        if self.ser and self.ser.is_open:
            frequency_commands = {
                1: b'#A GNGGA 1\r\n',
                2: b'#A GNGGA 0.5\r\n',
                5: b'#A GNGGA 0.2\r\n',
                10: b'#A GNGGA 0.1\r\n',
                20: b'#A GNGGA 0.05\r\n'
            }

            command = frequency_commands.get(frequency, b'#A GNGGA 1\r\n')
            self.ser.write(command)

    def set_data_file(self, filename):
        """设置数据存储文件"""
        try:
            self.data_file = open(filename, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.data_file)
            # 写入表头
            self.csv_writer.writerow([
                'timestamp', 'gps_time', 'latitude', 'longitude', 'altitude',
                'quality', 'satellites', 'hdop', 'speed', 'direction'
            ])
            self.writing_enabled = True
        except Exception as e:
            self.rtk_error_occurred.emit(f"创建数据文件失败: {str(e)}")

    def close_data_file(self):
        """关闭数据文件"""
        self.writing_enabled = False
        if self.data_file:
            self.data_file.close()
            self.data_file = None
            self.csv_writer = None

    def set_location_storage(self, enabled):
        """设置是否存储位置数据（经纬度）"""
        self.store_location_data = enabled

    def set_altitude_storage(self, enabled):
        """设置是否存储海拔数据"""
        self.store_altitude_data = enabled

    def _read_data(self):
        """读取RTK数据的线程函数"""
        while self.running:
            try:
                # 使用非阻塞方式读取数据，减少延迟
                if self.ser.in_waiting > 0:
                    new_data = self.ser.read(min(self.ser.in_waiting, 4096))  # 限制单次读取量
                    self.buffer += new_data

                    # 处理完整的行
                    while b'\n' in self.buffer and self.running:
                        line_end = self.buffer.find(b'\n') + 1
                        line = self.buffer[:line_end].decode('utf-8', errors='ignore')
                        self.buffer = self.buffer[line_end:]

                        # 解析数据
                        parsed_data = self._parse_nmea_data(line.strip())
                        if parsed_data:
                            # 立即发送数据更新信号
                            try:
                                self.rtk_data_updated.emit(parsed_data)
                            except Exception as e:
                                self.rtk_error_occurred.emit(f"发送RTK数据信号时出错: {str(e)}")

                            # 存储数据到缓存队列
                            if self.writing_enabled:
                                try:
                                    self.data_queue.put(parsed_data, block=False)
                                except:
                                    # 队列满时丢弃旧数据
                                    try:
                                        self.data_queue.get_nowait()
                                        self.data_queue.put(parsed_data, block=False)
                                    except:
                                        pass

                # 控制读取频率，避免CPU占用过高
                time.sleep(0.005)  # 5ms延迟，之前是1ms，稍微增加以减少CPU占用
                
            except Exception as e:
                self.rtk_error_occurred.emit(f"读取RTK数据时出错: {str(e)}")
                time.sleep(0.1)  # 出错时增加延迟避免快速重试

    def _write_data(self):
        """写入数据到文件的线程函数"""
        while self.running:
            try:
                # 从队列中获取数据
                data_written = False
                while not self.data_queue.empty():
                    try:
                        data = self.data_queue.get_nowait()
                        # 添加到缓存
                        with self.buffer_lock:
                            self.cache_buffer.append(data)
                            
                        # 如果缓存达到一定大小，写入文件
                        if len(self.cache_buffer) >= 50:
                            self._flush_buffer_to_file()
                            data_written = True
                    except Empty:
                        break
                
                # 定期写入数据以确保及时存储
                if not data_written:
                    self._flush_buffer_to_file()
                
                time.sleep(0.01)  # 10ms延迟
                
            except Exception as e:
                self.rtk_error_occurred.emit(f"写入RTK数据时出错: {str(e)}")
                time.sleep(0.1)

    def _flush_buffer_to_file(self):
        """将缓存数据刷新到文件"""
        if not self.csv_writer:
            return
            
        try:
            # 写入缓存中的所有数据
            with self.buffer_lock:
                while self.cache_buffer:
                    data = self.cache_buffer.popleft()
                    self._save_to_csv(data)
                
            # 强制刷新文件
            if self.data_file:
                self.data_file.flush()
        except Exception as e:
            self.rtk_error_occurred.emit(f"刷新数据到文件时出错: {str(e)}")

    def _flush_remaining_data(self):
        """刷新剩余数据"""
        # 确保所有队列中的数据都被处理
        while not self.data_queue.empty():
            try:
                data = self.data_queue.get_nowait()
                with self.buffer_lock:
                    self.cache_buffer.append(data)
            except Empty:
                break
                
        # 写入所有缓存数据
        self._flush_buffer_to_file()

    def _parse_nmea_data(self, line):
        """解析NMEA数据"""
        try:
            # 解析GNGGA数据
            if line.startswith('$GNGGA') or line.startswith('$GPGGA'):
                return self._parse_gga_data(line)
            # 解析GNRMC数据
            elif line.startswith('$GNRMC') or line.startswith('$GPRMC'):
                return self._parse_rmc_data(line)
            # 解析GPGSA数据
            elif line.startswith('$GPGSA'):
                return self._parse_gsa_data(line)
        except Exception as e:
            self.rtk_error_occurred.emit(f"解析NMEA数据时出错: {str(e)}")
        return None

    def _parse_gga_data(self, line):
        """解析GGA数据"""
        fields = line.split(',')
        if len(fields) < 15:
            return None

        try:
            data = {
                'type': 'GGA',
                'utc_time': fields[1],  # UTC时间
                'latitude': self._convert_to_decimal(fields[2], fields[3]),  # 纬度
                'longitude': self._convert_to_decimal(fields[4], fields[5]),  # 经度
                'quality': fields[6],  # 定位质量
                'satellites': fields[7],  # 使用的卫星数
                'hdop': fields[8],  # 水平精度因子
                'altitude': fields[9],  # 海拔高度
                'timestamp': time.time()  # 系统时间戳
            }
            return data
        except Exception:
            return None

    def _parse_rmc_data(self, line):
        """解析RMC数据"""
        fields = line.split(',')
        if len(fields) < 12:
            return None

        try:
            # 解析日期和时间
            date_str = fields[9]  # ddmmyy
            time_str = fields[1]  # hhmmss.ss

            data = {
                'type': 'RMC',
                'utc_time': time_str,  # UTC时间
                'status': fields[2],  # 状态
                'latitude': self._convert_to_decimal(fields[3], fields[4]),  # 纬度
                'longitude': self._convert_to_decimal(fields[5], fields[6]),  # 经度
                'speed': fields[7],  # 速度
                'direction': fields[8],  # 航向
                'date': date_str,  # 日期
                'timestamp': time.time()  # 系统时间戳
            }

            # 如果时间和日期都有效，计算GPS时间戳
            if time_str and date_str and len(time_str) >= 6 and len(date_str) == 6:
                try:
                    # 解析日期 (ddmmyy -> yyyy-mm-dd)
                    day = int(date_str[0:2])
                    month = int(date_str[2:4])
                    year = 2000 + int(date_str[4:6])  # 假设都是20xx年

                    # 解析时间 (hhmmss.ss -> hh:mm:ss)
                    hour = int(time_str[0:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])

                    # 构造GPS时间字符串
                    gps_time_str = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
                    data['gps_timestamp'] = gps_time_str
                except Exception:
                    pass

            return data
        except Exception:
            return None

    def _parse_gsa_data(self, line):
        """解析GSA数据"""
        fields = line.split(',')
        # GSA语句至少需要18个字段（包括校验和）
        if len(fields) < 18:
            return None

        try:
            # 提取VDOP并移除可能存在的校验和标识符
            vdop_field = fields[17]
            if '*' in vdop_field:
                vdop_field = vdop_field.split('*')[0]

            data = {
                'type': 'GSA',
                'mode': fields[1] if len(fields) > 1 else '',  # 模式(M=手动, A=自动)
                'fix_type': fields[2] if len(fields) > 2 else '',  # 定位类型(1=未定位, 2=2D定位, 3=3D定位)
                'satellites': [prn for prn in fields[3:15] if prn.strip()],  # 使用的卫星PRN号列表（过滤空值）
                'pdop': fields[15] if len(fields) > 15 else '',  # 位置精度因子
                'hdop': fields[16] if len(fields) > 16 else '',  # 水平精度因子
                'vdop': vdop_field if vdop_field else '',  # 垂直精度因子(去除校验和部分)
                'timestamp': time.time()  # 系统时间戳
            }
            return data
        except Exception as e:
            self.rtk_error_occurred.emit(f"解析GSA数据时出错: {str(e)}")
            return None

    def _convert_to_decimal(self, coordinate, direction):
        """将NMEA坐标格式转换为十进制格式"""
        if not coordinate or not direction:
            return ""

        try:
            # 分割度和分
            if '.' in coordinate:
                dot_index = coordinate.index('.')
                if dot_index >= 3:  # 经度格式 (dddmm.mmmm)
                    degrees = int(coordinate[:dot_index-2])
                    minutes = float(coordinate[dot_index-2:])
                else:  # 纬度格式 (ddmm.mmmm)
                    degrees = int(coordinate[:dot_index-2])
                    minutes = float(coordinate[dot_index-2:])

                decimal_degrees = degrees + minutes / 60

                # 根据方向调整正负号
                if direction in ['S', 'W']:
                    decimal_degrees = -decimal_degrees

                return f"{decimal_degrees:.8f}"
            return ""
        except Exception:
            return ""

    def _save_to_csv(self, data):
        """保存数据到CSV文件"""
        try:
            if data['type'] == 'GGA':
                # 根据设置决定是否存储位置和海拔数据
                latitude = data.get('latitude', '') if self.store_location_data else ''
                longitude = data.get('longitude', '') if self.store_location_data else ''
                altitude = data.get('altitude', '') if self.store_altitude_data else ''
                
                self.csv_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # 系统时间戳
                    data.get('utc_time', ''),  # GPS时间
                    latitude,  # 纬度
                    longitude,  # 经度
                    altitude,  # 海拔
                    data.get('quality', ''),  # 定位质量
                    data.get('satellites', ''),  # 卫星数
                    data.get('hdop', ''),  # HDOP
                    '',  # 速度 (GGA中没有)
                    ''   # 方向 (GGA中没有)
                ])
            elif data['type'] == 'RMC':
                # 根据设置决定是否存储位置数据
                latitude = data.get('latitude', '') if self.store_location_data else ''
                longitude = data.get('longitude', '') if self.store_location_data else ''
                
                self.csv_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # 系统时间戳
                    data.get('utc_time', ''),  # GPS时间
                    latitude,  # 纬度
                    longitude,  # 经度
                    '',  # 海拔 (RMC中没有)
                    '',  # 定位质量 (RMC中没有)
                    '',  # 卫星数 (RMC中没有)
                    '',  # HDOP (RMC中没有)
                    data.get('speed', ''),  # 速度
                    data.get('direction', '')  # 方向
                ])
        except Exception as e:
            self.rtk_error_occurred.emit(f"保存数据到CSV文件时出错: {str(e)}")

    @staticmethod
    def list_available_ports():
        """列出所有可用的串口"""
        import serial.tools.list_ports
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports

    @staticmethod
    def get_baudrates():
        """获取支持的波特率列表"""
        return RTKModule.BAUDRATES