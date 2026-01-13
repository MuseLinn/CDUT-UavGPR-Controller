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

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval):
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

    def run(self):
        try:
            # 切换目录
            self.vna_controller.cdir(self.path)

            # 执行数据采集循环
            for i in range(self.count):
                # 生成文件名，格式为{prefix}_0000001.csv
                filename = f"{self.file_prefix}_{i + 1:07d}.csv"
                response = self.vna_controller.data_dump(
                    filename, self.data_type, self.scope, self.data_format, self.selector)

                if response is None:
                    self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                    return

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

    def __init__(self, vna_controller, file_prefix, path, data_type, scope, data_format, selector, interval):
        super().__init__()
        self.vna_controller = vna_controller
        self.file_prefix = file_prefix
        self.path = path
        self.data_type = data_type
        self.scope = scope
        self.data_format = data_format
        self.selector = selector
        self.interval = interval
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
                # 生成文件名，格式为{prefix}_0000001.csv
                filename = f"{self.file_prefix}_{count:07d}.csv"
                response = self.vna_controller.data_dump(
                    filename, self.data_type, self.scope, self.data_format, self.selector)

                if response is None:
                    self.finished_signal.emit(False, f"数据采集在第{count}次时失败")
                    return

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

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval):
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

                # 生成文件名，格式为{prefix}_0000001.csv
                filename = f"{self.file_prefix}_{i + 1:07d}.csv"
                response = self.vna_controller.data_dump(
                    filename, self.data_type, self.scope, self.data_format, self.selector)

                if response is None:
                    self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                    return

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

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval,
                 start_index):
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

    def run(self):
        try:
            # 切换目录
            self.vna_controller.cdir(self.path)

            # 执行数据采集循环
            for i in range(self.count):
                # 生成文件名，格式为{prefix}_{index:08d}.csv
                filename = f"{self.file_prefix}_{self.start_index + i:08d}.csv"

                response = self.vna_controller.data_dump(
                    filename, self.data_type, self.scope, self.data_format, self.selector)

                if response is None:
                    self.finished_signal.emit(False, f"数据采集在第{i + 1}次时失败")
                    return

                # 发送进度更新信号
                self.progress_updated.emit(i + 1, self.count)

                # 间隔延时
                if self.interval > 0:
                    time.sleep(self.interval)

            self.finished_signal.emit(True, f"成功采集{self.count}组数据")
        except Exception as e:
            self.finished_signal.emit(False, f"采集过程中发生错误: {str(e)}")
