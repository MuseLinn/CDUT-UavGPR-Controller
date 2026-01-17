# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2026-01-12 22:04:03
LastEditors  : Linn
LastEditTime : 2026-01-13 18:10:00
FilePath     : \\usbvna\\src\\lib\\workers.py
Description  : 数据采集工作线程

Copyright (c) 2026 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

import time
from PyQt6.QtCore import QThread, pyqtSignal

class DataDumpWorker(QThread):
    """工作线程，用于执行数据采集操作，避免阻塞GUI"""
    progress_updated = pyqtSignal(int, int)  # 当前进度, 总数
    finished_signal = pyqtSignal(bool, str)  # 成功与否, 消息
    ascan_data_available = pyqtSignal(object)  # A-Scan数据可用信号

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval, data_acquisition_mode="传统存储方式"):
        super().__init__()
        self.vna_controller = vna_controller
        self.count = count
        self.file_prefix = file_prefix
        self.path = path
        self.data_type = data_type
        self.scope = scope
        self.data_format = data_format
        self.selector = selector
        self.interval = interval
        self.data_acquisition_mode = data_acquisition_mode

    def run(self):
        try:
            # 切换目录
            self.vna_controller.cdir(self.path)

            # 执行数据采集循环
            for i in range(self.count):
                # 根据数据获取方式执行不同的采集逻辑
                if self.data_acquisition_mode == "单CSV存储方式":
                    # 生成文件名，格式为{prefix}_0000001.csv
                    filename = f"{self.file_prefix}_{i + 1:07d}.csv"
                    response = self.vna_controller.data_dump(
                        filename, self.data_type, self.scope, self.data_format, self.selector)

                    if response is None:
                        self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                        return
                    
                    # 尝试读取刚刚存储的数据以用于实时显示
                    try:
                        import numpy as np
                        import csv
                        import os
                        
                        # 读取CSV文件
                        file_path = os.path.join(self.path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            # 跳过前7行标题和元数据
                            for _ in range(7):
                                next(reader)
                            # 读取数据
                            amp_data = []
                            for row in reader:
                                if len(row) >= 2 and row[0] != 'END':
                                    try:
                                        amp = float(row[1])
                                        amp_data.append(amp)
                                    except ValueError:
                                        continue
                            if amp_data:
                                ascan_data = np.array(amp_data)
                                self.ascan_data_available.emit(ascan_data)
                    except Exception as e:
                        # 读取失败不影响采集流程
                        pass
                else:  # 实时数据流方式
                    # 使用新的read_ascan_data方法获取数据
                    import numpy as np
                    import os
                    import csv
                    
                    # 生成主文件名，格式为{prefix}_streaming.csv
                    main_filename = f"{self.file_prefix}_streaming.csv"
                    main_file_path = os.path.join(self.path, main_filename)
                    
                    # 读取A-Scan数据
                    ascan_data = self.vna_controller.read_ascan_data()
                    
                    if ascan_data is None:
                        self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                        return
                    
                    # 发送A-Scan数据信号用于实时显示
                    self.ascan_data_available.emit(ascan_data)
                    
                    # 第一次采集时创建文件并写入表头
                    if i == 0:
                        with open(main_file_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            # 写入表头，第一列为道数，后续为采样点
                            header = ['Trace'] + [f'Sample_{j}' for j in range(len(ascan_data))]
                            writer.writerow(header)
                    
                    # 追加数据到CSV文件
                    with open(main_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # 第一列为道数，后续为采样点数据
                        row_data = [i + 1] + ascan_data.tolist()
                        writer.writerow(row_data)

                # 发送进度更新信号
                self.progress_updated.emit(i + 1, self.count)

                # 间隔延时
                if self.interval > 0:
                    time.sleep(self.interval)

            self.finished_signal.emit(True, f"成功采集{self.count}道数据")
        except Exception as e:
            self.finished_signal.emit(False, f"采集过程中发生错误: {str(e)}")


class ContinuousDumpWorker(QThread):
    """连续数据采集工作线程"""
    progress_updated = pyqtSignal(int)  # 当前次数
    finished_signal = pyqtSignal(bool, str)  # 成功与否的信号
    ascan_data_available = pyqtSignal(object)  # A-Scan数据可用信号

    def __init__(self, vna_controller, file_prefix, path, data_type, scope, data_format, selector, interval, data_acquisition_mode="传统存储方式"):
        super().__init__()
        self.vna_controller = vna_controller
        self.file_prefix = file_prefix
        self.path = path
        self.data_type = data_type
        self.scope = scope
        self.data_format = data_format
        self.selector = selector
        self.interval = interval
        self.data_acquisition_mode = data_acquisition_mode
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        try:
            # 切换目录
            self.vna_controller.cdir(self.path)

            count = 0
            while self.running:
                count += 1
                # 根据数据获取方式执行不同的采集逻辑
                if self.data_acquisition_mode == "单CSV存储方式":
                    # 生成文件名，格式为{prefix}_0000001.csv
                    filename = f"{self.file_prefix}_{count:07d}.csv"
                    response = self.vna_controller.data_dump(
                        filename, self.data_type, self.scope, self.data_format, self.selector)

                    if response is None:
                        self.finished_signal.emit(False, f"数据采集在第{count}次时失败")
                        return
                    
                    # 尝试读取刚刚存储的数据以用于实时显示
                    try:
                        import numpy as np
                        import csv
                        import os
                        
                        # 读取CSV文件
                        file_path = os.path.join(self.path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            # 跳过前7行标题和元数据
                            for _ in range(7):
                                next(reader)
                            # 读取数据
                            amp_data = []
                            for row in reader:
                                if len(row) >= 2 and row[0] != 'END':
                                    try:
                                        amp = float(row[1])
                                        amp_data.append(amp)
                                    except ValueError:
                                        continue
                            if amp_data:
                                ascan_data = np.array(amp_data)
                                self.ascan_data_available.emit(ascan_data)
                    except Exception as e:
                        # 读取失败不影响采集流程
                        pass
                else:  # 实时数据流方式
                    # 使用新的read_ascan_data方法获取数据
                    import numpy as np
                    import os
                    import csv
                    
                    # 生成主文件名，格式为{prefix}_streaming.csv
                    main_filename = f"{self.file_prefix}_streaming.csv"
                    main_file_path = os.path.join(self.path, main_filename)
                    
                    # 读取A-Scan数据
                    ascan_data = self.vna_controller.read_ascan_data()
                    
                    if ascan_data is None:
                        self.finished_signal.emit(False, f"数据采集在第{count}次时失败")
                        return
                    
                    # 发送A-Scan数据信号用于实时显示
                    self.ascan_data_available.emit(ascan_data)
                    
                    # 第一次采集时创建文件并写入表头
                    if count == 1:
                        with open(main_file_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            # 写入表头，第一列为道数，后续为采样点
                            header = ['Trace'] + [f'Sample_{j}' for j in range(len(ascan_data))]
                            writer.writerow(header)
                    
                    # 追加数据到CSV文件
                    with open(main_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # 第一列为道数，后续为采样点数据
                        row_data = [count] + ascan_data.tolist()
                        writer.writerow(row_data)

                # 发送进度更新信号
                self.progress_updated.emit(count)

                # 间隔延时
                if self.interval > 0 and self.running:
                    time.sleep(self.interval)

            self.finished_signal.emit(True, f"成功采集{count}组数据")
        except Exception as e:
            self.finished_signal.emit(False, f"采集过程中发生错误: {str(e)}")


class PointDumpWorker(QThread):
    """点测数据采集工作线程（连续模式）"""
    progress_updated = pyqtSignal(int, int)  # 当前进度, 总数
    finished_signal = pyqtSignal(bool, str)  # 成功与否, 消息
    ascan_data_available = pyqtSignal(object)  # A-Scan数据可用信号

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval, data_acquisition_mode="传统存储方式"):
        super().__init__()
        self.vna_controller = vna_controller
        self.count = count
        self.file_prefix = file_prefix
        self.path = path
        self.data_type = data_type
        self.scope = scope
        self.data_format = data_format
        self.selector = selector
        self.interval = interval
        self.data_acquisition_mode = data_acquisition_mode
        self.running = True  # 添加运行标志

    def stop(self):
        """停止采集"""
        self.running = False

    def run(self):
        try:
            # 切换目录
            self.vna_controller.cdir(self.path)

            # 执行数据采集循环
            for i in range(self.count):
                # 检查是否需要停止
                if not self.running:
                    self.finished_signal.emit(False, "采集被用户中断")
                    return

                # 根据数据获取方式执行不同的采集逻辑
                if self.data_acquisition_mode == "单CSV存储方式":
                    # 生成文件名，格式为{prefix}_0000001.csv
                    filename = f"{self.file_prefix}_{i + 1:07d}.csv"
                    response = self.vna_controller.data_dump(
                        filename, self.data_type, self.scope, self.data_format, self.selector)

                    if response is None:
                        self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                        return
                    
                    # 尝试读取刚刚存储的数据以用于实时显示
                    try:
                        import numpy as np
                        import csv
                        import os
                        
                        # 读取CSV文件
                        file_path = os.path.join(self.path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            # 跳过前7行标题和元数据
                            for _ in range(7):
                                next(reader)
                            # 读取数据
                            amp_data = []
                            for row in reader:
                                if len(row) >= 2 and row[0] != 'END':
                                    try:
                                        amp = float(row[1])
                                        amp_data.append(amp)
                                    except ValueError:
                                        continue
                            if amp_data:
                                ascan_data = np.array(amp_data)
                                self.ascan_data_available.emit(ascan_data)
                    except Exception as e:
                        # 读取失败不影响采集流程
                        pass
                else:  # 实时数据流方式
                    # 使用新的read_ascan_data方法获取数据
                    import numpy as np
                    import os
                    import csv
                    
                    # 生成主文件名，格式为{prefix}_streaming.csv
                    main_filename = f"{self.file_prefix}_streaming.csv"
                    main_file_path = os.path.join(self.path, main_filename)
                    
                    # 读取A-Scan数据
                    ascan_data = self.vna_controller.read_ascan_data()
                    
                    if ascan_data is None:
                        self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                        return
                    
                    # 发送A-Scan数据信号用于实时显示
                    self.ascan_data_available.emit(ascan_data)
                    
                    # 第一次采集时创建文件并写入表头
                    if i == 0:
                        with open(main_file_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            # 写入表头，第一列为道数，后续为采样点
                            header = ['Trace'] + [f'Sample_{j}' for j in range(len(ascan_data))]
                            writer.writerow(header)
                    
                    # 追加数据到CSV文件
                    with open(main_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # 第一列为道数，后续为采样点数据
                        row_data = [i + 1] + ascan_data.tolist()
                        writer.writerow(row_data)

                # 发送进度更新信号
                self.progress_updated.emit(i + 1, self.count)

                # 间隔延时
                if self.interval > 0 and self.running:
                    time.sleep(self.interval)

            self.finished_signal.emit(True, f"成功采集{self.count}道数据")
        except Exception as e:
            self.finished_signal.emit(False, f"采集过程中发生错误: {str(e)}")


class SinglePointDumpWorker(QThread):
    """单次点测数据采集工作线程"""
    progress_updated = pyqtSignal(int, int)  # 当前进度, 总数
    finished_signal = pyqtSignal(bool, str)  # 成功与否, 消息
    ascan_data_available = pyqtSignal(object)  # A-Scan数据可用信号

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval,
                 start_index, data_acquisition_mode="传统存储方式"):
        super().__init__()
        self.vna_controller = vna_controller
        self.count = count
        self.file_prefix = file_prefix
        self.path = path
        self.data_type = data_type
        self.scope = scope
        self.data_format = data_format
        self.selector = selector
        self.interval = interval
        self.start_index = start_index
        self.data_acquisition_mode = data_acquisition_mode

    def run(self):
        try:
            # 切换目录
            self.vna_controller.cdir(self.path)

            # 执行数据采集循环
            for i in range(self.count):
                # 根据数据获取方式执行不同的采集逻辑
                if self.data_acquisition_mode == "单CSV存储方式":
                    # 生成文件名，格式为{prefix}_{index:08d}.csv
                    filename = f"{self.file_prefix}_{self.start_index + i:08d}.csv"

                    response = self.vna_controller.data_dump(
                        filename, self.data_type, self.scope, self.data_format, self.selector)

                    if response is None:
                        self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                        return
                    
                    # 尝试读取刚刚存储的数据以用于实时显示
                    try:
                        import numpy as np
                        import csv
                        import os
                        
                        # 读取CSV文件
                        file_path = os.path.join(self.path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            # 跳过前7行标题和元数据
                            for _ in range(7):
                                next(reader)
                            # 读取数据
                            amp_data = []
                            for row in reader:
                                if len(row) >= 2 and row[0] != 'END':
                                    try:
                                        amp = float(row[1])
                                        amp_data.append(amp)
                                    except ValueError:
                                        continue
                            if amp_data:
                                ascan_data = np.array(amp_data)
                                self.ascan_data_available.emit(ascan_data)
                    except Exception as e:
                        # 读取失败不影响采集流程
                        pass
                else:  # 实时数据流方式
                    # 使用新的read_ascan_data方法获取数据
                    import numpy as np
                    import os
                    import csv
                    
                    # 生成主文件名，格式为{prefix}_streaming.csv
                    main_filename = f"{self.file_prefix}_streaming.csv"
                    main_file_path = os.path.join(self.path, main_filename)
                    
                    # 读取A-Scan数据
                    ascan_data = self.vna_controller.read_ascan_data()
                    
                    if ascan_data is None:
                        self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                        return
                    
                    # 发送A-Scan数据信号用于实时显示
                    self.ascan_data_available.emit(ascan_data)
                    
                    # 第一次采集时创建文件并写入表头
                    if i == 0:
                        with open(main_file_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            # 写入表头，第一列为道数，后续为采样点
                            header = ['Trace'] + [f'Sample_{j}' for j in range(len(ascan_data))]
                            writer.writerow(header)
                    
                    # 追加数据到CSV文件
                    with open(main_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # 第一列为道数，后续为采样点数据
                        row_data = [self.start_index + i + 1] + ascan_data.tolist()
                        writer.writerow(row_data)

                # 发送进度更新信号
                self.progress_updated.emit(i + 1, self.count)

                # 间隔延时
                if self.interval > 0:
                    time.sleep(self.interval)

            self.finished_signal.emit(True, f"成功采集{self.count}组数据")
        except Exception as e:
            self.finished_signal.emit(False, f"采集过程中发生错误: {str(e)}")
