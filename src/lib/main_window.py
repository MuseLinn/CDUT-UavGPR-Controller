# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2026-01-12 22:04:03
LastEditors  : Linn
LastEditTime : 2026-01-13 11:10:00
FilePath     : \\usbvna\\src\\lib\\main_window.py
Description  : 主窗口类，包含VNA控制器GUI界面

Copyright (c) 2026 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

import os
import sys
# 将src目录添加到Python路径中
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QGroupBox, QLabel, QTextEdit, QStackedWidget,
    QFileDialog, QGridLayout, QScrollArea  # 添加文件对话框和滚动区域支持
)
from PyQt6.QtCore import Qt, QSize, QFileInfo, QEventLoop, QTimer
from PyQt6.QtGui import QFont, QIcon

# 导入PyQt6-Fluent-Widgets组件
from qfluentwidgets import (
    FluentWindow, FluentIcon, PrimaryPushButton, PushButton, EditableComboBox as ComboBox, SpinBox, DoubleSpinBox,
    LineEdit, ProgressBar, SplashScreen,
    InfoBar, InfoBarPosition, FluentIcon as FIF,
    ComboBoxSettingCard, SwitchButton, CheckBox, HeaderCardWidget, BodyLabel,
    CardWidget, GroupHeaderCardWidget, SimpleCardWidget,
    TitleLabel, SubtitleLabel, CaptionLabel,
    SegmentedWidget, SegmentedItem,
    ScrollArea, ImageLabel,
    ColorDialog, Theme
)

# 导入自定义模块
from .logger_config import setup_logger
from .vna_controller import VNAController
from .rtk_module import RTKModule
from .workers import (DataDumpWorker, ContinuousDumpWorker, PointDumpWorker, SinglePointDumpWorker)
from .rtk_status import RTKStatusBar

# NOTE: 创建日志记录器
logger = setup_logger("vna_window", "logs/vna_window.log", level=10)  # 10对应DEBUG级别

class VNAControllerGUI(FluentWindow):
    def __init__(self):
        """初始化VNA控制器GUI界面"""
        super().__init__()

        # 初始化VNA控制器为None，稍后再初始化
        self.status_group = None
        self.mode_combo_card = None
        self.continuous_mode_page = None
        self.fixed_mode_page = None
        self.point_mode_page = None
        self.vna_controller = None
        self.device_connected = False

        # 初始化各种工作线程
        self.fixed_worker = None  # 定次采集工作线程
        self.continuous_worker = None  # 连续采集工作线程
        self.point_worker = None  # 点测采集工作线程

        # 初始化工作状态
        self.is_continuous_running = False  # 连续采集运行状态
        self.is_point_running = False  # 点测采集运行状态

        # 点测模式计数器
        self.point_sample_counter = 0  # 点测样本计数器
        self.point_group_counter = 0  # 点测组计数器

        # 初始化界面组件
        self.homeInterface = None  # 主界面部件
        self.main_layout = None  # 主布局
        self.title_label = None  # 标题标签
        self.device_combo = None  # 设备选择下拉框
        self.refresh_button = None  # 刷新设备按钮
        self.connect_button = None  # 连接设备按钮
        self.disconnect_button = None  # 断开设备按钮
        self.get_id_button = None  # 获取设备ID按钮
        self.catalog_button = None  # 查看目录按钮
        self.path_line_edit = None  # 路径输入框
        self.browse_dir_button = None  # 浏览目录按钮
        self.change_dir_button = None  # 切换目录按钮
        self.data_type_combo = None  # 数据类型下拉框
        self.scope_combo = None  # 范围下拉框
        self.format_combo = None  # 数据格式下拉框
        self.selector_spin = None  # 测量编号选择框
        self.file_prefix_line_edit = None  # 文件前缀输入框
        self.interval_spin = None  # 数据存储间隔时间选择框
        self.point_mode_radio = None  # 点测模式单选按钮
        self.fixed_mode_radio = None  # 定次采集模式单选按钮
        self.continuous_mode_radio = None  # 连续采集模式单选按钮
        self.mode_stacked_widget = None  # 模式堆叠部件
        self.point_acquire_button = None  # 点测采集按钮
        self.point_count_spin = None  # 点测采集数量选择框
        self.point_start_button = None  # 点测开始按钮
        self.point_stop_button = None  # 点测停止按钮
        self.fixed_count_spin = None  # 定次采集数量选择框
        self.fixed_start_button = None  # 定次开始按钮
        self.continuous_start_button = None  # 连续开始按钮
        self.continuous_stop_button = None  # 连续停止按钮
        self.status_text_edit = None  # 状态信息文本框
        self.progress_bar = None  # 进度条

        # RTK相关组件
        self.rtk_port_combo = None  # RTK串口选择下拉框
        self.rtk_baudrate_combo = None  # RTK波特率选择下拉框
        self.rtk_enable_switch = None  # RTK启用开关
        self.rtk_storage_combo = None  # RTK经纬度高程采样存储频率下拉框
        self.rtk_status_bar = None  # RTK状态栏

        # RTK相关属性
        self.rtk_module = None
        self.rtk_enabled = False
        self.rtk_data_file = None
        self.rtk_storage_frequency = 2  # 默认经纬度高程采样存储频率为2Hz
        self.rtk_data_storage_enabled = True  # 添加RTK数据存储开关，默认开启
        
        # 存储最近的RTK数据
        self.latest_rtk_gga_data = {}
        self.latest_rtk_rmc_data = {}
        self.latest_rtk_gsa_data = {}
        
        # 系统定时器，用于更新系统时间
        self.system_timer = None
        
        # 当前采集模式，默认为点测模式
        self.current_mode = "point"

        # 创建界面
        """初始化用户界面组件"""
        # 设置窗口标题和大小
        self.setWindowTitle('低频无人机航空探地雷达装备及配套软件研发')
        self.resize(1200, 900)
        self.setMinimumSize(1000, 700)
        root = QFileInfo(__file__).absolutePath()
        self.setWindowIcon(QIcon(root + '/app_logo.png'))
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
        self.spacing = 15
        
        # 初始化系统定时器，用于更新系统时间
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.update_system_time)
        self.system_timer.start(1000)  # 每秒更新一次

        # 创建主水平布局
        main_h_layout = QHBoxLayout(self.homeInterface)
        main_h_layout.setSpacing(self.spacing)
        main_h_layout.setContentsMargins(20, 20, 20, 20)

        # 创建左侧配置区域（带滚动功能）
        left_scroll_area = ScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll_area.setFixedWidth(450)
        left_scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        self.config_widget = QWidget()
        self.config_widget.setFixedWidth(430)
        self.config_widget.setStyleSheet("background-color: transparent;")
        self.main_layout = QVBoxLayout(self.config_widget)
        self.main_layout.setSpacing(self.spacing)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建标题
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 10, 0, 10)
        
        self.title_label = TitleLabel('CDUT-UavGPR探地雷达采集控制面板')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont('Microsoft YaHei', 11, QFont.Weight.Bold))
        
        title_layout.addWidget(self.title_label)
        
        self.main_layout.addWidget(title_widget)

        # 创建设备控制区域
        self.create_control_section()
        
        # 采集模式区域
        self.create_acquisition_mode_section()
        
        # 创建RTK状态栏（移到左侧）
        self.create_rtk_status_bar()
        if self.rtk_status_bar:
            self.main_layout.addWidget(self.rtk_status_bar)
        
        # 数据采集配置区域
        self.create_data_config_section()

        # 将配置组件添加到滚动区域
        left_scroll_area.setWidget(self.config_widget)

        # 创建右侧状态信息区域
        self.status_widget = QWidget()
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setSpacing(self.spacing)
        status_layout.setContentsMargins(0, 0, 0, 0)

        # 创建状态信息区域（不包含RTK状态栏）
        self.create_status_section()
        status_layout.addWidget(self.status_group)

        # 将左右区域添加到主布局
        main_h_layout.addWidget(left_scroll_area)  # 左侧配置区域使用固定宽度
        main_h_layout.addWidget(self.status_widget, 1)  # 右侧状态区域自动填充剩余空间

        # 添加界面到 FluentWindow
        self.initNavigation()

        # 设置信号连接
        self.setup_connections()
        # 初始化数据选项
        self.init_data_options()
        # 初始化采集模式
        self.init_acquisition_modes()
        # 更新设备状态显示
        self.update_device_status()
        # 显示初始状态信息（现在确保组件已创建）
        self.log_message("系统初始化完成，准备就绪")
        
        # 启动系统时间定时器
        self.start_system_timer()

        # 初始化数据获取方式控件状态
        self.on_data_acquisition_mode_changed()

    def on_data_acquisition_mode_changed(self, index=None):
        """当数据获取方式改变时调用"""
        # 获取当前选中的模式
        if index is None:
            mode_text = self.data_acquisition_combo.currentText()
        else:
            mode_text = self.data_acquisition_combo.itemText(index)
        
        # 根据数据获取方式启用/禁用相关控件
        if mode_text == "实时数据流方式":
            # 实时数据流方式：只启用文件前缀和间隔控件
            self.data_type_combo.setEnabled(False)
            self.scope_combo.setEnabled(False)
            self.format_combo.setEnabled(False)
            self.selector_spin.setEnabled(False)
            self.file_prefix_line_edit.setEnabled(True)
            self.interval_spin.setEnabled(True)
            
            # 启用A-Scan实时显示
            if hasattr(self, 'ascan_display_group'):
                self.ascan_display_group.setEnabled(True)
        else:  # A-Scan分散存储
            # A-Scan分散存储：启用所有控件
            self.data_type_combo.setEnabled(True)
            self.scope_combo.setEnabled(True)
            self.format_combo.setEnabled(True)
            self.selector_spin.setEnabled(True)
            self.file_prefix_line_edit.setEnabled(True)
            self.interval_spin.setEnabled(True)
            
            # 禁用A-Scan实时显示
            if hasattr(self, 'ascan_display_group'):
                self.ascan_display_group.setEnabled(False)
            
            # 显示InfoBar提示
            from qfluentwidgets import InfoBar, InfoBarPosition
            info_bar = InfoBar(
                icon='🔔',
                title='提示',
                content='A-Scan实时显示仅在实时数据流方式下可用',
                orient='horizontal',
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            info_bar.show()
        
        self.log_message(f"数据获取方式已切换到: {mode_text}")

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
        
        # 添加设置界面
        self.setupInterface = QWidget()
        self.setupInterface.setObjectName("setupInterface")
        self.setup_layout = QVBoxLayout(self.setupInterface)
        self.setup_layout.setSpacing(self.spacing)
        self.setup_layout.setContentsMargins(15, 15, 15, 15)
        
        # 设置界面标题
        setup_title = SubtitleLabel('系统设置')
        setup_title.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
        setup_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setup_layout.addWidget(setup_title)
        
        # 使用滚动区域避免界面拥挤
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(self.spacing)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # RTK定位模块设置区域
        rtk_card = CardWidget()
        rtk_layout = QVBoxLayout(rtk_card)
        rtk_layout.setSpacing(self.spacing)
        rtk_layout.setContentsMargins(15, 15, 15, 15)
        
        # RTK标题
        rtk_title = SubtitleLabel('RTK定位模块设置')
        rtk_title.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        rtk_layout.addWidget(rtk_title)
        
        # RTK串口选择和控制行
        rtk_control_layout = QHBoxLayout()
        rtk_port_label = CaptionLabel('RTK串口:')
        self.rtk_port_combo = ComboBox()
        # 获取可用的串口列表
        self.refresh_rtk_ports()
        
        rtk_refresh_button = PushButton('刷新', icon=FIF.SYNC)
        rtk_refresh_button.clicked.connect(self.refresh_rtk_ports)
        
        rtk_enable_label = CaptionLabel('启用:')
        self.rtk_enable_switch = SwitchButton()
        self.rtk_enable_switch.setChecked(False)
        
        # RTK波特率选择
        rtk_baudrate_label = CaptionLabel('波特率:')
        self.rtk_baudrate_combo = ComboBox()
        # 获取支持的波特率列表
        supported_baudrates = RTKModule.get_baudrates()
        baudrate_strings = [str(b) for b in supported_baudrates]
        self.rtk_baudrate_combo.addItems(baudrate_strings)
        self.rtk_baudrate_combo.setCurrentText('115200')  # 设置默认值为115200
        
        rtk_control_layout.addWidget(rtk_port_label)
        rtk_control_layout.addWidget(self.rtk_port_combo)
        rtk_control_layout.addWidget(rtk_refresh_button)
        rtk_control_layout.addWidget(rtk_baudrate_label)
        rtk_control_layout.addWidget(self.rtk_baudrate_combo)
        rtk_control_layout.addWidget(rtk_enable_label)
        rtk_control_layout.addWidget(self.rtk_enable_switch)
        rtk_control_layout.addStretch()
        
        # RTK经纬度高程采样存储频率选择和存储开关
        rtk_storage_layout = QHBoxLayout()
        rtk_storage_label = CaptionLabel('经纬度高程数据采样频率:')
        self.rtk_storage_combo = ComboBox()
        self.rtk_storage_combo.addItems(['1Hz', '2Hz', '5Hz', '10Hz', '20Hz'])
        self.rtk_storage_combo.setCurrentText('2Hz')
        
        # 添加RTK数据存储开关
        rtk_data_storage_label = CaptionLabel('存储RTK数据:')
        self.rtk_data_storage_switch = SwitchButton()
        self.rtk_data_storage_switch.setChecked(True)  # 默认开启存储
        
        rtk_storage_layout.addWidget(rtk_storage_label)
        rtk_storage_layout.addWidget(self.rtk_storage_combo)
        rtk_storage_layout.addWidget(rtk_data_storage_label)
        rtk_storage_layout.addWidget(self.rtk_data_storage_switch)
        rtk_storage_layout.addStretch()
        
        rtk_layout.addLayout(rtk_control_layout)
        rtk_layout.addLayout(rtk_storage_layout)
        
        # 数据采集设置区域
        acquisition_card = CardWidget()
        acquisition_layout = QVBoxLayout(acquisition_card)
        acquisition_layout.setSpacing(self.spacing)
        acquisition_layout.setContentsMargins(15, 15, 15, 15)
        
        # 数据采集设置标题
        acquisition_title = SubtitleLabel('数据采集设置')
        acquisition_title.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        acquisition_layout.addWidget(acquisition_title)
        
        # 数据获取方式设置
        # 创建一个美观的设置项
        data_acquisition_widget = QWidget()
        data_acquisition_layout = QVBoxLayout(data_acquisition_widget)
        data_acquisition_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加标题和内容
        title_label = CaptionLabel("数据获取方式")
        content_label = BodyLabel("选择A-Scan数据的获取和存储方式")
        
        # 添加ComboBox
        self.data_acquisition_combo = ComboBox()
        self.data_acquisition_combo.addItems(['A-Scan分散存储', '实时数据流方式'])
        self.data_acquisition_combo.setCurrentIndex(1)  # 默认使用实时数据流方式
        self.data_acquisition_combo.currentIndexChanged.connect(self.on_data_acquisition_mode_changed)
        self.data_acquisition_combo.setMinimumWidth(200)
        
        data_acquisition_layout.addWidget(title_label)
        data_acquisition_layout.addWidget(content_label)
        data_acquisition_layout.addWidget(self.data_acquisition_combo)
        
        acquisition_layout.addWidget(data_acquisition_widget)
        
        scroll_layout.addWidget(rtk_card)
        scroll_layout.addWidget(acquisition_card)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        self.setup_layout.addWidget(scroll_area)
        
        # 添加设置界面到导航栏
        self.addSubInterface(self.setupInterface, FIF.SETTING, '设置')

    def log_message(self, message):
        """在状态文本框中添加日志消息"""
        if hasattr(self, 'status_text_edit') and self.status_text_edit is not None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S:%f")
            self.status_text_edit.append(f"[{timestamp}] {message}")
            # 滚动到底部
            self.status_text_edit.verticalScrollBar().setValue(
                self.status_text_edit.verticalScrollBar().maximum()
            )

    def create_control_section(self):
        """创建设备控制区域"""
        # 创建连接区域容器
        connection_card = CardWidget()
        connection_layout = QVBoxLayout(connection_card)
        connection_layout.setSpacing(self.spacing)
        connection_layout.setContentsMargins(15, 15, 15, 15)
        
        # 设备控制标题
        control_label = SubtitleLabel('设备控制')
        control_label.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        connection_layout.addWidget(control_label)

        # 设备连接控件
        device_layout = QHBoxLayout()
        
        device_label = CaptionLabel('设备地址:')
        self.device_combo = ComboBox()
        # PyQt6-Fluent-Widgets EditableComboBox是可编辑的，只需设置LineEdit为可编辑即可
        self.device_combo.addItems(['TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR'])
        self.device_combo.setCurrentText('TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR')
        self.device_combo.setMinimumWidth(250)

        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo, 1)  # 添加拉伸因子，占满剩余空间
        connection_layout.addLayout(device_layout)

        # 控制按钮布局
        button_layout = QHBoxLayout()
        
        self.refresh_button = PushButton('刷新', icon=FIF.SYNC)
        self.connect_button = PrimaryPushButton('连接', icon=FIF.CONNECT)
        self.disconnect_button = PushButton('断开', icon=FIF.CLOSE)
        self.disconnect_button.setEnabled(False)
        self.get_id_button = PushButton('获取ID', icon=FIF.INFO)
        self.get_id_button.setEnabled(False)

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        button_layout.addWidget(self.get_id_button)
        
        connection_layout.addLayout(button_layout)

        self.main_layout.addWidget(connection_card)

        # RTK控制区域
        # RTK设置已移至设置界面

    def refresh_rtk_ports(self):
        """刷新RTK串口列表"""
        self.log_message("刷新RTK串口列表")
        
        # 显示刷新开始的InfoBar
        from qfluentwidgets import InfoBar, InfoBarPosition
        info_bar = InfoBar(
            icon=FIF.SYNC,
            title='刷新串口',
            content='正在扫描可用的串口...',
            orient='horizontal',
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        info_bar.show()
        
        # 保存当前选择的串口（如果存在）
        current_port = self.rtk_port_combo.currentText() if self.rtk_port_combo.count() > 0 else None
        
        # 清空现有列表
        self.rtk_port_combo.clear()
        
        try:
            # 获取可用的串口列表
            available_ports = RTKModule.list_available_ports()
            if available_ports:
                self.rtk_port_combo.addItems(available_ports)
                # 尝试恢复之前选择的串口，如果不存在则选择第一个
                if current_port and current_port in available_ports:
                    self.rtk_port_combo.setCurrentText(current_port)
                else:
                    self.rtk_port_combo.setCurrentText(available_ports[0])
                self.log_message(f"发现 {len(available_ports)} 个可用串口")
                
                # 显示成功的InfoBar
                success_info_bar = InfoBar.success(
                    title='刷新成功',
                    content=f'发现 {len(available_ports)} 个可用串口',
                    orient='horizontal',
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                success_info_bar.show()
            else:
                # 如果没有检测到串口，则留空并提示
                common_ports = ['No Available Serial Port']
                self.rtk_port_combo.addItems(common_ports)
                self.log_message("未发现可用串口，使用默认串口列表")
                
                # 显示警告的InfoBar
                warning_info_bar = InfoBar.warning(
                    title='未发现串口',
                    content='未发现可用串口，使用默认串口列表',
                    orient='horizontal',
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                warning_info_bar.show()
        except Exception as e:
            error_message = f"刷新RTK串口列表失败: {str(e)}"
            self.log_message(error_message)
            # 出错时使用模拟数据
            self.rtk_port_combo.clear()
            self.rtk_port_combo.addItems(['COM11'])
            self.rtk_port_combo.setCurrentText('COM11')
            
            # 显示错误的InfoBar
            error_info_bar = InfoBar.error(
                title='刷新失败',
                content=error_message,
                orient='horizontal',
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            error_info_bar.show()

    def create_data_config_section(self):
        """创建数据采集配置区域"""
        # 创建存储配置卡片
        storage_card = CardWidget()
        storage_layout = QVBoxLayout(storage_card)
        storage_layout.setSpacing(self.spacing)
        storage_layout.setContentsMargins(15, 15, 15, 15)
        
        # 数据配置标题
        config_label = SubtitleLabel('A-scan采集配置')
        config_label.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        storage_layout.addWidget(config_label)

        # 设备控制按钮
        path_layout = QVBoxLayout()

        # 存储路径输入行
        path_input_layout = QHBoxLayout()
        path_label = CaptionLabel('存储路径:')
        self.path_line_edit = LineEdit()
        # 自动根据电脑用户设置默认的路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Documents")
        self.path_line_edit.setText(desktop_path)
        self.path_line_edit.setMinimumWidth(300)
        path_input_layout.addWidget(path_label)
        path_input_layout.addWidget(self.path_line_edit, 1)

        # 按钮行
        path_buttons_layout = QHBoxLayout()
        self.catalog_button = PushButton('查看目录', icon=FIF.FOLDER)
        self.catalog_button.setEnabled(False)
        self.browse_dir_button = PushButton('选择目录', icon=FIF.FOLDER)
        self.browse_dir_button.setEnabled(False)
        self.change_dir_button = PushButton('切换目录', icon=FIF.FOLDER)
        self.change_dir_button.setEnabled(False)
        path_buttons_layout.addWidget(self.catalog_button)
        path_buttons_layout.addWidget(self.browse_dir_button)  # 添加浏览按钮
        path_buttons_layout.addWidget(self.change_dir_button)

        path_layout.addLayout(path_input_layout)
        path_layout.addLayout(path_buttons_layout)
        
        storage_layout.addLayout(path_layout)

        self.main_layout.addWidget(storage_card)

        # 创建配置参数卡片
        config_card = CardWidget()
        config_layout = QVBoxLayout(config_card)
        config_layout.setSpacing(self.spacing)
        config_layout.setContentsMargins(15, 15, 15, 15)

        # 使用垂直布局，利用上下滚动空间
        config_items_layout = QVBoxLayout()
        config_items_layout.setSpacing(10)

        # 数据类型设置
        data_type_layout = QHBoxLayout()
        data_type_label = CaptionLabel('数据类型:')
        data_type_label.setMinimumWidth(100)
        self.data_type_combo = ComboBox()
        self.data_type_combo.addItems([
            "CSV Formatted Data",
            "SDP Formatted Data",
            "SNP Formatted Data"
        ])
        self.data_type_combo.setMinimumWidth(250)
        data_type_layout.addWidget(data_type_label)
        data_type_layout.addWidget(self.data_type_combo)
        config_items_layout.addLayout(data_type_layout)

        # 范围设置
        scope_layout = QHBoxLayout()
        scope_label = CaptionLabel('范围:')
        scope_label.setMinimumWidth(100)
        self.scope_combo = ComboBox()
        self.scope_combo.addItems([
            "Trace",
            "Displayed",
            "Channel",
            "Auto"
        ])
        self.scope_combo.setMinimumWidth(250)
        scope_layout.addWidget(scope_label)
        scope_layout.addWidget(self.scope_combo)
        config_items_layout.addLayout(scope_layout)

        # 数据格式设置
        format_layout = QHBoxLayout()
        format_label = CaptionLabel('数据格式:')
        format_label.setMinimumWidth(100)
        self.format_combo = ComboBox()
        self.format_combo.addItems([
            "Displayed",
            "RI",  # Real Imaginary
            "MA",  # Magnitude Angle
            "DB"  # Decibel Angle
        ])
        self.format_combo.setMinimumWidth(250)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        config_items_layout.addLayout(format_layout)

        # 测量编号设置
        selector_layout = QHBoxLayout()
        selector_label = CaptionLabel('测量编号:')
        selector_label.setMinimumWidth(100)
        self.selector_spin = SpinBox()
        self.selector_spin.setRange(-1, 100)
        self.selector_spin.setValue(-1)
        self.selector_spin.setMinimumWidth(150)
        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.selector_spin)
        config_items_layout.addLayout(selector_layout)

        # 文件前缀设置
        file_prefix_layout = QHBoxLayout()
        file_prefix_label = CaptionLabel('文件前缀:')
        file_prefix_label.setMinimumWidth(100)
        self.file_prefix_line_edit = LineEdit()
        self.file_prefix_line_edit.setText('lineData')
        self.file_prefix_line_edit.setMinimumWidth(250)
        file_prefix_layout.addWidget(file_prefix_label)
        file_prefix_layout.addWidget(self.file_prefix_line_edit)
        config_items_layout.addLayout(file_prefix_layout)

        # 存储间隔设置
        interval_layout = QHBoxLayout()
        interval_label = CaptionLabel('存储间隔(s):')
        interval_label.setMinimumWidth(100)
        self.interval_spin = DoubleSpinBox()
        self.interval_spin.setRange(0.005, 10.00)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setSingleStep(0.01)
        self.interval_spin.setValue(0.08)
        self.interval_spin.setMinimumWidth(150)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        config_items_layout.addLayout(interval_layout)

        # 添加布局到配置卡片
        config_layout.addLayout(config_items_layout)

        self.main_layout.addWidget(config_card)

    def create_acquisition_mode_section(self):
        """创建采集模式区域"""
        # 创建采集模式选择区域
        mode_card = CardWidget()
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setSpacing(self.spacing)
        mode_layout.setContentsMargins(15, 15, 15, 15)
        
        # 采集模式标题
        mode_label = SubtitleLabel('采集模式')
        mode_label.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        mode_layout.addWidget(mode_label)
        
        # 创建模式选择标签和组合框
        mode_select_layout = QHBoxLayout()
        mode_select_label = CaptionLabel('选择数据采集模式:')
        mode_select_layout.addWidget(mode_select_label)
        
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(['点测模式', '定次采集模式', '连续采集模式'])
        self.mode_combo.setCurrentIndex(2)  # 默认连续采集模式
        # 连接模式变化信号
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_select_layout.addWidget(self.mode_combo)
        
        mode_select_layout.addStretch()  # 添加弹性空间，将组合框推到右边
        mode_layout.addLayout(mode_select_layout)
        
        # 将模式选择区域添加到主布局
        self.main_layout.addWidget(mode_card)

        # 模式堆叠部件
        self.mode_stacked_widget = QStackedWidget()

        # 点测模式页面
        self.point_mode_page = CardWidget()
        point_layout = QHBoxLayout(self.point_mode_page)
        point_layout.setSpacing(self.spacing)  # 设置控件间距
        point_layout.setContentsMargins(15, 15, 15, 15)  # 设置边距

        self.point_acquire_button = PrimaryPushButton('单次采集')  # 修改按钮名称
        self.point_acquire_button.setEnabled(False)

        point_count_label = CaptionLabel('每次采集道数:')
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
        self.fixed_mode_page = CardWidget()
        fixed_layout = QHBoxLayout(self.fixed_mode_page)
        fixed_layout.setSpacing(self.spacing)  # 设置控件间距
        fixed_layout.setContentsMargins(15, 15, 15, 15)  # 设置边距

        fixed_count_label = CaptionLabel('采集次数:')
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
        self.continuous_mode_page = CardWidget()
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
        # 创建状态区域容器
        self.status_group = CardWidget()
        status_group_layout = QVBoxLayout(self.status_group)
        status_group_layout.setSpacing(self.spacing)
        status_group_layout.setContentsMargins(15, 15, 15, 15)

        # 创建A-Scan实时显示区域（放在上方）
        self.create_ascan_display()
        if hasattr(self, 'ascan_display_group'):
            status_group_layout.addWidget(self.ascan_display_group)

        # 添加运行状态标题
        status_title = TitleLabel('运行状态')
        status_title.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        status_group_layout.addWidget(status_title)

        # 状态文本框
        self.status_text_edit = QTextEdit()
        self.status_text_edit.setMinimumHeight(80)
        self.status_text_edit.setReadOnly(True)
        self.status_text_edit.setStyleSheet("QTextEdit { border: 1px solid #e0e0e0; border-radius: 4px; }")
        status_group_layout.addWidget(self.status_text_edit)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 默认隐藏进度条
        status_group_layout.addWidget(self.progress_bar)

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

        # RTK控制连接
        self.rtk_enable_switch.checkedChanged.connect(self.toggle_rtk_module)
        self.rtk_storage_combo.currentTextChanged.connect(self.change_rtk_storage_frequency)

        # 点测模式按钮
        self.point_acquire_button.clicked.connect(self.point_acquire)
        self.point_start_button.clicked.connect(self.start_point_measurement)  # 使用实际存在的方法名
        self.point_stop_button.clicked.connect(self.stop_point_measurement)  # 使用实际存在的方法名

        # 定次采集模式按钮
        self.fixed_start_button.clicked.connect(self.start_fixed_acquire)

        # 连续采集模式按钮
        self.continuous_start_button.clicked.connect(self.start_continuous_acquire)
        self.continuous_stop_button.clicked.connect(self.stop_continuous_acquire)

    def toggle_rtk_module(self, checked):
        """开关RTK模块"""
        if checked:
            self.log_message("正在启用RTK模块...")
            # 禁用开关防止重复操作
            self.rtk_enable_switch.setEnabled(False)
            
            # 使用QThread在后台线程中启用RTK模块，避免阻塞主线程
            from PyQt6.QtCore import QThread, pyqtSignal
            
            class RTKEnableThread(QThread):
                """在后台线程中启用RTK模块的线程类"""
                
                # 定义信号
                success = pyqtSignal(str, str)  # 成功信号，传递串口和波特率
                failure = pyqtSignal(str)  # 失败信号，传递错误信息
                
                def __init__(self, parent, selected_port, selected_baudrate):
                    super().__init__(parent)
                    self.selected_port = selected_port
                    self.selected_baudrate = selected_baudrate
                    self.parent = parent
                
                def run(self):
                    """线程运行函数"""
                    try:
                        # 更新RTK模块实例
                        self.parent.rtk_module = RTKModule(port=self.selected_port, baudrate=self.selected_baudrate)
                        
                        # 先连接信号再启动模块，确保不会错过任何数据
                        self.parent.rtk_module.rtk_data_updated.connect(self.parent.update_rtk_data)
                        self.parent.rtk_module.rtk_error_occurred.connect(self.parent.handle_rtk_error)
                        self.parent.rtk_module.rtk_module_info_received.connect(self.parent.display_rtk_module_info)

                        # 启动RTK模块
                        if self.parent.rtk_module.connect():
                            if self.parent.rtk_module.start():
                                self.parent.rtk_enabled = True
                                
                                # 如果RTK数据存储已启用，则设置数据文件
                                if self.parent.rtk_data_storage_enabled:
                                    self.parent.setup_rtk_data_file()
                                    
                                # 设置RTK模块的采样频率
                                current_frequency_text = self.parent.rtk_storage_combo.currentText()
                                self.parent.change_rtk_storage_frequency(current_frequency_text)
                                
                                # 重新配置定时器：不完全停止，而是降低频率
                                if self.parent.system_timer and self.parent.system_timer.isActive():
                                    self.parent.system_timer.stop()
                                    # 设置一个备用定时器，以防RTK数据中断
                                    self.parent.system_timer.start(5000)  # 每5秒更新一次作为备用
                                
                                self.success.emit(self.selected_port, str(self.selected_baudrate))
                            else:
                                # 启动失败，清理资源
                                self.parent.rtk_module.rtk_data_updated.disconnect()
                                self.parent.rtk_module.rtk_error_occurred.disconnect()
                                self.parent.rtk_module.rtk_module_info_received.disconnect()
                                self.failure.emit("启动RTK模块失败")
                        else:
                            # 连接失败，清理资源
                            self.parent.rtk_module.rtk_data_updated.disconnect()
                            self.parent.rtk_module.rtk_error_occurred.disconnect()
                            self.parent.rtk_module.rtk_module_info_received.disconnect()
                            self.failure.emit("连接RTK模块失败")
                    except Exception as e:
                        self.failure.emit(f"启用RTK模块失败: {str(e)}")
            
            # 获取选择的串口和波特率
            selected_port = self.rtk_port_combo.currentText()
            selected_baudrate = int(self.rtk_baudrate_combo.currentText())
            
            # 创建并启动线程
            self.rtk_enable_thread = RTKEnableThread(self, selected_port, selected_baudrate)
            self.rtk_enable_thread.success.connect(self.on_rtk_enable_success)
            self.rtk_enable_thread.failure.connect(self.on_rtk_enable_failure)
            self.rtk_enable_thread.finished.connect(lambda: self.rtk_enable_switch.setEnabled(True))
            self.rtk_enable_thread.start()
        else:
            self.log_message("正在禁用RTK模块...")
            # 禁用开关防止重复操作
            self.rtk_enable_switch.setEnabled(False)
            
            # 使用QThread在后台线程中禁用RTK模块，避免阻塞主线程
            from PyQt6.QtCore import QThread, pyqtSignal
            
            class RTKDisableThread(QThread):
                """在后台线程中禁用RTK模块的线程类"""
                
                # 定义信号
                finished = pyqtSignal()  # 完成信号
                
                def __init__(self, parent):
                    super().__init__(parent)
                    self.parent = parent
                
                def run(self):
                    """线程运行函数"""
                    try:
                        # 关闭RTK数据文件
                        if self.parent.rtk_module and self.parent.rtk_data_file:
                            self.parent.rtk_module.close_data_file()
                            self.parent.rtk_data_file = None
                        
                        # 断开RTK模块
                        if self.parent.rtk_module:
                            self.parent.rtk_module.disconnect()
                            try:
                                self.parent.rtk_module.rtk_data_updated.disconnect()
                                self.parent.rtk_module.rtk_error_occurred.disconnect()
                                self.parent.rtk_module.rtk_module_info_received.disconnect()
                            except TypeError:
                                # 如果信号未连接就断开，会抛出TypeError，忽略即可
                                pass
                            self.parent.rtk_enabled = False
                            port = self.parent.rtk_port_combo.currentText()
                            self.parent.log_message(f"RTK模块已禁用 (串口: {port})")
                            
                            # 恢复系统定时器为正常频率
                            if self.parent.system_timer:
                                self.parent.system_timer.stop()
                                self.parent.system_timer.start(1000)  # 恢复每秒更新
                        
                        self.finished.emit()
                    except Exception as e:
                        self.parent.log_message(f"禁用RTK模块时出错: {str(e)}")
                        self.finished.emit()
            
            # 创建并启动线程
            self.rtk_disable_thread = RTKDisableThread(self)
            self.rtk_disable_thread.finished.connect(self.on_rtk_disable_finished)
            self.rtk_disable_thread.start()
    
    def on_rtk_enable_success(self, port, baudrate):
        """RTK模块启用成功后的处理"""
        self.log_message("RTK模块已启用")
        InfoBar.success(
            title='RTK模块',
            content=f'RTK模块已在 {port} 上启用，波特率: {baudrate}',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def on_rtk_enable_failure(self, error_msg):
        """RTK模块启用失败后的处理"""
        self.log_message(error_msg)
        InfoBar.error(
            title='RTK模块',
            content=error_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        self.rtk_enable_switch.setChecked(False)
    
    def on_rtk_disable_finished(self):
        """RTK模块禁用完成后的处理"""
        # 重新启用开关
        self.rtk_enable_switch.setEnabled(True)
        # 显示信息
        port = self.rtk_port_combo.currentText()
        InfoBar.info(
            title='RTK已禁用',
            content=f'RTK模块已从串口 {port} 断开',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def toggle_rtk_data_storage(self, checked):
        """开关RTK数据存储"""
        self.rtk_data_storage_enabled = checked
        if self.rtk_enabled:
            if checked:
                # 启用RTK数据存储
                self.setup_rtk_data_file()
                self.log_message("RTK数据存储已启用")
            else:
                # 禁用RTK数据存储
                if self.rtk_module:
                    self.rtk_module.close_data_file()
                    self.rtk_data_file = None
                self.log_message("RTK数据存储已禁用")

    def setup_rtk_data_file(self):
        """设置RTK数据文件"""
        # 获取当前路径
        current_path = self.path_line_edit.text()
        # 创建RTK数据目录
        rtk_data_dir = os.path.join(current_path, "rtk_data")
        if not os.path.exists(rtk_data_dir):
            os.makedirs(rtk_data_dir)
        # 生成文件名
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rtk_data_filename = os.path.join(rtk_data_dir, f"rtk_data_{timestamp}.csv")
        # 设置RTK数据文件
        if self.rtk_module:
            self.rtk_data_file = self.rtk_module.set_data_file(rtk_data_filename)
            if self.rtk_data_file:
                self.log_message(f"RTK数据文件已创建: {rtk_data_filename}")

    def change_rtk_storage_frequency(self, frequency_text):
        """改变RTK存储频率"""
        # 从文本中提取频率值
        frequency = int(frequency_text.replace('Hz', ''))
        self.rtk_storage_frequency = frequency
        # 更新RTK模块的采样频率
        if self.rtk_module:
            self.rtk_module.set_storage_frequency(frequency)
        self.log_message(f"RTK存储频率已设置为: {frequency}Hz")

    def update_rtk_data(self, data):
        """更新RTK数据"""
        # 根据数据类型更新不同的RTK数据
        if 'type' in data:
            data_type = data['type']
            if data_type == 'GGA':
                self.latest_rtk_gga_data = data
            elif data_type == 'RMC':
                self.latest_rtk_rmc_data = data
            elif data_type == 'GSA':
                self.latest_rtk_gsa_data = data
        
        # 更新RTK状态栏
        if self.rtk_status_bar:
            # 合并所有RTK数据
            combined_data = {}
            combined_data.update(self.latest_rtk_gga_data)
            combined_data.update(self.latest_rtk_rmc_data)
            combined_data.update(self.latest_rtk_gsa_data)
            # 更新显示
            self.rtk_status_bar.update_display(combined_data)

    def handle_rtk_error(self, error_message):
        """处理RTK错误"""
        self.log_message(f"RTK错误: {error_message}")
        InfoBar.error(
            title='RTK错误',
            content=error_message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def display_rtk_module_info(self, info):
        """显示RTK模块信息"""
        self.log_message(f"RTK模块信息: {info}")

    def create_rtk_status_bar(self):
        """创建RTK状态栏"""
        self.rtk_status_bar = RTKStatusBar()

    def create_ascan_display(self):
        """创建A-Scan实时显示区域"""
        import pyqtgraph as pg
        
        # 创建A-Scan显示组
        self.ascan_display_group = CardWidget()
        ascan_layout = QVBoxLayout(self.ascan_display_group)
        ascan_layout.setSpacing(self.spacing)
        ascan_layout.setContentsMargins(15, 15, 15, 15)
        
        # A-Scan显示标题
        ascan_title = SubtitleLabel('A-Scan实时显示')
        ascan_title.setFont(QFont('Microsoft YaHei', 10, QFont.Weight.Bold))
        ascan_layout.addWidget(ascan_title)
        
        # 创建pyqtgraph图形布局
        self.ascan_plot_widget = pg.GraphicsLayoutWidget()
        self.ascan_plot_widget.setMinimumHeight(200)
        
        # 添加绘图项
        self.ascan_plot = self.ascan_plot_widget.addPlot(title='A-Scan时域波形')
        self.ascan_curve = self.ascan_plot.plot([], [], pen='b', lineWidth=2)
        
        # 设置坐标轴
        self.ascan_plot.setLabel('bottom', '采样点')
        self.ascan_plot.setLabel('left', '幅度')
        self.ascan_plot.setXRange(0, 500)
        self.ascan_plot.setYRange(-1, 1)
        
        # 添加控制选项
        control_layout = QHBoxLayout()
        
        # 抽样显示选项
        self.sampling_checkbox = CheckBox('抽样显示')
        self.sampling_checkbox.setChecked(True)
        
        # 抽样间隔
        self.sampling_spinbox = SpinBox()
        self.sampling_spinbox.setRange(1, 100)
        self.sampling_spinbox.setValue(10)
        self.sampling_spinbox.setMinimumWidth(80)
        
        control_layout.addWidget(self.sampling_checkbox)
        control_layout.addWidget(CaptionLabel('抽样间隔:'))
        control_layout.addWidget(self.sampling_spinbox)
        control_layout.addStretch()
        
        ascan_layout.addWidget(self.ascan_plot_widget)
        ascan_layout.addLayout(control_layout)

    def update_ascan_display(self, data):
        """更新A-Scan实时显示"""
        if not hasattr(self, 'ascan_curve'):
            return
        
        try:
            import numpy as np
            
            # 检查是否启用了抽样显示
            if self.sampling_checkbox.isChecked():
                # 获取抽样间隔
                sampling_interval = self.sampling_spinbox.value()
                # 执行抽样
                sampled_data = data[::sampling_interval]
                x = np.arange(0, len(data), sampling_interval)
            else:
                # 不抽样，显示所有数据
                sampled_data = data
                x = np.arange(len(data))
            
            # 更新曲线数据
            self.ascan_curve.setData(x, sampled_data)
            
            # 调整坐标轴范围
            if len(data) > 0:
                self.ascan_plot.setXRange(0, len(data))
                self.ascan_plot.setYRange(np.min(data) - 0.1, np.max(data) + 0.1)
                
        except Exception as e:
            self.log_message(f"更新A-Scan显示失败: {str(e)}")

    def update_system_time(self):
        """更新系统时间"""
        if not self.rtk_enabled:
            # 如果RTK未启用，则更新系统时间
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            # 更新RTK状态栏的时间显示
            if self.rtk_status_bar:
                self.rtk_status_bar.update_display({'time': current_time})

    def start_system_timer(self):
        """启动系统时间定时器"""
        if self.system_timer and not self.system_timer.isActive():
            self.system_timer.start(1000)

    def on_mode_changed(self, index=None):
        """当采集模式改变时调用"""
        # 获取当前选中的模式索引
        if index is None:
            index = self.mode_combo.currentIndex()
        
        # 更新当前模式
        mode_list = ['point', 'fixed', 'continuous']
        self.current_mode = mode_list[index]
        
        # 切换到对应的模式页面
        self.mode_stacked_widget.setCurrentIndex(index)
        
        # 重置点测计数器
        self.reset_point_counter_on_mode_change()
        
        self.log_message(f"采集模式已切换到: {self.mode_combo.currentText()}")

    def reset_point_counter_on_mode_change(self):
        """模式切换时重置点测计数器"""
        self.point_sample_counter = 0
        self.point_group_counter = 0

    def refresh_devices(self):
        """刷新可用设备列表"""
        self.log_message("刷新设备列表")
        try:
            # 创建临时VNA控制器实例来获取设备列表
            temp_vna = VNAController()
            devices = temp_vna.list_devices()
            
            # 清空并添加设备列表
            self.device_combo.clear()
            if devices:
                self.device_combo.addItems(devices)
                self.device_combo.setCurrentIndex(0)
                self.log_message(f"发现 {len(devices)} 个设备")
            else:
                # 如果没有发现设备，添加一个默认设备
                self.device_combo.addItems(['TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR'])
                self.device_combo.setCurrentIndex(0)
                self.log_message("未发现设备，使用默认设备")
        except Exception as e:
            self.log_message(f"刷新设备列表失败: {str(e)}")
            # 出错时使用模拟数据
            self.device_combo.clear()
            self.device_combo.addItems(['TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR'])
            self.device_combo.setCurrentIndex(0)

    def connect_device(self):
        """连接到VNA设备"""
        # 获取设备地址
        device_address = self.device_combo.currentText()
        self.log_message(f"正在连接到设备: {device_address}")
        
        # 禁用连接按钮防止重复操作
        self.connect_button.setEnabled(False)
        
        # 使用QThread在后台线程中连接设备，避免阻塞主线程
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class DeviceConnectThread(QThread):
            """在后台线程中连接设备的线程类"""
            
            # 定义信号
            success = pyqtSignal(str)  # 成功信号，传递设备地址
            failure = pyqtSignal(str, str)  # 失败信号，传递设备地址和错误信息
            
            def __init__(self, parent, device_address):
                super().__init__(parent)
                self.device_address = device_address
                self.parent = parent
            
            def run(self):
                """线程运行函数"""
                try:
                    # 创建VNA控制器实例
                    vna_controller = VNAController()
                    
                    # 使用open_device方法连接设备
                    if vna_controller.open_device(self.device_address):
                        # 保存VNA控制器实例到父对象
                        self.parent.vna_controller = vna_controller
                        self.success.emit(self.device_address)
                    else:
                        self.failure.emit(self.device_address, "连接设备失败")
                except Exception as e:
                    self.failure.emit(self.device_address, f"连接设备时发生错误: {str(e)}")
        
        # 创建并启动线程
        self.connect_thread = DeviceConnectThread(self, device_address)
        self.connect_thread.success.connect(self.on_device_connect_success)
        self.connect_thread.failure.connect(self.on_device_connect_failure)
        self.connect_thread.finished.connect(lambda: self.connect_button.setEnabled(True))
        self.connect_thread.start()
    
    def on_device_connect_success(self, device_address):
        """设备连接成功后的处理"""
        self.device_connected = True
        self.update_device_status()
        self.log_message(f"成功连接到设备: {device_address}")
        InfoBar.success(
            title='设备连接',
            content=f'成功连接到设备: {device_address}',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def on_device_connect_failure(self, device_address, error_msg):
        """设备连接失败后的处理"""
        self.log_message(f"{error_msg}: {device_address}")
        InfoBar.error(
            title='设备连接',
            content=f'{error_msg}: {device_address}',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def disconnect_device(self):
        """断开与VNA设备的连接"""
        try:
            if self.vna_controller:
                self.vna_controller.close_device()
                self.device_connected = False
                self.update_device_status()
                self.log_message("设备已断开连接")
                InfoBar.info(
                    title='设备断开',
                    content='设备已断开连接',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            self.log_message(f"断开设备连接时发生错误: {str(e)}")

    def get_device_id(self):
        """获取设备ID"""
        try:
            if self.vna_controller:
                # 使用query方法发送*IDN?命令获取设备ID
                device_id = self.vna_controller.query("*IDN?")
                if device_id:
                    self.log_message(f"设备ID: {device_id.strip()}")
                    InfoBar.success(
                        title='设备ID',
                        content=f'设备ID: {device_id.strip()}',
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
        except Exception as e:
            self.log_message(f"获取设备ID时发生错误: {str(e)}")

    def get_catalog(self):
        """获取设备目录"""
        try:
            if self.vna_controller:
                current_path = self.path_line_edit.text()
                catalog = self.vna_controller.catalog(current_path)
                self.log_message(f"设备目录: {catalog}")
        except Exception as e:
            self.log_message(f"获取设备目录时发生错误: {str(e)}")

    def browse_directory(self):
        """浏览目录"""
        # 打开文件对话框，让用户选择目录
        directory = QFileDialog.getExistingDirectory(self, "选择目录", self.path_line_edit.text())
        if directory:
            self.path_line_edit.setText(directory)

    def change_directory(self):
        """切换目录"""
        try:
            if self.vna_controller:
                new_path = self.path_line_edit.text()
                if self.vna_controller.cdir(new_path):
                    self.log_message(f"目录已切换到: {new_path}")
                    InfoBar.success(
                        title='目录切换',
                        content=f'目录已切换到: {new_path}',
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
        except Exception as e:
            self.log_message(f"切换目录时发生错误: {str(e)}")

    def update_device_status(self):
        """更新设备状态"""
        if self.device_connected:
            # 设备已连接，启用相关按钮
            self.disconnect_button.setEnabled(True)
            self.get_id_button.setEnabled(True)
            self.catalog_button.setEnabled(True)
            self.browse_dir_button.setEnabled(True)
            self.change_dir_button.setEnabled(True)
            self.point_acquire_button.setEnabled(True)
            self.point_start_button.setEnabled(True)
            self.fixed_start_button.setEnabled(True)
            self.continuous_start_button.setEnabled(True)
        else:
            # 设备未连接，禁用相关按钮
            self.disconnect_button.setEnabled(False)
            self.get_id_button.setEnabled(False)
            self.catalog_button.setEnabled(False)
            self.browse_dir_button.setEnabled(False)
            self.change_dir_button.setEnabled(False)
            self.point_acquire_button.setEnabled(False)
            self.point_start_button.setEnabled(False)
            self.fixed_start_button.setEnabled(False)
            self.continuous_start_button.setEnabled(False)

    def point_acquire(self):
        """执行单次点测采集"""
        # 这里应该添加单次点测采集的逻辑
        self.log_message("执行单次点测采集")
        # 模拟点测采集
        self.point_sample_counter += 1
        self.point_group_counter += 1
        self.log_message(f"点测采集完成，样本数: {self.point_sample_counter}, 组数: {self.point_group_counter}")

    def start_point_measurement(self):
        """开始连续点测测量"""
        # 这里应该添加开始连续点测测量的逻辑
        self.log_message("开始连续点测测量")
        self.is_point_running = True
        self.point_start_button.setEnabled(False)
        self.point_stop_button.setEnabled(True)

    def stop_point_measurement(self):
        """停止连续点测测量"""
        # 这里应该添加停止连续点测测量的逻辑
        self.log_message("停止连续点测测量")
        self.is_point_running = False
        self.point_start_button.setEnabled(True)
        self.point_stop_button.setEnabled(False)

    def start_fixed_acquire(self):
        """开始定次采集"""
        # 这里应该添加开始定次采集的逻辑
        self.log_message("开始定次采集")
        self.fixed_start_button.setEnabled(False)
        # 模拟定次采集
        count = self.fixed_count_spin.value()
        self.log_message(f"定次采集开始，共采集 {count} 次")

    def start_continuous_acquire(self):
        """开始连续采集"""
        # 这里应该添加开始连续采集的逻辑
        self.log_message("开始连续采集")
        self.is_continuous_running = True
        self.continuous_start_button.setEnabled(False)
        self.continuous_stop_button.setEnabled(True)

    def stop_continuous_acquire(self):
        """停止连续采集"""
        self.log_message("停止连续采集")
        if self.continuous_worker and self.continuous_worker.isRunning():
            self.continuous_worker.stop()
            self.continuous_worker.wait()
            self.continuous_worker = None
        self.is_continuous_running = False
        self.continuous_start_button.setEnabled(True)
        self.continuous_stop_button.setEnabled(False)
    
    def on_worker_progress(self, current, total=None):
        """处理工作线程进度更新"""
        if total:
            self.progress_bar.setValue(int((current / total) * 100))
        else:
            # 连续模式，只显示当前计数
            self.log_message(f"连续采集已完成 {current} 次")
    
    def on_worker_finished(self, success, message):
        """处理工作线程完成信号"""
        if success:
            self.log_message(f"采集成功: {message}")
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
            self.log_message(f"采集失败: {message}")
            InfoBar.error(
                title='采集失败',
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        
        # 恢复按钮状态
        self.fixed_start_button.setEnabled(True)
        self.continuous_start_button.setEnabled(True)
        self.point_start_button.setEnabled(True)
        self.point_acquire_button.setEnabled(True)
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
    
    def start_fixed_acquire(self):
        """开始定次采集"""
        self.log_message("开始定次采集")
        self.fixed_start_button.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 获取采集参数
        count = self.fixed_count_spin.value()
        file_prefix = self.file_prefix_line_edit.text()
        path = self.path_line_edit.text()
        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        data_acquisition_mode = self.data_acquisition_combo.currentText()
        
        # 创建并启动工作线程
        self.fixed_worker = DataDumpWorker(
            self.vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval, data_acquisition_mode
        )
        # 绑定信号
        self.fixed_worker.progress_updated.connect(self.on_worker_progress)
        self.fixed_worker.finished_signal.connect(self.on_worker_finished)
        self.fixed_worker.ascan_data_available.connect(self.update_ascan_display)
        # 启动线程
        self.fixed_worker.start()
        
        self.log_message(f"定次采集开始，共采集 {count} 次")
    
    def start_continuous_acquire(self):
        """开始连续采集"""
        self.log_message("开始连续采集")
        self.is_continuous_running = True
        self.continuous_start_button.setEnabled(False)
        self.continuous_stop_button.setEnabled(True)
        
        # 获取采集参数
        file_prefix = self.file_prefix_line_edit.text()
        path = self.path_line_edit.text()
        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        data_acquisition_mode = self.data_acquisition_combo.currentText()
        
        # 创建并启动工作线程
        self.continuous_worker = ContinuousDumpWorker(
            self.vna_controller, file_prefix, path, data_type, scope, data_format, selector, interval, data_acquisition_mode
        )
        # 绑定信号
        self.continuous_worker.progress_updated.connect(self.on_worker_progress)
        self.continuous_worker.finished_signal.connect(self.on_worker_finished)
        self.continuous_worker.ascan_data_available.connect(self.update_ascan_display)
        # 启动线程
        self.continuous_worker.start()
    
    def point_acquire(self):
        """执行单次点测采集"""
        self.log_message("执行单次点测采集")
        self.point_acquire_button.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 获取采集参数
        count = self.point_count_spin.value()
        file_prefix = self.file_prefix_line_edit.text()
        path = self.path_line_edit.text()
        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        data_acquisition_mode = self.data_acquisition_combo.currentText()
        
        # 计算起始索引
        start_index = self.point_sample_counter * count
        
        # 创建并启动工作线程
        self.point_worker = SinglePointDumpWorker(
            self.vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval, start_index, data_acquisition_mode
        )
        # 绑定信号
        self.point_worker.progress_updated.connect(self.on_worker_progress)
        self.point_worker.finished_signal.connect(self.on_worker_finished)
        self.point_worker.ascan_data_available.connect(self.update_ascan_display)
        # 启动线程
        self.point_worker.start()
        
        # 更新计数器
        self.point_sample_counter += 1
    
    def start_point_measurement(self):
        """开始连续点测测量"""
        self.log_message("开始连续点测测量")
        self.is_point_running = True
        self.point_start_button.setEnabled(False)
        self.point_stop_button.setEnabled(True)
        
        # 获取采集参数
        count = self.point_count_spin.value()
        file_prefix = self.file_prefix_line_edit.text()
        path = self.path_line_edit.text()
        data_type = self.data_type_combo.currentText()
        scope = self.scope_combo.currentText()
        data_format = self.format_combo.currentText()
        selector = self.selector_spin.value()
        interval = self.interval_spin.value()
        data_acquisition_mode = self.data_acquisition_combo.currentText()
        
        # 创建并启动工作线程
        self.point_worker = PointDumpWorker(
            self.vna_controller, count, file_prefix, path, data_type, scope, data_format, selector, interval, data_acquisition_mode
        )
        # 绑定信号
        self.point_worker.progress_updated.connect(self.on_worker_progress)
        self.point_worker.finished_signal.connect(self.on_worker_finished)
        self.point_worker.ascan_data_available.connect(self.update_ascan_display)
        # 启动线程
        self.point_worker.start()
    
    def stop_point_measurement(self):
        """停止连续点测测量"""
        self.log_message("停止连续点测测量")
        if self.point_worker and self.point_worker.isRunning():
            self.point_worker.stop()
            self.point_worker.wait()
            self.point_worker = None
        self.is_point_running = False
        self.point_start_button.setEnabled(True)
        self.point_stop_button.setEnabled(False)
