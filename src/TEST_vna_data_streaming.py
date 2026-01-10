#!/usr/bin/env python
# coding: utf-8

# # 矢网仪A-Scan时域波形读取测试
# 
# 本示例展示如何使用SCPI指令直接读取VNA显示的时域A-Scan数据，并绘制验证

# 导入必要的库
import pyvisa as visa
import numpy as np
import matplotlib.pyplot as plt
import time
import csv
import threading
import queue

# 尝试导入pyqtgraph和Qt，用于高效的实时B-Scan绘制
try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtCore, QtGui
    import sys
    PYQTGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"pyqtgraph导入失败: {e}")
    PYQTGRAPH_AVAILABLE = False

# 配置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

DEBUG = True
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
    简化版数据可视化类，仅提供A-Scan时域波形绘制功能
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
        
        # 创建画布，绘制时域波形
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 时域波形图
        ax.plot(time_array, data, 'b-', linewidth=1.5)
        ax.set_xlabel('时间 (ns)')
        ax.set_ylabel('幅度')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        # 设置X轴范围
        ax.set_xlim(0, time_range_ns)
        
        plt.tight_layout()
        plt.show()


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
    def test_bscan_real_time(vna_controller, rounds=50):
        """
        测试边读取A-Scan边绘制B-Scan的性能
        参数：
        - vna_controller: VNA控制器实例
        - rounds: 测试轮数
        返回：
        - 测试结果字典
        """
        import matplotlib.animation as animation
        
        results = {
            "rounds": rounds,
            "success_rounds": 0,
            "read_times": [],
            "total_time": 0,
            "avg_read_time": 0,
            "max_read_time": 0,
            "min_read_time": float('inf'),
            "read_rate": 0,
            "bscan_data": []
        }
        
        debug_print(f"\n=== 开始边读取边绘制B-Scan测试 ({rounds}轮) ===")
        
        # 初始化B-Scan图像
        fig, ax = plt.subplots(figsize=(10, 8))
        im = None
        
        start_total = time.time()
        
        for i in range(rounds):
            # 读取A-Scan数据
            round_start = time.time()
            ascan_data = vna_controller.read_ascan_data()
            round_end = time.time()
            
            if ascan_data is not None:
                read_time = round_end - round_start
                results["read_times"].append(read_time)
                results["success_rounds"] += 1
                results["bscan_data"].append(ascan_data)
                
                if read_time > results["max_read_time"]:
                    results["max_read_time"] = read_time
                if read_time < results["min_read_time"]:
                    results["min_read_time"] = read_time
                
                # 更新B-Scan图像
                bscan_array = np.array(results["bscan_data"]).T
                if im is None:
                    # 第一次绘制
                    im = ax.imshow(bscan_array, aspect='auto', cmap='seismic', 
                                  origin='lower', interpolation='nearest')
                    plt.colorbar(im)
                    ax.set_title('实时B-Scan图像')
                    ax.set_xlabel('道数')
                    ax.set_ylabel('采样点')
                else:
                    # 更新图像数据
                    im.set_data(bscan_array)
                    im.set_extent([0, bscan_array.shape[1]-1, 0, bscan_array.shape[0]-1])
                
                # 刷新图像
                plt.pause(0.001)
            
            # 每10轮打印一次进度
            if (i + 1) % 10 == 0:
                debug_print(f"  已完成 {i + 1}/{rounds} 轮")
        
        results["total_time"] = time.time() - start_total
        
        if results["success_rounds"] > 0:
            results["avg_read_time"] = np.mean(results["read_times"])
            results["read_rate"] = results["success_rounds"] / results["total_time"]
        
        # 打印测试结果
        debug_print(f"\n=== B-Scan实时绘制测试结果 ===")
        debug_print(f"总轮数: {rounds}")
        debug_print(f"成功轮数: {results['success_rounds']}")
        debug_print(f"总耗时: {results['total_time']:.3f}秒")
        debug_print(f"平均读取时间: {results['avg_read_time']*1000:.2f}毫秒")
        debug_print(f"读取速率: {results['read_rate']:.2f}道/秒")
        debug_print(f"是否保持了原始采集速率: {'是' if results['read_rate'] >= 10.0 else '否'}")
        debug_print("=== B-Scan测试结束 ===")
        
        # 保存最终B-Scan图像
        plt.savefig("./bscan_final.png", dpi=300, bbox_inches='tight')
        debug_print("B-Scan最终图像已保存")
        
        return results
    
    @staticmethod
    def test_bscan_pyqtgraph(vna_controller, rounds=50):
        """
        测试使用pyqtgraph进行高效的B-Scan实时绘制
        参数：
        - vna_controller: VNA控制器实例
        - rounds: 测试轮数
        返回：
        - 测试结果字典
        """
        if not PYQTGRAPH_AVAILABLE:
            debug_print("pyqtgraph未安装，无法进行此测试")
            return None
        
        results = {
            "rounds": rounds,
            "success_rounds": 0,
            "read_times": [],
            "total_time": 0,
            "avg_read_time": 0,
            "max_read_time": 0,
            "min_read_time": float('inf'),
            "read_rate": 0,
            "bscan_data": []
        }
        
        # 创建数据队列用于线程通信
        data_queue = queue.Queue()
        stop_event = threading.Event()
        
        class BScanWindow(pg.GraphicsLayoutWidget):
            """pyqtgraph B-Scan显示窗口"""
            def __init__(self):
                super().__init__()
                self.setWindowTitle('实时B-Scan图像 (pyqtgraph)')
                self.setGeometry(100, 100, 1000, 800)
                
                # 创建视图
                self.view = self.addViewBox()
                self.view.setAspectLocked(False)
                
                # 创建图像项
                self.img = pg.ImageItem()
                self.view.addItem(self.img)
                
                # 设置颜色映射
                self.colormap = pg.colormap.get('RdBu', source='matplotlib')  # 使用类似seismic的颜色映射
                self.img.setLookupTable(self.colormap.getLookupTable())
                
                # 添加颜色条
                self.cbar = pg.ColorBarItem(values=(0, 1), colorMap=self.colormap)
                self.cbar.setImageItem(self.img)
                self.cbar.setWidth(30)
                self.cbar.setHeight(600)
                self.addItem(self.cbar, row=0, col=1)
                
                # 设置坐标轴
                self.view.setLabel('left', text='采样点')
                self.view.setLabel('bottom', text='道数')
                
                # 初始化数据
                self.bscan_data = []
                
            def update_bscan(self, ascan_data):
                """更新B-Scan数据并刷新图像"""
                self.bscan_data.append(ascan_data)
                
                # 转换为numpy数组并转置，使道数为X轴，采样点为Y轴
                bscan_array = np.array(self.bscan_data).T
                
                # 更新图像数据
                self.img.setImage(bscan_array)
                
                # 调整视图范围以适应新数据
                self.view.autoRange()
                
            def save_image(self, filename):
                """保存当前图像"""
                self.scene().save()
                debug_print(f"pyqtgraph B-Scan图像已保存")
        
        def pyqtgraph_main():
            """pyqtgraph主循环，运行在主线程"""
            debug_print("pyqtgraph主循环已启动")
            
            # 创建应用和窗口
            app = pg.mkQApp()
            win = BScanWindow()
            win.show()
            
            def update_from_queue():
                """从队列获取数据并更新图像"""
                try:
                    while not data_queue.empty():
                        ascan_data = data_queue.get_nowait()
                        if ascan_data is not None:
                            win.update_bscan(ascan_data)
                        data_queue.task_done()
                    
                    if stop_event.is_set():
                        win.save_image("./bscan_pyqtgraph_final.png")
                        app.quit()
                except queue.Empty:
                    pass
            
            # 创建定时器，定期从队列获取数据
            timer = QtCore.QTimer()
            timer.timeout.connect(update_from_queue)
            timer.start(10)  # 每10ms检查一次队列
            
            # 启动应用事件循环
            app.exec_()
        
        debug_print(f"\n=== 开始pyqtgraph B-Scan绘制测试 ({rounds}轮) ===")
        
        # 启动pyqtgraph主线程
        pg_thread = threading.Thread(target=pyqtgraph_main)
        pg_thread.daemon = False  # 必须在主线程运行，所以这里设置为非守护线程
        pg_thread.start()
        
        start_total = time.time()
        
        for i in range(rounds):
            # 读取A-Scan数据
            round_start = time.time()
            ascan_data = vna_controller.read_ascan_data()
            round_end = time.time()
            
            if ascan_data is not None:
                read_time = round_end - round_start
                results["read_times"].append(read_time)
                results["success_rounds"] += 1
                results["bscan_data"].append(ascan_data)
                
                if read_time > results["max_read_time"]:
                    results["max_read_time"] = read_time
                if read_time < results["min_read_time"]:
                    results["min_read_time"] = read_time
                
                # 将数据放入队列供pyqtgraph更新
                data_queue.put(ascan_data)
            
            # 每10轮打印一次进度
            if (i + 1) % 10 == 0:
                debug_print(f"  已完成 {i + 1}/{rounds} 轮")
        
        results["total_time"] = time.time() - start_total
        
        # 通知pyqtgraph线程停止
        stop_event.set()
        
        # 等待pyqtgraph线程完成
        pg_thread.join(timeout=5.0)
        
        if results["success_rounds"] > 0:
            results["avg_read_time"] = np.mean(results["read_times"])
            results["read_rate"] = results["success_rounds"] / results["total_time"]
        
        # 打印测试结果
        debug_print(f"\n=== pyqtgraph B-Scan绘制测试结果 ===")
        debug_print(f"总轮数: {rounds}")
        debug_print(f"成功轮数: {results['success_rounds']}")
        debug_print(f"总耗时: {results['total_time']:.3f}秒")
        debug_print(f"平均读取时间: {results['avg_read_time']*1000:.2f}毫秒")
        debug_print(f"读取速率: {results['read_rate']:.2f}道/秒")
        debug_print(f"是否保持了原始采集速率: {'是' if results['read_rate'] >= 10.0 else '否'}")
        debug_print("=== pyqtgraph B-Scan测试结束 ===")
        
        return results

# ## 5. 主程序

def main():
    # 创建控制器实例
    vna_controller = SimpleVNAController()
    
    try:
        # 1. 列出设备
        devices = vna_controller.list_devices()
        if not devices:
            debug_print("未找到任何设备")
            return
        
        # 2. 选择设备连接
        # 使用用户提供的设备名称
        device_name = "TCPIP0::MagicbookPro16-Hunter::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR"
        if not vna_controller.open_device(device_name):
            debug_print("无法打开设备")
            return
        
        # 3. 测试1: 多轮A-Scan读取性能
        reading_results = PerformanceTester.test_multi_round_reading(vna_controller, rounds=100)
        
        # 4. 准备测试数据（用于存储测试）
        debug_print("\n=== 准备存储测试数据 ===")
        test_data = []
        for i in range(50):  # 准备50道测试数据
            data = vna_controller.read_ascan_data()
            if data is not None:
                test_data.append(data)
        debug_print(f"已准备 {len(test_data)} 道测试数据")
        
        # 5. 测试2: 文件存储性能
        storage_results = PerformanceTester.test_file_storage(test_data)
        
        # 6. 测试3: 边读取边绘制B-Scan
        bscan_results = PerformanceTester.test_bscan_real_time(vna_controller, rounds=50)
        
        # 7. 测试4: pyqtgraph高效B-Scan绘制
        bscan_pyqtgraph_results = PerformanceTester.test_bscan_pyqtgraph(vna_controller, rounds=50)
        
        # 8. 综合测试结果
        debug_print("\n=== 综合测试结果 ===")
        debug_print(f"1. 读取速率: {reading_results['read_rate']:.2f}道/秒 (期望: 12道/秒)")
        debug_print(f"2. 存储效率: 单文件({storage_results['single_file_time']:.3f}秒) vs 多文件({storage_results['multi_file_time']:.3f}秒)")
        debug_print(f"   推荐: {storage_results['recommended_method']}")
        debug_print(f"3. Matplotlib边读取边绘制速率: {bscan_results['read_rate']:.2f}道/秒")
        
        if bscan_pyqtgraph_results:
            debug_print(f"4. pyqtgraph高效绘制速率: {bscan_pyqtgraph_results['read_rate']:.2f}道/秒")
            if bscan_results['read_rate'] > 0:
                debug_print(f"   pyqtgraph性能提升: {bscan_pyqtgraph_results['read_rate'] / bscan_results['read_rate']:.2f}倍")
        
        debug_print("=== 所有测试完成 ===")
        
    except KeyboardInterrupt:
        debug_print("\n用户中断程序")
    except Exception as e:
        debug_print(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        vna_controller.close_device()
        plt.close('all')
        debug_print("程序已退出")

# 运行主程序
if __name__ == "__main__":
    main()