#!/usr/bin/env python
# coding: utf-8

# # 矢网仪A-Scan时域波形读取测试
# 
# 本示例展示如何使用SCPI指令直接读取VNA显示的时域A-Scan数据，并绘制验证

# 导入必要的库
import pyvisa as visa
import numpy as np
import time
import csv

# 导入pyqtgraph和Qt，用于高效的实时B-Scan绘制
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import sys

# 设置pyqtgraph全局主题为浅色
pg.setConfigOption('background', 'w')  # 设置背景为白色
pg.setConfigOption('foreground', 'k')  # 设置前景（文字等）为黑色

DEBUG = False  # 简化调试信息，仅保留关键信息
def debug_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)


# ## 1. 矢网仪控制器类


class SimpleVNAController:
    """
    简化版矢网仪控制器类，仅用于读取A-Scan时域数据
    """
    def __init__(self):
        self.rm = None
        self.vna = None
        self.current_channel = 1
        self.current_measurement = 1
        
        try:
            self.rm = visa.ResourceManager()
            debug_print("VISA资源管理器初始化成功")
        except Exception as e:
            debug_print(f"VISA资源管理器初始化失败: {e}")
            self.rm = None

    def list_devices(self):
        """列出所有连接的VISA设备"""
        if not self.rm:
            debug_print("资源管理器未初始化")
            return []
        try:
            resources = self.rm.list_resources()
            debug_print(f"发现设备: {resources}")
            return resources
        except Exception as e:
            debug_print(f"列出设备失败: {e}")
            return []

    def open_device(self, resource_name, timeout=30000):
        """打开VISA设备"""
        if not self.rm:
            debug_print("资源管理器未初始化")
            return False
        
        try:
            debug_print(f"正在打开设备: {resource_name}")
            self.close_device()  # 确保之前的连接已关闭
            self.vna = self.rm.open_resource(resource_name)
            self.vna.timeout = timeout  # 增加超时时间到30秒
            self.vna.write_termination = '\n'
            self.vna.read_termination = '\n'
            
            # 检查设备ID
            idn = self.query("*IDN?")
            debug_print(f"设备ID: {idn}")
            
            # 设置数据格式为二进制
            self.write("FORM:DATA REAL,32")  # 32位浮点数
            self.write("FORM:BORD NORM")     # 正常字节顺序
            
            return True
        except Exception as e:
            debug_print(f"打开设备失败: {e}")
            self.vna = None
            return False

    def close_device(self):
        """关闭VISA设备"""
        if self.vna:
            try:
                self.vna.close()
                debug_print("设备已关闭")
            except Exception as e:
                debug_print(f"关闭设备失败: {e}")
            finally:
                self.vna = None

    def write(self, command):
        """发送命令到设备"""
        if not self.vna:
            debug_print("设备未连接")
            return False
        try:
            self.vna.write(command)
            return True
        except Exception as e:
            debug_print(f"发送命令失败: {e}")
            return False

    def query(self, command):
        """发送查询命令并返回响应"""
        if not self.vna:
            debug_print("设备未连接")
            return None
        try:
            return self.vna.query(command).strip()
        except Exception as e:
            debug_print(f"查询失败: {e}")
            return None

    def read_ascan_data(self):
        """直接读取VNA显示的A-Scan时域数据
        使用CALC:MEAS:DATA:FDATA?获取显示的时域数据
        采用ASCII格式以确保可靠的数据解析
        """
        if not self.vna:
            debug_print("设备未连接")
            return None
        
        try:
            # 设置数据格式为ASCII
            self.write("FORM:DATA ASCII")
            
            # 使用FDATA获取显示的时域数据
            start_time = time.time()
            command = f"CALC{self.current_channel}:MEAS{self.current_measurement}:DATA:FDATA?"
            ascii_data = self.query(command)
            read_time = time.time() - start_time
            
            # 解析ASCII数据
            if ascii_data:
                # 分割数据并转换为浮点数
                data_points = ascii_data.split(',')
                float_data = [float(point) for point in data_points if point.strip()]
                np_data = np.array(float_data)
                
                debug_print(f"读取A-Scan时域数据完成，耗时: {read_time:.3f}秒, 数据点: {len(np_data)}")
                return np_data
            
            return None
        except Exception as e:
            debug_print(f"读取A-Scan数据失败: {e}")
            return None


# ## 2. 数据可视化工具
class SimpleVisualizer:
    """
    简化版数据可视化类，提供A-Scan时域波形绘制和实时B-Scan绘制功能
    """
    @staticmethod
    def plot_ascan_time_domain(data, time_range_ns=900, title='A-Scan时域波形'):
        """绘制A-Scan时域波形
        参数：
        - data: A-Scan数据数组
        - time_range_ns: 时间范围（纳秒），默认900ns
        - title: 图像标题
        """
        # 创建时间数组，从0到time_range_ns均匀分布
        time_array = np.linspace(0, time_range_ns, len(data))
        
        # 创建pyqtgraph窗口
        win = pg.GraphicsLayoutWidget(show=True, title=title)
        win.resize(800, 600)
        
        # 添加绘图项
        plot = win.addPlot(title="时域波形")
        plot.plot(time_array, data, pen='b', lineWidth=1.5)
        
        # 设置坐标轴
        plot.setLabel('bottom', '时间', 'ns')
        plot.setLabel('left', '幅度')
        plot.setXRange(0, time_range_ns)
        plot.grid(True)

class AcquisitionThread(QtCore.QThread):
    """
    数据采集线程，负责在后台读取A-Scan数据
    """
    # 定义信号
    new_data = QtCore.pyqtSignal(np.ndarray)  # 新数据信号
    progress = QtCore.pyqtSignal(int, int)  # 进度信号 (当前, 总数)
    finished = QtCore.pyqtSignal()  # 完成信号
    
    def __init__(self, vna_controller, num_traces=500, acquisition_period_ms=80):
        """
        初始化采集线程
        参数：
        - vna_controller: VNA控制器实例
        - num_traces: 采集的A-Scan道数
        - acquisition_period_ms: 采集周期（毫秒）
        """
        super().__init__()
        self.vna_controller = vna_controller
        self.num_traces = num_traces
        self.acquisition_period_ms = acquisition_period_ms
        self.is_running = False
    
    def run(self):
        """线程运行函数"""
        self.is_running = True
        
        for i in range(self.num_traces):
            if not self.is_running:
                break
            
            # 读取A-Scan数据
            start_time = time.time()
            ascan_data = self.vna_controller.read_ascan_data()
            read_time = time.time() - start_time
            
            if ascan_data is not None:
                # 发送新数据信号
                self.new_data.emit(ascan_data)
                
                # 发送进度信号
                if (i + 1) % 50 == 0:
                    self.progress.emit(i + 1, self.num_traces)
            
            # 控制采集周期
            elapsed = time.time() - start_time
            wait_time = self.acquisition_period_ms / 1000 - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
        
        # 发送完成信号
        self.finished.emit()
    
    def stop(self):
        """停止采集"""
        self.is_running = False

class RealTimeBScanPlotter:
    """
    实时B-Scan绘制类，用于以指定周期采集A-Scan并实时绘制B-Scan
    使用多线程分离数据采集和GUI绘制，确保窗口响应
    """
    def __init__(self, vna_controller, num_traces=500, acquisition_period_ms=80):
        """
        初始化实时B-Scan绘制器
        参数：
        - vna_controller: VNA控制器实例
        - num_traces: 采集的A-Scan道数
        - acquisition_period_ms: 采集周期（毫秒）
        """
        self.vna_controller = vna_controller
        self.num_traces = num_traces
        self.acquisition_period_ms = acquisition_period_ms
        self.bscan_data = []
        self.is_running = False
        
        # 创建pyqtgraph窗口
        self.win = pg.GraphicsLayoutWidget(show=True, title=f'实时B-Scan图像 ({num_traces}道)')
        self.win.resize(1200, 800)
        
        # 添加绘图区域
        self.plot = self.win.addPlot(title=f'实时B-Scan图像')
        
        # 设置坐标轴标签
        self.plot.setLabel('bottom', '道数')
        self.plot.setLabel('left', '采样点')
        
        # 创建图像项
        self.img = pg.ImageItem(axisOrder='row-major')
        self.plot.addItem(self.img)
        
        # 设置坐标轴方向，Y轴从上往下表示深度增加（时深关系）
        self.plot.invertY(True)
        
        # 使用matplotlib的seismic颜色映射
        cmap = pg.colormap.getFromMatplotlib('seismic')
        
        # 创建颜色条，确保颜色映射和标签正确
        self.cbar = pg.ColorBarItem(
            values=(0, 1),  # 初始范围，将在数据更新时调整
            width=30,       # 颜色条宽度
            colorMap=cmap,  # 使用seismic颜色映射
            label='幅度'
        )
        # 正确关联颜色条与图像项
        self.cbar.setImageItem(self.img)
        # 将颜色条添加到布局中
        self.win.addItem(self.cbar, row=0, col=1)
        
        # 禁用自动范围调整，避免图像闪烁
        self.plot.disableAutoRange()
        
        # 连接关闭事件
        self.win.closeEvent = self.close_event
        
        # 创建采集线程
        self.acquisition_thread = AcquisitionThread(
            vna_controller, 
            num_traces=num_traces, 
            acquisition_period_ms=acquisition_period_ms
        )
        
        # 连接信号槽
        self.acquisition_thread.new_data.connect(self.update_bscan)
        self.acquisition_thread.progress.connect(self.on_progress)
        self.acquisition_thread.finished.connect(self.on_finished)
        
    def close_event(self, event):
        """窗口关闭事件处理"""
        self.stop()
        event.accept()
    
    def on_progress(self, current, total):
        """进度更新处理"""
        print(f"  已完成 {current}/{total} 道")
    
    def update_bscan(self, ascan_data):
        """
        更新B-Scan图像
        参数：
        - ascan_data: 新的A-Scan数据
        """
        # 添加到B-Scan数据
        self.bscan_data.append(ascan_data)
        
        # 转换为numpy数组，形状为 (num_traces, num_samples)
        bscan_array = np.array(self.bscan_data)
        
        # 转置数据，使其形状变为 (num_samples, num_traces)
        # 这样Y轴显示采样点，X轴显示道数
        bscan_array_transposed = bscan_array.T
        
        # 更新图像数据，确保显示正确
        self.img.setImage(bscan_array_transposed, axisOrder='row-major')
        
        # 调整图像大小以匹配当前数据
        self.img.setRect(QtCore.QRectF(0, 0, bscan_array_transposed.shape[1], bscan_array_transposed.shape[0]))
        
        # 仅更新颜色条范围，避免冗余的颜色映射设置
        min_val = np.min(bscan_array_transposed)
        max_val = np.max(bscan_array_transposed)
        self.cbar.setLevels((min_val, max_val))
        
        # 更新坐标轴范围，确保X轴显示道数，Y轴显示采样点
        self.plot.setXRange(0, bscan_array_transposed.shape[1])
        self.plot.setYRange(0, bscan_array_transposed.shape[0])
    
    def on_finished(self):
        """采集完成处理"""
        self.is_running = False
        
        # 计算性能指标
        total_time = time.time() - self.start_total
        read_rate = len(self.bscan_data) / total_time if total_time > 0 else 0
        
        print(f"\n=== 实时B-Scan采集测试结果 ===")
        print(f"总道数: {self.num_traces}")
        print(f"成功道数: {len(self.bscan_data)}")
        print(f"总耗时: {total_time:.3f}秒")
        print(f"读取速率: {read_rate:.2f}道/秒")
        print(f"期望速率: {1000/self.acquisition_period_ms:.2f}道/秒")
        print(f"是否满足期望速率: {'是' if read_rate >= 1000/self.acquisition_period_ms else '否'}")
        print("=== 实时B-Scan测试结束 ===")
        
        # 保存B-Scan数据和图像
        self.save_bscan()
        
        # 保存结果
        self.results = {
            "num_traces": self.num_traces,
            "success_traces": len(self.bscan_data),
            "total_time": total_time,
            "read_rate": read_rate,
            "bscan_data": self.bscan_data
        }
    
    def acquire_and_plot(self):
        """
        开始采集A-Scan并实时绘制B-Scan
        """
        self.is_running = True
        
        print(f"\n=== 开始实时并行B-Scan绘制采集测试 ({self.num_traces}道) ===")
        print(f"采集周期: {self.acquisition_period_ms}ms")
        
        # 记录开始时间
        self.start_total = time.time()
        print(f"开始时间: {self.start_total:.3f}秒")
        
        # 启动采集线程
        self.acquisition_thread.start()
        
        # 返回None，结果将通过回调获取
        return None
    
    def stop(self):
        """停止采集和绘制"""
        self.is_running = False
        if self.acquisition_thread.isRunning():
            self.acquisition_thread.stop()
            self.acquisition_thread.wait()
    
    def get_results(self):
        """获取测试结果"""
        return getattr(self, 'results', None)
    
    def save_bscan(self):
        """
        保存B-Scan数据和图像
        """
        try:
            if len(self.bscan_data) > 0:
                # 转换为numpy数组，形状为 (num_traces, num_samples)
                bscan_array = np.array(self.bscan_data)
                
                # 保存原始数据到npy文件
                data_filename = f"./real_time_bscan_{self.num_traces}道.npy"
                np.save(data_filename, bscan_array)
                print(f"实时B-Scan数据已保存到: {data_filename}")
                
                # 使用matplotlib保存图像（确保能正常保存）
                import matplotlib.pyplot as plt
                # 配置matplotlib支持中文显示
                plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
                
                plt.figure(figsize=(12, 8))
                # 转置数据，确保X轴为道数，Y轴为采样点
                # origin='upper'表示Y轴从上往下（时深关系）
                plt.imshow(bscan_array.T, aspect='auto', cmap='seismic', 
                          origin='upper', interpolation='nearest')
                plt.colorbar(label='幅度')
                plt.title(f'实时B-Scan图像 ({self.num_traces}道)')
                plt.xlabel('道数')
                plt.ylabel('采样点')
                
                img_filename = f"./real_time_bscan_{self.num_traces}道.png"
                plt.savefig(img_filename, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"实时B-Scan图像已保存到: {img_filename}")
                
        except Exception as e:
            print(f"保存B-Scan失败: {e}")


# ## 3. 数据验证工具


class DataValidator:
    """
    数据验证类，用于验证读取到的A-Scan数据是否与参考数据一致
    """
    @staticmethod
    def load_reference_data(file_path):
        """加载参考CSV数据
        参数：
        - file_path: 参考数据文件路径
        返回：
        - time_data: 时间数组（ns）
        - amp_data: 幅度数据数组
        """
        time_data = []
        amp_data = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 跳过前7行标题和元数据
            for _ in range(7):
                next(reader)
            # 读取数据行
            for row in reader:
                if len(row) >= 2 and row[0] != 'END':
                    try:
                        # 时间转换为纳秒
                        time_ns = float(row[0]) * 1e9
                        amp = float(row[1])
                        time_data.append(time_ns)
                        amp_data.append(amp)
                    except ValueError:
                        continue
        
        return np.array(time_data), np.array(amp_data)
    
    @staticmethod
    def validate_data(ascan_data, reference_time, reference_amp):
        """验证A-Scan数据
        参数：
        - ascan_data: 读取到的A-Scan数据
        - reference_time: 参考时间数组
        - reference_amp: 参考幅度数组
        返回：
        - 验证结果字典
        """
        result = {
            "read_data_points": len(ascan_data),
            "ref_data_points": len(reference_amp),
            "time_range": "0-900ns",
            "expected_points": 501,
            "points_match": len(ascan_data) == len(reference_amp),
            "range_match": len(ascan_data) == 501
        }
        
        # 计算数据相关性
        if len(ascan_data) == len(reference_amp):
            # 归一化数据
            ascan_norm = (ascan_data - np.mean(ascan_data)) / np.std(ascan_data)
            ref_norm = (reference_amp - np.mean(reference_amp)) / np.std(reference_amp)
            correlation = np.corrcoef(ascan_norm, ref_norm)[0, 1]
            result["correlation"] = correlation
            result["high_correlation"] = abs(correlation) > 0.5
        else:
            result["correlation"] = None
            result["high_correlation"] = False
        
        return result
    
    @staticmethod
    def print_validation_result(result):
        """打印验证结果"""
        debug_print("\n=== A-Scan数据验证结果 ===")
        debug_print(f"读取到的数据点: {result['read_data_points']}")
        debug_print(f"参考数据点: {result['ref_data_points']}")
        debug_print(f"期望数据点: {result['expected_points']}")
        debug_print(f"时间范围: {result['time_range']}")
        debug_print(f"数据点数量匹配: {'是' if result['points_match'] else '否'}")
        debug_print(f"期望数量匹配: {'是' if result['range_match'] else '否'}")
        
        if result['correlation'] is not None:
            debug_print(f"数据相关性: {result['correlation']:.4f}")
            debug_print(f"高相关性: {'是' if result['high_correlation'] else '否'}")
        
        debug_print("=== 验证结束 ===")


# ## 4. 测试工具类
class PerformanceTester:
    """
    性能测试工具类，用于测试A-Scan读取、存储和绘制性能
    """
    @staticmethod
    def test_multi_round_reading(vna_controller, rounds=100):
        """
        测试多轮A-Scan读取性能
        参数：
        - vna_controller: VNA控制器实例
        - rounds: 测试轮数
        返回：
        - 测试结果字典
        """
        results = {
            "rounds": rounds,
            "success_rounds": 0,
            "read_times": [],
            "total_time": 0,
            "avg_read_time": 0,
            "max_read_time": 0,
            "min_read_time": float('inf'),
            "read_rate": 0
        }
        
        debug_print(f"\n=== 开始多轮A-Scan读取测试 ({rounds}轮) ===")
        start_total = time.time()
        debug_print(f"开始时间: {start_total:.3f}秒")
        
        for i in range(rounds):
            round_start = time.time()
            ascan_data = vna_controller.read_ascan_data()
            round_end = time.time()
            
            if ascan_data is not None:
                read_time = round_end - round_start
                results["read_times"].append(read_time)
                results["success_rounds"] += 1
                
                if read_time > results["max_read_time"]:
                    results["max_read_time"] = read_time
                if read_time < results["min_read_time"]:
                    results["min_read_time"] = read_time
            
            # 每10轮打印一次进度
            if (i + 1) % 10 == 0:
                debug_print(f"  已完成 {i + 1}/{rounds} 轮")
        
        debug_print(f"结束时间: {time.time():.3f}秒")
        results["total_time"] = time.time() - start_total
        
        if results["success_rounds"] > 0:
            results["avg_read_time"] = np.mean(results["read_times"])
            results["read_rate"] = results["success_rounds"] / results["total_time"]
        
        # 打印测试结果
        debug_print("\n=== 多轮A-Scan读取测试结果 ===")
        debug_print(f"总轮数: {rounds}")
        debug_print(f"成功轮数: {results['success_rounds']}")
        debug_print(f"总耗时: {results['total_time']:.3f}秒")
        debug_print(f"平均读取时间: {results['avg_read_time']*1000:.2f}毫秒")
        debug_print(f"最大读取时间: {results['max_read_time']*1000:.2f}毫秒")
        debug_print(f"最小读取时间: {results['min_read_time']*1000:.2f}毫秒")
        debug_print(f"读取速率: {results['read_rate']:.2f}道/秒")
        debug_print(f"期望速率: 12.00道/秒")
        debug_print(f"是否满足期望速率: {'是' if results['read_rate'] >= 12.0 else '否'}")
        debug_print("=== 读取测试结束 ===")
        
        return results
    
    @staticmethod
    def test_file_storage(ascan_data_list, base_path="./test_data"):
        """
        测试文件存储性能
        参数：
        - ascan_data_list: A-Scan数据列表
        - base_path: 测试数据存储目录
        返回：
        - 测试结果字典
        """
        import os
        
        # 创建测试目录
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        results = {
            "data_count": len(ascan_data_list),
            "multi_file_time": 0,
            "single_file_time": 0,
            "recommended_method": ""
        }
        
        # 测试1: 多文件存储（每道A-Scan一个文件）
        debug_print(f"\n=== 开始多文件存储测试 ({len(ascan_data_list)}道) ===")
        multi_start = time.time()
        
        for i, data in enumerate(ascan_data_list):
            file_path = os.path.join(base_path, f"ascan_{i}.npy")
            np.save(file_path, data)
        
        results["multi_file_time"] = time.time() - multi_start
        debug_print(f"多文件存储耗时: {results['multi_file_time']:.3f}秒")
        
        # 测试2: 单文件存储（所有A-Scan连续写入同一文件）
        debug_print(f"\n=== 开始单文件存储测试 ({len(ascan_data_list)}道) ===")
        single_start = time.time()
        
        # 使用numpy二进制格式存储所有数据
        single_file_path = os.path.join(base_path, "ascan_all.npy")
        np.save(single_file_path, ascan_data_list)
        
        results["single_file_time"] = time.time() - single_start
        debug_print(f"单文件存储耗时: {results['single_file_time']:.3f}秒")
        
        # 理论分析与实际结果比较
        debug_print("\n=== 文件存储性能分析 ===")
        debug_print(f"理论分析: 单文件存储通常比多文件存储更高效，因为减少了文件系统开销")
        debug_print(f"实际结果: {'单文件更高效' if results['single_file_time'] < results['multi_file_time'] else '多文件更高效'}")
        debug_print(f"效率差异: {(abs(results['single_file_time'] - results['multi_file_time']) / max(results['single_file_time'], results['multi_file_time']))*100:.2f}%")
        
        results["recommended_method"] = "单文件存储" if results['single_file_time'] < results['multi_file_time'] else "多文件存储"
        debug_print(f"推荐方法: {results['recommended_method']}")
        debug_print("=== 存储测试结束 ===")
        
        return results

    @staticmethod
    def test_continuous_bscan(vna_controller, num_traces=500):
        """
        测试连续采集多道A-Scan并一次性绘制B-Scan
        参数：
        - vna_controller: VNA控制器实例
        - num_traces: 采集的A-Scan道数
        返回：
        - 测试结果字典
        """
        results = {
            "num_traces": num_traces,
            "success_traces": 0,
            "read_times": [],
            "total_time": 0,
            "avg_read_time": 0,
            "max_read_time": 0,
            "min_read_time": float('inf'),
            "read_rate": 0,
            "bscan_data": []
        }
        
        print(f"\n=== 开始连续B-Scan采集测试 ({num_traces}道) ===")
        
        start_total = time.time()
        
        for i in range(num_traces):
            trace_start = time.time()
            ascan_data = vna_controller.read_ascan_data()
            trace_end = time.time()
            
            if ascan_data is not None:
                read_time = trace_end - trace_start
                results["read_times"].append(read_time)
                results["success_traces"] += 1
                results["bscan_data"].append(ascan_data)
                
                if read_time > results["max_read_time"]:
                    results["max_read_time"] = read_time
                if read_time < results["min_read_time"]:
                    results["min_read_time"] = read_time
            
            # 每50道打印一次进度
            if (i + 1) % 50 == 0:
                print(f"  已完成 {i + 1}/{num_traces} 道")
        
        results["total_time"] = time.time() - start_total
        
        if results["success_traces"] > 0:
            results["avg_read_time"] = np.mean(results["read_times"])
            results["read_rate"] = results["success_traces"] / results["total_time"]
        
        # 绘制最终的B-Scan图像
        print("\n=== 绘制最终B-Scan图像 ===")
        
        try:
            # 转换数据为numpy数组并转置
            bscan_array = np.array(results["bscan_data"]).T
            
            # 使用pyqtgraph绘制B-Scan
            win = pg.GraphicsLayoutWidget(show=True, title=f'连续B-Scan图像 ({num_traces}道)')
            win.resize(1200, 800)
            
            # 添加图像项
            plot = win.addPlot(title=f'连续B-Scan图像 ({num_traces}道)')
            img = pg.ImageItem(bscan_array)
            plot.addItem(img)
            
            # 设置图像属性
            img.setLookupTable(pg.colormap.getFromMatplotlib('seismic').getLookupTable())
            img.setLevels([np.min(bscan_array), np.max(bscan_array)])
            
            # 设置坐标轴方向，origin='upper'表示Y轴从上往下（时深关系）
            plot.invertY(True)
            
            # 添加颜色条
            cbar = pg.ColorBarItem(values=(np.min(bscan_array), np.max(bscan_array)), label='幅度')
            win.addItem(cbar, row=0, col=1)
            # 关联图像
            cbar.setImageItem(img)
            
            # 保存图像到文件（简化版本，直接保存数据）
            filename = f"./continuous_bscan_{num_traces}道.npy"
            np.save(filename, bscan_array)
            print(f"连续B-Scan数据已保存到: {filename}")
            
        except Exception as e:
            print(f"绘制B-Scan失败: {e}")
        
        # 打印测试结果
        print(f"\n=== 连续B-Scan采集测试结果 ===")
        print(f"总道数: {num_traces}")
        print(f"成功道数: {results['success_traces']}")
        print(f"总耗时: {results['total_time']:.3f}秒")
        print(f"平均读取时间: {results['avg_read_time']*1000:.2f}毫秒")
        print(f"最大读取时间: {results['max_read_time']*1000:.2f}毫秒")
        print(f"最小读取时间: {results['min_read_time']*1000:.2f}毫秒")
        print(f"读取速率: {results['read_rate']:.2f}道/秒")
        print(f"期望速率: 12.00道/秒")
        print(f"是否满足期望速率: {'是' if results['read_rate'] >= 12.0 else '否'}")
        
        # 计算稳定速率（去掉前10道和后10道，避免启动和结束时的波动）
        if len(results['read_times']) > 20:
            stable_read_times = results['read_times'][10:-10]
            stable_rate = len(stable_read_times) / sum(stable_read_times)
            print(f"稳定读取速率: {stable_rate:.2f}道/秒")
        
        print("=== 连续B-Scan测试结束 ===")
        
        return results

# ## 5. 主程序

def main():
    # 确保有QApplication实例
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    # 创建控制器实例
    vna_controller = SimpleVNAController()
    
    try:
        # 1. 列出设备
        devices = vna_controller.list_devices()
        if not devices:
            print("未找到任何设备")
            return
        
        # 2. 选择设备连接
        # 使用用户提供的设备名称
        device_name = "TCPIP0::MagicbookPro16-Hunter::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR"
        if not vna_controller.open_device(device_name):
            print("无法打开设备")
            return
        
        # 3. 实时B-Scan采集和绘制测试
        # 500道A-Scan，80ms周期
        plotter = RealTimeBScanPlotter(vna_controller, num_traces=300, acquisition_period_ms=80)
        
        # 开始采集和绘制
        plotter.acquire_and_plot()
        
        # 运行QApplication事件循环，保持窗口响应
        app.exec()
        
        # 测试完成后获取结果
        realtime_results = plotter.get_results()
        if realtime_results:
            # 综合测试结果
            print("\n=== 最终测试结果 ===")
            print(f"实时B-Scan采集结果:")
            print(f"   采集道数: {realtime_results['success_traces']}/{realtime_results['num_traces']}")
            print(f"   总耗时: {realtime_results['total_time']:.3f}秒")
            print(f"   连续采集速率: {realtime_results['read_rate']:.2f}道/秒")
            print(f"   期望速率: {1000/80:.2f}道/秒")
            print(f"   是否满足期望速率: {'是' if realtime_results['read_rate'] >= 1000/80 else '否'}")
            print("=== 所有测试完成 ===")
        
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        vna_controller.close_device()
        print("程序已退出")

# 运行主程序
if __name__ == "__main__":
    main()