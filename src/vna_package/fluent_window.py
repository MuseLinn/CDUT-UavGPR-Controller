# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2025-07-28 22:04:03
LastEditors  : Linn
LastEditTime : 2025-07-29 18:10:00
FilePath     : \\usbvna\\src\\vna_package\\fluent_window.py
Description  : Functions and Objects forked from PyQt6, FluentWindow and vna_controller
2025-07-29-18:30 FIXED: point measurement method refresh-hold response needs to be fixed
                    开启点测时，切换至其他模式后切换回来直接点击采集会crush，但停止再开始正常——信号绑定与线程问题

Copyright (c) 2025 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""
import os
import time
import pyvisa as visa
from datetime import datetime
from .vna_controller import VNAController
from .logger_config import setup_logger

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QGroupBox, QLabel, QTextEdit, QStackedWidget,
    QFileDialog, QGridLayout  # 添加文件对话框支持
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QFileInfo, QEventLoop, QTimer
from PyQt6.QtGui import QFont, QIcon

# 导入PyQt6-Fluent-Widgets组件
from qfluentwidgets import (
    FluentWindow, FluentIcon, PrimaryPushButton, PushButton, EditableComboBox as ComboBox, SpinBox, DoubleSpinBox,
    LineEdit, ProgressBar, SplashScreen,
    InfoBar, InfoBarPosition, FluentIcon as FIF,
    ComboBoxSettingCard, OptionsConfigItem, OptionsValidator, QConfig  # 添加新导入
)

# NOTE: 创建日志记录器
logger = setup_logger("vna_window", "logs/vna_window.log", level=10)  # 10对应DEBUG级别

class AcquisitionModeConfig(QConfig):
    """采集模式配置"""
    Mode = OptionsConfigItem(
        "Acquisition", "Mode", "point", OptionsValidator(["point", "fixed", "continuous"]), restart=False)


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

    def __init__(self, vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval, start_index):
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


class VNAControllerGUI(FluentWindow):
    def __init__(self):
        """初始化VNA控制器GUI界面"""
        super().__init__()

        # 初始化VNA控制器为None，稍后再初始化
        self.status_group = None
        self.mode_combo_card = None
        self.mode_config = None
        self.continuous_mode_page = None
        self.fixed_mode_page = None
        self.point_mode_page = None
        self.vna_controller = None
        self.device_connected = False

        # 初始化各种工作线程
        self.fixed_worker = None       # 定次采集工作线程
        self.continuous_worker = None  # 连续采集工作线程
        self.point_worker = None       # 点测采集工作线程

        # 初始化工作状态
        self.is_continuous_running = False  # 连续采集运行状态
        self.is_point_running = False       # 点测采集运行状态

        # 点测模式计数器
        self.point_sample_counter = 0       # 点测样本计数器
        self.point_group_counter = 0        # 点测组计数器

        # 初始化界面组件
        self.homeInterface = None           # 主界面部件
        self.main_layout = None           # 主布局
        self.title_label = None           # 标题标签
        self.device_combo = None          # 设备选择下拉框
        self.refresh_button = None        # 刷新设备按钮
        self.connect_button = None        # 连接设备按钮
        self.disconnect_button = None     # 断开设备按钮
        self.get_id_button = None         # 获取设备ID按钮
        self.catalog_button = None        # 查看目录按钮
        self.path_line_edit = None        # 路径输入框
        self.browse_dir_button = None     # 浏览目录按钮
        self.change_dir_button = None     # 切换目录按钮
        self.data_type_combo = None       # 数据类型下拉框
        self.scope_combo = None           # 范围下拉框
        self.format_combo = None          # 数据格式下拉框
        self.selector_spin = None         # 测量编号选择框
        self.file_prefix_line_edit = None # 文件前缀输入框
        self.interval_spin = None         # 数据存储间隔时间选择框
        self.point_mode_radio = None      # 点测模式单选按钮
        self.fixed_mode_radio = None      # 定次采集模式单选按钮
        self.continuous_mode_radio = None # 连续采集模式单选按钮
        self.mode_stacked_widget = None   # 模式堆叠部件
        self.point_acquire_button = None  # 点测采集按钮
        self.point_count_spin = None      # 点测采集数量选择框
        self.point_start_button = None    # 点测开始按钮
        self.point_stop_button = None     # 点测停止按钮
        self.fixed_count_spin = None      # 定次采集数量选择框
        self.fixed_start_button = None    # 定次开始按钮
        self.continuous_start_button = None # 连续开始按钮
        self.continuous_stop_button = None  # 连续停止按钮
        self.status_text_edit = None      # 状态信息文本框
        self.progress_bar = None          # 进度条

        # 创建界面
        """初始化用户界面组件"""
        # 设置窗口标题和大小
        self.setWindowTitle('CDUT-非显性滑坡延缓高效勘测技术装备研发')
        self.resize(1100, 800)
        self.setMinimumSize(1100, 800)
        root = QFileInfo(__file__).absolutePath()
        self.setWindowIcon(QIcon(root+'/app_logo.png'))
        # 创建启动页面
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(102, 102))

        # 居中显示窗口
        self.center_window()

        # 在创建其他子页面前先显示主页面
        self.show()
        # 启动页面
        self.welcomeInterface()
        # 隐藏启动界面
        self.splashScreen.finish()

        # 创建主界面
        self.homeInterface = QWidget()
        if hasattr(self.homeInterface, 'setObjectName'):
            self.homeInterface.setObjectName("homeInterface")  # 添加对象名称
            
        # 初始化spacing属性
        self.spacing = 10
        
        # 创建主水平布局
        main_h_layout = QHBoxLayout(self.homeInterface)
        main_h_layout.setSpacing(self.spacing)
        main_h_layout.setContentsMargins(15, 15, 15, 15)

        # 创建左侧配置区域
        self.config_widget = QWidget()
        self.main_layout = QVBoxLayout(self.config_widget)
        self.main_layout.setSpacing(self.spacing)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建标题
        self.title_label = QLabel('CDUT-GPR探地雷达采集控制面板v0.8Rev9')
        self.title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #007acc; margin: 10px 0;")
        self.main_layout.addWidget(self.title_label)

        # 创建设备控制区域
        self.create_control_section()
        # 数据采集配置区域
        self.create_data_config_section()
        # 采集模式区域
        self.create_acquisition_mode_section()

        # 创建右侧状态信息区域
        self.status_widget = QWidget()
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setSpacing(self.spacing)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建状态信息区域
        self.create_status_section()
        status_layout.addWidget(self.status_group)

        # 将左右区域添加到主布局
        main_h_layout.addWidget(self.config_widget, 3)  # 左侧配置区域占3份
        main_h_layout.addWidget(self.status_widget, 2)  # 右侧状态区域占2份

        # 添加界面到 FluentWindow
        self.initNavigation()

        # 设置信号连接
        self.setup_connections()
        # 初始化数据选项
        self.init_data_options()
        # 初始化采集模式
        self.init_acquisition_modes()
        # 显示初始状态信息（现在确保组件已创建）
        self.log_message("系统初始化完成，准备就绪")

    def center_window(self):
        """将窗口居中显示在屏幕中央"""
        # 获取屏幕尺寸
        screen = self.screen().availableGeometry()
        # 获取窗口尺寸
        window = self.geometry()
        # 计算居中位置
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        # 移动窗口到居中位置
        self.move(x, y)

    def welcomeInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '主页')


    def log_message(self, message):
        """在状态文本框中添加日志消息"""
        if hasattr(self, 'status_text_edit') and self.status_text_edit is not None:
            timestamp = datetime.now().strftime("%H:%M:%S:%f")
            self.status_text_edit.append(f"[{timestamp}] {message}")
            # 滚动到底部
            self.status_text_edit.verticalScrollBar().setValue(
                self.status_text_edit.verticalScrollBar().maximum()
            )

    def create_control_section(self):
        """创建设备控制区域"""
        # 设备控制标题
        control_label = QLabel('设备控制')
        control_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
        self.main_layout.addWidget(control_label)

        # 创建连接区域容器
        connection_group = QGroupBox("连接参数")
        connection_group_layout = QVBoxLayout(connection_group)
        connection_group_layout.setSpacing(self.spacing)
        connection_group_layout.setContentsMargins(15, 15, 15, 15)

        # 设备连接控件
        connection_layout = QHBoxLayout()

        device_label = QLabel('设备地址:')
        self.device_combo = ComboBox()
        # PyQt6-Fluent-Widgets EditableComboBox是可编辑的，只需设置LineEdit为可编辑即可
        self.device_combo.addItems(['TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR'])
        self.device_combo.setCurrentText('TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR')
        self.device_combo.setMinimumWidth(200)

        self.refresh_button = PushButton('刷新设备')
        self.connect_button = PrimaryPushButton(FluentIcon.CONNECT, '连接')
        self.disconnect_button = PushButton('断开')
        self.disconnect_button.setEnabled(False)
        self.get_id_button = PushButton('获取设备ID')
        self.get_id_button.setEnabled(False)

        connection_layout.addWidget(device_label)
        connection_layout.addWidget(self.device_combo, 2) # 添加拉伸因子，占满剩余空间
        connection_layout.addWidget(self.refresh_button)
        connection_layout.addWidget(self.connect_button)
        connection_layout.addWidget(self.disconnect_button)
        connection_layout.addWidget(self.get_id_button)
        connection_layout.addStretch()

        connection_group_layout.addLayout(connection_layout)
        self.main_layout.addWidget(connection_group)

    def create_data_config_section(self):
        """创建数据采集配置区域"""
        # 数据配置标题
        config_label = QLabel('A-scan采集配置')
        config_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
        self.main_layout.addWidget(config_label)

        # 创建控制区域容器
        control_group = QGroupBox("存储配置")
        control_group_layout = QVBoxLayout(control_group)
        control_group_layout.setSpacing(self.spacing)
        control_group_layout.setContentsMargins(15, 15, 15, 15)

        # 设备控制按钮
        control_layout = QHBoxLayout()

        path_label = QLabel('路径:')
        self.path_line_edit = LineEdit()
        # 自动根据电脑用户设置默认的路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Documents")
        self.path_line_edit.setText(desktop_path)
        self.path_line_edit.setMinimumWidth(300)

        self.catalog_button = PushButton('查看目录')
        self.catalog_button.setEnabled(False)
        self.browse_dir_button = PushButton('选择目录')
        self.browse_dir_button.setEnabled(False)
        self.change_dir_button = PushButton('切换目录')
        self.change_dir_button.setEnabled(False)

        control_layout.addWidget(path_label)
        control_layout.addWidget(self.path_line_edit, 2)
        control_layout.addWidget(self.catalog_button)
        control_layout.addWidget(self.browse_dir_button)  # 添加浏览按钮
        control_layout.addWidget(self.change_dir_button)
        control_layout.addStretch()

        control_group_layout.addLayout(control_layout)
        self.main_layout.addWidget(control_group)

        # 创建配置区域容器
        config_group = QGroupBox("配置参数")
        config_group_layout = QVBoxLayout(config_group)
        config_group_layout.setSpacing(self.spacing)
        config_group_layout.setContentsMargins(15, 15, 15, 15)

        # 使用网格布局实现标签对齐
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(15)
        grid_layout.setVerticalSpacing(10)
        
        # 第一行控件
        data_type_label = QLabel('数据类型:')
        data_type_label.setMinimumWidth(80)  # 设置标签最小宽度以保证对齐
        self.data_type_combo = ComboBox()
        self.data_type_combo.addItems([
            "CSV Formatted Data",
            "SDP Formatted Data",
            "SNP Formatted Data"
        ])
        self.data_type_combo.setMinimumWidth(120)

        scope_label = QLabel('范围:')
        scope_label.setMinimumWidth(80)  # 保持与上面标签相同宽度以对齐
        self.scope_combo = ComboBox()
        self.scope_combo.addItems([
            "Trace",
            "Displayed",
            "Channel",
            "Auto"
        ])
        self.scope_combo.setMinimumWidth(100)

        # 第二行控件
        format_label = QLabel('数据格式:')
        format_label.setMinimumWidth(80)  # 保持一致的标签宽度
        self.format_combo = ComboBox()
        self.format_combo.addItems([
            "Displayed",
            "RI",  # Real Imaginary
            "MA",  # Magnitude Angle
            "DB"  # Decibel Angle
        ])
        self.format_combo.setMinimumWidth(100)

        selector_label = QLabel('测量编号:')
        selector_label.setMinimumWidth(80)  # 保持一致的标签宽度
        self.selector_spin = SpinBox()
        self.selector_spin.setRange(-1, 100)
        self.selector_spin.setValue(-1)
        self.selector_spin.setMinimumWidth(80)

        # 第三行控件
        file_prefix_label = QLabel('文件前缀:')
        file_prefix_label.setMinimumWidth(80)  # 保持一致的标签宽度
        self.file_prefix_line_edit = LineEdit()
        self.file_prefix_line_edit.setText('usbvna')
        self.file_prefix_line_edit.setMinimumWidth(80)

        interval_label = QLabel('存储间隔(s):')
        interval_label.setMinimumWidth(80)  # 保持一致的标签宽度
        self.interval_spin = DoubleSpinBox()
        self.interval_spin.setRange(0.005, 10.00)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setSingleStep(0.01)
        self.interval_spin.setValue(0.08)
        self.interval_spin.setMinimumWidth(80)

        # 将控件添加到网格布局
        # 第一行
        grid_layout.addWidget(data_type_label, 0, 0)
        grid_layout.addWidget(self.data_type_combo, 0, 1)
        grid_layout.addWidget(scope_label, 0, 2)
        grid_layout.addWidget(self.scope_combo, 0, 3)
        
        # 第二行
        grid_layout.addWidget(format_label, 1, 0)
        grid_layout.addWidget(self.format_combo, 1, 1)
        grid_layout.addWidget(selector_label, 1, 2)
        grid_layout.addWidget(self.selector_spin, 1, 3)
        
        # 第三行
        grid_layout.addWidget(file_prefix_label, 2, 0)
        grid_layout.addWidget(self.file_prefix_line_edit, 2, 1)
        grid_layout.addWidget(interval_label, 2, 2)
        grid_layout.addWidget(self.interval_spin, 2, 3)
        
        # 添加弹性空间
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)

        # 添加网格布局到配置组
        config_group_layout.addLayout(grid_layout)

        self.main_layout.addWidget(config_group)

    def create_acquisition_mode_section(self):
        """创建采集模式区域"""
        # 采集模式标题
        mode_label = QLabel('采集模式')
        mode_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
        self.main_layout.addWidget(mode_label)

        # 创建配置项
        self.mode_config = AcquisitionModeConfig()

        # 模式选择下拉框
        self.mode_combo_card = ComboBoxSettingCard(
            configItem=self.mode_config.Mode,
            icon=FIF.ALIGNMENT,
            title='采集模式',
            content='选择数据采集模式',
            texts=['点测模式', '定次采集模式', '连续采集模式']
        )
        self.mode_config.Mode.valueChanged.connect(self.on_mode_changed)

        # # 创建模式选择区域容器
        # mode_selection_group = QGroupBox("模式选择")
        # mode_selection_layout = QVBoxLayout(mode_selection_group)
        # mode_selection_layout.setSpacing(self.spacing)
        # mode_selection_layout.setContentsMargins(15, 15, 15, 15)
        # mode_selection_layout.addWidget(self.mode_combo_card)
        #
        # self.main_layout.addWidget(mode_selection_group)

        # 直接将模式选择控件添加到主布局，不使用QGroupBox
        self.main_layout.addWidget(self.mode_combo_card)

        # 模式堆叠部件
        self.mode_stacked_widget = QStackedWidget()

        # 点测模式页面
        self.point_mode_page = QGroupBox("点测模式参数")
        point_layout = QHBoxLayout(self.point_mode_page)
        point_layout.setSpacing(self.spacing)  # 设置控件间距
        point_layout.setContentsMargins(15, 15, 15, 15)  # 设置边距

        self.point_acquire_button = PrimaryPushButton('单次采集')  # 修改按钮名称
        self.point_acquire_button.setEnabled(False)

        point_count_label = QLabel('每次采集道数:')
        self.point_count_spin = SpinBox()
        self.point_count_spin.setRange(1, 10000)
        self.point_count_spin.setValue(10)

        self.point_start_button = PrimaryPushButton('开始连续采集')
        self.point_start_button.setEnabled(False)
        self.point_stop_button = PushButton('停止连续采集')
        self.point_stop_button.setEnabled(False)

        point_layout.addWidget(self.point_acquire_button)
        point_layout.addWidget(point_count_label)
        point_layout.addWidget(self.point_count_spin)
        point_layout.addWidget(self.point_start_button)
        point_layout.addWidget(self.point_stop_button)
        point_layout.addStretch()  # 添加弹性空间

        # 定次采集模式页面
        self.fixed_mode_page = QGroupBox("定次采集模式参数")
        fixed_layout = QHBoxLayout(self.fixed_mode_page)
        fixed_layout.setSpacing(self.spacing)  # 设置控件间距
        fixed_layout.setContentsMargins(15, 15, 15, 15)  # 设置边距

        fixed_count_label = QLabel('采集次数:')
        self.fixed_count_spin = SpinBox()
        self.fixed_count_spin.setRange(1, 10000)
        self.fixed_count_spin.setValue(1000)

        self.fixed_start_button = PrimaryPushButton('开始采集')
        self.fixed_start_button.setEnabled(False)

        # 优化定次采集模式布局
        fixed_layout.addWidget(fixed_count_label)
        fixed_layout.addWidget(self.fixed_count_spin)
        fixed_layout.addWidget(self.fixed_start_button)
        fixed_layout.addStretch()  # 添加弹性空间

        # 连续采集模式页面
        self.continuous_mode_page = QGroupBox("连续采集模式参数")
        continuous_layout = QHBoxLayout(self.continuous_mode_page)
        continuous_layout.setSpacing(self.spacing)  # 设置控件间距
        continuous_layout.setContentsMargins(15, 15, 15, 15)  # 设置边距

        self.continuous_start_button = PrimaryPushButton('开始采集')
        self.continuous_start_button.setEnabled(False)
        self.continuous_stop_button = PushButton('停止采集')
        self.continuous_stop_button.setEnabled(False)

        # 优化连续采集模式布局
        continuous_layout.addWidget(self.continuous_start_button)
        continuous_layout.addWidget(self.continuous_stop_button)
        continuous_layout.addStretch()  # 添加弹性空间

        # 添加页面到堆叠部件
        self.mode_stacked_widget.addWidget(self.point_mode_page)
        self.mode_stacked_widget.addWidget(self.fixed_mode_page)
        self.mode_stacked_widget.addWidget(self.continuous_mode_page)

        self.main_layout.addWidget(self.mode_stacked_widget)

    def create_status_section(self):
        """创建状态信息区域"""
        # 状态信息标题
        status_label = QLabel('状态信息')
        status_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
        # 注意：这里不再添加到主布局，而是添加到右侧状态区域布局

        # 创建状态区域容器
        self.status_group = QGroupBox("运行状态")
        status_group_layout = QVBoxLayout(self.status_group)
        status_group_layout.setSpacing(self.spacing)
        status_group_layout.setContentsMargins(15, 15, 15, 15)

        # 状态文本框
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setMinimumHeight(100)
        self.status_text_edit.setReadOnly(True)
        status_group_layout.addWidget(self.status_text_edit)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False) # 默认隐藏进度条
        status_group_layout.addWidget(self.progress_bar)

        # 注意：这里不再添加到主布局

    def init_data_options(self):
        """初始化数据采集选项"""
        # 数据类型选项已在UI创建时初始化
        pass

    def init_acquisition_modes(self):
        """初始化采集模式"""
        # 初始化模式页面
        self.on_mode_changed()

    def setup_connections(self):
        """设置所有按钮和控件的信号连接"""
        self.refresh_button.clicked.connect(self.refresh_devices)
        self.connect_button.clicked.connect(self.connect_device)
        self.disconnect_button.clicked.connect(self.disconnect_device)
        self.get_id_button.clicked.connect(self.get_device_id)
        self.catalog_button.clicked.connect(self.get_catalog)
        self.browse_dir_button.clicked.connect(self.browse_directory)
        self.change_dir_button.clicked.connect(self.change_directory)

        # 点测模式按钮
        self.point_acquire_button.clicked.connect(self.point_acquire)
        self.point_start_button.clicked.connect(self.start_point_measurement)  # 使用实际存在的方法名
        self.point_stop_button.clicked.connect(self.stop_point_measurement)    # 使用实际存在的方法名

        # 定次采集模式按钮
        self.fixed_start_button.clicked.connect(self.start_fixed_acquire)

        # 连续采集模式按钮
        self.continuous_start_button.clicked.connect(self.start_continuous_acquire)
        self.continuous_stop_button.clicked.connect(self.stop_continuous_acquire)

        # 添加模式切换时重置点测计数器
        # 注意：由于现在使用ComboBoxSettingCard，我们需要连接到配置项的valueChanged信号
        self.mode_config.Mode.valueChanged.connect(self.reset_point_counter_on_mode_change)

    def reset_point_counter(self, checked):
        """重置点测计数器"""
        if checked:
            self.point_sample_counter = 0
            self.point_group_counter = 0

    def reset_point_counter_on_mode_change(self, value):
        """当模式切换到点测模式时重置点测计数器"""
        if value == "point":
            self.point_sample_counter = 0
            self.point_group_counter = 0

    def on_mode_changed(self):
        """采集模式改变时的处理"""
        # 如果从点测模式切换到其他模式，需要关闭点测
        if self.mode_config.Mode.value != "point" and self.is_point_running:
            self.is_point_running = False
            
        if self.mode_config.Mode.value == "point":
            self.mode_stacked_widget.setCurrentIndex(0)
        elif self.mode_config.Mode.value == "fixed":
            self.mode_stacked_widget.setCurrentIndex(1)
        elif self.mode_config.Mode.value == "continuous":
            self.mode_stacked_widget.setCurrentIndex(2)

    def refresh_devices(self):
        """刷新设备列表"""
        try:
            # 确保控制器已初始化
            if self.vna_controller is None:
                self.vna_controller = VNAController()

            devices = self.vna_controller.list_devices()
            self.device_combo.clear()
            for device in devices:
                self.device_combo.addItem(device)
            self.log_message(f"找到 {len(devices)} 个设备")
            self.log_message("注意：如使用VISA虚拟地址连接，请先通过VNA前面板软件连接获取VISA地址")

            # 显示信息提示条
            InfoBar.success(
                title='刷新完成',
                content=f'找到 {len(devices)} 个设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.log_message(f"刷新设备时出错: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"刷新设备时出错: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )

    def connect_device(self):
        """连接到选定的设备"""
        resource_name = self.device_combo.currentText()
        print(f"device name: {resource_name}")

        if not resource_name:
            InfoBar.warning(
                title='错误',
                content="请选择或输入设备地址",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        try:
            # 创建新的控制器实例
            new_controller = VNAController()
            device = new_controller.open_device(resource_name)

            if device:
                # 成功连接后，替换旧的控制器
                old_controller = self.vna_controller
                self.vna_controller = new_controller

                # 安全地关闭旧控制器
                if old_controller:
                    try:
                        old_controller.close_device()
                        del old_controller
                    except Exception as e:
                        self.log_message(f"关闭旧设备时出错: {str(e)}")

                self.device_connected = True
                self.log_message(f"成功连接到设备: {resource_name}")
                InfoBar.success(
                    title='连接成功',
                    content=f'已连接到: {resource_name}',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                self.update_ui_state()
            else:
                # 连接失败，清理新创建的控制器
                # try:
                    # new_controller.close_device()
                    # del new_controller
                # except Exception:
                #     pass
                self.log_message(f"无法连接到设备: {resource_name}")
                InfoBar.error(
                    title='错误',
                    content=f"无法连接到设备: {resource_name}",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1000,
                    parent=self
                )
                # 确保即使连接失败也不会导致程序退出
                return

        except visa.VisaIOError as e:
            self.log_message(f"连接设备时VISA IO错误: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"连接设备时VISA IO错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
        except visa.VisaTypeError as e:
            self.log_message(f"连接设备时VISA类型错误: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"连接设备时VISA类型错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
        except Exception as e:
            self.log_message(f"连接设备时出错: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"连接设备时出错: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
        except BaseException as e:
            # 捕获所有可能的异常，防止程序中断
            self.log_message(f"连接设备时发生严重错误: {str(e)}")
            InfoBar.error(
                title='严重错误',
                content=f"连接设备时发生严重错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )

    def disconnect_device(self):
        """断开设备连接"""
        if self.vna_controller and self.device_connected:
            try:
                self.vna_controller.close_device()
                self.device_connected = False
                self.log_message("设备已断开连接")
                InfoBar.success(
                    title='断开连接',
                    content='设备已断开连接',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                self.update_ui_state()
            except Exception as e:
                self.log_message(f"断开设备连接时出错: {str(e)}")
                InfoBar.error(
                    title='错误',
                    content=f"断开设备连接时出错: {str(e)}",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1000,
                    parent=self
                )
        else:
            self.log_message("没有设备连接")

    def update_ui_state(self):
        """更新UI控件的启用/禁用状态"""
        # 更新连接相关按钮状态
        self.connect_button.setEnabled(not self.device_connected)
        self.disconnect_button.setEnabled(self.device_connected)
        
        # 更新设备控制按钮状态
        device_control_enabled = self.device_connected
        self.get_id_button.setEnabled(device_control_enabled)
        self.catalog_button.setEnabled(device_control_enabled)
        self.browse_dir_button.setEnabled(device_control_enabled)
        self.change_dir_button.setEnabled(device_control_enabled)
        
        # 更新采集模式按钮状态
        # 点测模式按钮
        self.point_acquire_button.setEnabled(device_control_enabled and self.is_point_running)  # 只有在点测模式运行时才启用
        self.point_start_button.setEnabled(device_control_enabled and not self.is_point_running)
        self.point_stop_button.setEnabled(device_control_enabled and self.is_point_running)
        
        # 定次采集模式按钮
        self.fixed_start_button.setEnabled(device_control_enabled and not self.is_continuous_running)
        
        # 连续采集模式按钮
        self.continuous_start_button.setEnabled(device_control_enabled and not self.is_continuous_running)
        self.continuous_stop_button.setEnabled(device_control_enabled and self.is_continuous_running)

    def start_point_measurement(self):
        """开始点测采集"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='请先连接设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        # 更新UI状态
        self.point_acquire_button.setEnabled(True)  # 启用单次采集按钮
        self.point_start_button.setEnabled(False)
        self.point_stop_button.setEnabled(True)
        self.fixed_start_button.setEnabled(False)
        self.continuous_start_button.setEnabled(False)
        self.is_point_running = True
        self.log_message(f"点测模式已开启")

    def stop_point_measurement(self):
        """停止点测采集"""
        # 更新UI状态
        self.point_acquire_button.setEnabled(False)
        self.point_start_button.setEnabled(True)
        self.point_stop_button.setEnabled(False)
        self.fixed_start_button.setEnabled(True)
        self.continuous_start_button.setEnabled(True)
        self.is_point_running = False
        self.log_message("点测模式已关闭")

    def update_point_progress(self, current, total):
        """更新点测进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.log_message(f"采集进度: {current}/{total}")

    def start_fixed_acquire(self):
        """开始定次采集"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='请先连接设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        try:
            count = self.fixed_count_spin.value()
            if count <= 0:
                raise ValueError("采集次数必须大于0")
        except ValueError as e:
            InfoBar.error(
                title='输入错误',
                content=f"请输入有效的采集次数: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        # 获取采集参数
        file_prefix = self.file_prefix_line_edit.text()
        if not file_prefix:
            file_prefix = "usbvna"

        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        path = self.path_line_edit.text()

        # 更新UI状态
        self.point_acquire_button.setEnabled(False)
        self.point_start_button.setEnabled(False)
        self.fixed_start_button.setEnabled(False)
        self.continuous_start_button.setEnabled(False)
        self.is_continuous_running = True  # 使用正确的状态变量
        self.progress_bar.setVisible(True)  # 显示进度条
        self.progress_bar.setMaximum(count)
        self.progress_bar.setValue(0)
        self.log_message(f"开始定次数据采集，计划采集数量: {count}...")
        logger.debug(f"开始定次数据采集，计划采集数量: {count}...")

        # 创建并启动定次采集工作线程
        self.fixed_worker = DataDumpWorker(  # 使用正确的Worker类
            self.vna_controller, count, file_prefix, path,
            data_type, scope, data_format, selector, interval)
        self.fixed_worker.progress_updated.connect(self.update_point_progress)
        self.fixed_worker.finished_signal.connect(self.fixed_acquire_finished)
        self.fixed_worker.start()

    def fixed_acquire_finished(self, success, message):
        """定次采集完成处理"""
        # 重新启用按钮
        self.point_acquire_button.setEnabled(False)
        self.point_start_button.setEnabled(True)
        self.fixed_start_button.setEnabled(True)
        self.continuous_start_button.setEnabled(True)
        self.is_continuous_running = False  # 使用正确的状态变量

        if success:
            self.log_message(f"定次采集完成: {message}")
            logger.debug(f"定次采集完成: {message}")
            InfoBar.success(
                title='采集完成',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            self.log_message(f"定次采集失败: {message}")
            logger.error(f"定次采集失败: {message}")
            InfoBar.error(
                title='采集失败',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 隐藏进度条

        # 清理工作线程引用
        self.fixed_worker = None

    def start_continuous_acquire(self):
        """开始连续采集"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='请先连接设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        # 获取采集参数
        file_prefix = self.file_prefix_line_edit.text()
        if not file_prefix:
            file_prefix = "usbvna"

        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        path = self.path_line_edit.text()

        # 更新UI状态
        self.point_acquire_button.setEnabled(False)
        self.point_start_button.setEnabled(False)
        self.fixed_start_button.setEnabled(False)
        self.continuous_start_button.setEnabled(False)
        self.continuous_stop_button.setEnabled(True)
        self.is_continuous_running = True
        self.progress_bar.setVisible(True)  # 显示进度条
        self.progress_bar.setMaximum(0)  # 设置为不确定模式
        self.log_message("开始连续数据采集...")
        logger.debug("开始连续数据采集...")

        # 创建并启动连续采集工作线程
        self.continuous_worker = ContinuousDumpWorker(
            self.vna_controller, file_prefix, path,
            data_type, scope, data_format, selector, interval)
        self.continuous_worker.progress_updated.connect(self.update_continuous_progress)  # 连接进度更新信号
        self.continuous_worker.finished_signal.connect(self.continuous_acquire_finished)
        self.continuous_worker.start()

    def update_continuous_progress(self, count):
        """更新连续采集进度"""
        self.log_message(f"连续采集进行中，已采集 {count} 道数据...")

    def stop_continuous_acquire(self):
        """停止连续采集"""
        if hasattr(self, 'continuous_worker') and self.continuous_worker is not None:
            self.continuous_worker.stop()
            self.log_message("正在停止连续采集...")
        else:
            self.log_message("没有正在运行的连续采集")

    def continuous_acquire_finished(self, success, message):
        """连续采集完成处理"""
        # 重新启用按钮
        self.point_acquire_button.setEnabled(False)
        self.point_start_button.setEnabled(True)
        self.fixed_start_button.setEnabled(True)
        self.continuous_start_button.setEnabled(True)
        self.continuous_stop_button.setEnabled(False)
        self.is_continuous_running = False

        if success:
            self.log_message(f"连续采集完成: {message}")
            logger.debug(f"连续采集完成: {message}")
            InfoBar.success(
                title='采集完成',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            self.log_message(f"连续采集失败: {message}")
            logger.error(f"连续采集失败: {message}")
            InfoBar.error(
                title='采集失败',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 隐藏进度条

        # 清理工作线程引用
        self.continuous_worker = None

    def point_acquire(self):
        """点测模式单次采集"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='请先连接设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        # 检查是否处于点测模式
        if not self.is_point_running:
            InfoBar.warning(
                title='警告',
                content='请先开启点测模式',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        try:
            count = self.point_count_spin.value()
            if count <= 0:
                raise ValueError("采集次数必须大于0")
        except ValueError as e:
            InfoBar.error(
                title='输入错误',
                content=f"请输入有效的采集次数: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        # 获取采集参数
        file_prefix = self.file_prefix_line_edit.text()
        if not file_prefix:
            file_prefix = "usbvna"

        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        path = self.path_line_edit.text()

        # 更新计数器
        self.point_group_counter += 1  # 每次点击"单次采集"按钮增加一组
        start_index = self.point_sample_counter + 1
        self.point_sample_counter += count  # 增加样本计数

        # 更新UI状态
        self.point_acquire_button.setEnabled(False)
        self.point_start_button.setEnabled(False)  # 保持点测开启状态
        self.point_stop_button.setEnabled(True)   # 保持点测开启状态
        self.fixed_start_button.setEnabled(False)
        self.continuous_start_button.setEnabled(False)
        self.progress_bar.setVisible(True)  # 显示进度条
        self.progress_bar.setMaximum(count)
        self.progress_bar.setValue(0)
        self.log_message(f"开始点测第 {self.point_group_counter} 组数据采集，采集数量: {count}...")

        # 创建并启动点测工作线程
        self.point_worker = SinglePointDumpWorker(
            self.vna_controller, count, file_prefix, path,
            data_type, scope, data_format, selector, interval, start_index)
        logger.debug("启动点测工作线程")
        self.point_worker.progress_updated.connect(self.update_point_progress)
        self.point_worker.finished_signal.connect(self.point_acquire_finished)
        self.point_worker.start()

    def point_acquire_finished(self, success, message):
        """点测采集完成处理"""
        # 重新启用按钮
        self.point_acquire_button.setEnabled(True)
        self.point_start_button.setEnabled(False)  # 保持点测开启状态
        self.point_stop_button.setEnabled(True)   # 保持点测开启状态
        self.fixed_start_button.setEnabled(False)
        self.continuous_start_button.setEnabled(False)
        # 注意：不修改is_point_running状态，保持点测模式开启

        if success:
            self.log_message(f"点测第 {self.point_group_counter} 组采集完成: {message}")
            logger.debug(f"点测第 {self.point_group_counter} 组采集完成: {message}")
            InfoBar.success(
                title='采集完成',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            self.log_message(f"点测第 {self.point_group_counter} 组采集失败: {message}")
            logger.error(f"点测第 {self.point_group_counter} 组采集失败: {message}")
            InfoBar.error(
                title='采集失败',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )


        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 隐藏进度条

        # 清理工作线程引用
        self.point_worker = None

    def get_device_id(self):
        """获取设备ID信息"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='请先连接设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        try:
            response = self.vna_controller.check_instrument_info()
            if response:
                self.log_message(f"设备ID: {response.strip()}")
            else:
                self.log_message("无法获取设备ID信息")
                InfoBar.warning(
                    title='警告',
                    content='无法获取设备ID信息，设备可能不支持此功能',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except visa.VisaIOError as e:
            self.log_message(f"获取设备ID时VISA IO错误: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"获取设备ID时VISA IO错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.log_message(f"获取设备ID时出错: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"获取设备ID时出错: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def get_catalog(self):
        """查看设备目录"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='请先连接设备',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        path = self.path_line_edit.text()
        if not path:
            path = "/"

        try:
            response = self.vna_controller.catalog(path)
            if response:
                self.log_message(f"目录内容 ({path}):")
                # 解析并显示目录内容
                items = response.strip().split(',')
                for item in items:
                    self.log_message(f"  {item}")
            else:
                self.log_message(f"无法获取目录内容 ({path})，设备可能不支持此功能")
                InfoBar.warning(
                    title='警告',
                    content='无法获取目录内容，设备可能不支持此功能',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except visa.VisaIOError as e:
            self.log_message(f"查看目录时VISA IO错误: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"查看目录时VISA IO错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.log_message(f"查看目录时出错: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f"查看目录时出错: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def browse_directory(self):
        """浏览并选择目录"""
        current_path = self.path_line_edit.text()
        directory = QFileDialog.getExistingDirectory(self, "选择目录", current_path)
        if directory:
            self.path_line_edit.setText(directory)

    def change_directory(self):
        """切换设备目录"""
        if self.vna_controller is None or not self.device_connected:
            InfoBar.warning(
                title='警告',
                content='设备未连接',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
            return

        path = self.path_line_edit.text()
        if not path:
            InfoBar.warning(
                title='警告',
                content='请输入目录路径',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            success = self.vna_controller.cdir(path)
            if success:
                self.log_message(f"成功切换到目录: {path}")
                InfoBar.success(
                    title='成功',
                    content=f"成功切换到目录: {path}",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                self.log_message("无法切换目录，设备可能不支持此功能")
                InfoBar.warning(
                    title='警告',
                    content='无法切换目录，设备可能不支持此功能',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except visa.VisaIOError as e:
            self.log_message(f"切换目录时VISA IO错误: {str(e)}")
            InfoBar.warning(
                title='警告',
                content='切换目录时VISA IO错误',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
        except Exception as e:
            self.log_message(f"切换目录时出错: {str(e)}")
            InfoBar.warning(
                title='警告',
                content='切换目录时出错',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1000,
                parent=self
            )
