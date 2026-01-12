#!/usr/bin/env python
# coding: utf-8

# # 实时A-Scan和B-Scan双窗口显示测试
# 
# 本示例展示如何同时实时显示A-Scan和B-Scan窗口，并测量实际采集速率

# 导入必要的库
import pyvisa as visa
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import time
import sys

# 设置pyqtgraph全局主题为浅色
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# 矢网仪控制器类
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
            print("VISA资源管理器初始化成功")
        except Exception as e:
            print(f"VISA资源管理器初始化失败: {e}")
            self.rm = None

    def list_devices(self):
        """列出所有连接的VISA设备"""
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
        """打开VISA设备"""
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
        """关闭VISA设备"""
        if self.vna:
            try:
                self.vna.close()
                print("设备已关闭")
            except Exception as e:
                print(f"关闭设备失败: {e}")
            finally:
                self.vna = None

    def write(self, command):
        """发送命令到设备"""
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
        """发送查询命令并返回响应"""
        if not self.vna:
            print("设备未连接")
            return None
        try:
            return self.vna.query(command).strip()
        except Exception as e:
            print(f"查询失败: {e}")
            return None

    def read_ascan_data(self):
        """直接读取VNA显示的A-Scan时域数据"""
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

# 数据采集线程
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

# 实时A-Scan显示类
class RealTimeAScanPlotter:
    """
    实时A-Scan显示类，用于显示当前A-Scan数据
    """
    def __init__(self, num_samples=501):
        """
        初始化实时A-Scan显示
        """
        # 创建窗口
        self.win = pg.GraphicsLayoutWidget(show=True, title='实时A-Scan图像')
        self.win.resize(800, 600)
        
        # 添加绘图项
        self.plot = self.win.addPlot(title='A-Scan时域波形')
        self.curve = self.plot.plot([], [], pen='b', lineWidth=2)
        
        # 设置坐标轴
        self.plot.setLabel('bottom', '采样点')
        self.plot.setLabel('left', '幅度')
        self.plot.setXRange(0, num_samples)
        
        # 初始化数据
        self.time_data = np.arange(num_samples)
        self.current_ascan = np.zeros(num_samples)
    
    def update_ascan(self, ascan_data):
        """
        更新A-Scan显示
        """
        self.current_ascan = ascan_data
        self.curve.setData(self.time_data, self.current_ascan)
        
        # 更新X轴范围以适应数据长度
        self.plot.setXRange(0, len(ascan_data))

# 实时B-Scan显示类
class RealTimeBScanPlotter:
    """
    实时B-Scan显示类，用于显示累积的B-Scan数据
    """
    def __init__(self, num_traces=500):
        """
        初始化实时B-Scan显示
        """
        # 创建窗口
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
        
        # 初始化数据
        self.bscan_data = []
        self.num_traces = num_traces
    
    def update_bscan(self, ascan_data):
        """
        更新B-Scan显示
        """
        # 添加新数据
        self.bscan_data.append(ascan_data)
        
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

# 主程序
class DualWindowTest:
    """
    双窗口测试主类，管理A-Scan和B-Scan的实时显示
    """
    def __init__(self, num_traces=500, acquisition_period_ms=80):
        """
        初始化双窗口测试
        """
        self.num_traces = num_traces
        self.acquisition_period_ms = acquisition_period_ms
        
        # 创建VNA控制器
        self.vna_controller = SimpleVNAController()
        
        # 创建显示窗口
        self.ascan_plotter = RealTimeAScanPlotter()
        self.bscan_plotter = RealTimeBScanPlotter(num_traces)
        
        # 创建采集线程
        self.acquisition_thread = AcquisitionThread(
            self.vna_controller, 
            num_traces=num_traces,
            acquisition_period_ms=acquisition_period_ms
        )
        
        # 连接信号槽
        self.acquisition_thread.new_data.connect(self.update_plots)
        self.acquisition_thread.progress.connect(self.on_progress)
        self.acquisition_thread.finished.connect(self.on_finished)
        
        # 记录开始时间
        self.start_time = 0
        self.success_traces = 0
    
    def start_test(self):
        """
        开始测试
        """
        # 连接设备
        device_name = "TCPIP0::MagicbookPro16-Hunter::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR"
        if not self.vna_controller.open_device(device_name):
            print("无法打开设备，测试终止")
            return
        
        # 开始采集
        self.start_time = time.time()
        self.success_traces = 0
        
        print(f"\n=== 开始双窗口实时B-Scan/A-Scan测试 ({self.num_traces}道) ===")
        print(f"采集周期: {self.acquisition_period_ms}ms")
        
        self.acquisition_thread.start()
    
    def update_plots(self, ascan_data):
        """
        更新A-Scan和B-Scan显示
        """
        self.success_traces += 1
        self.ascan_plotter.update_ascan(ascan_data)
        self.bscan_plotter.update_bscan(ascan_data)
    
    def on_progress(self, current, total):
        """
        进度更新处理
        """
        print(f"  已完成 {current}/{total} 道")
    
    def on_finished(self):
        """
        测试完成处理
        """
        total_time = time.time() - self.start_time
        read_rate = self.success_traces / total_time if total_time > 0 else 0
        
        print(f"\n=== 双窗口实时B-Scan/A-Scan测试结果 ===")
        print(f"总道数: {self.num_traces}")
        print(f"成功道数: {self.success_traces}")
        print(f"总耗时: {total_time:.3f}秒")
        print(f"实际采集速率: {read_rate:.2f}道/秒")
        print(f"期望速率: {1000/self.acquisition_period_ms:.2f}道/秒")
        print(f"是否满足期望速率: {'是' if read_rate >= 1000/self.acquisition_period_ms else '否'}")
        print("=== 测试结束 ===")
        
        # 关闭设备
        self.vna_controller.close_device()

# 主函数
if __name__ == "__main__":
    # 创建QApplication实例
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    # 创建测试实例
    test = DualWindowTest(num_traces=300, acquisition_period_ms=80)
    
    # 开始测试
    test.start_test()
    
    # 运行事件循环
    app.exec()
    
    # 测试结束
    print("程序已退出")
