# USB-VNA 项目开发维护说明文档

## 1. 项目概述

本项目是一个基于 Python 的 Keysight USB 矢量网络分析仪（VNA）控制程序，主要用于探地雷达（GPR）数据采集。项目使用 PyVISA 库与设备通信，通过 PyQt6 和 PyQt6-Fluent-Widgets 构建现代图形用户界面。

### 1.1 核心组件

- **[vna_controller.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py)** - 设备控制核心模块，封装所有与 VNA 通信的 SCPI 命令
- **[fluent_window.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py)** - GUI 界面实现模块，包含所有界面元素和用户交互逻辑
- **[logger_config.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/logger_config.py)** - 日志配置模块，提供统一的日志记录功能
- **[rtk_module.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/rtk_module.py)** - RTK定位模块，处理GPS/RTK数据的接收、解析和存储
- **[main_gui.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/main_gui.py)** - GUI 程序入口点
- **[main_nogui.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/main_nogui.py)** - 命令行程序入口点

### 1.2 项目特点

- 支持三种数据采集模式：点测模式、定次采集模式、连续采集模式
- 集成RTK高精度定位系统，实时显示GPS位置信息
- 提供友好的图形用户界面，便于操作和监控
- 支持多种数据格式（CSV、SDP、SNP）和数据范围（Trace、Displayed、Channel、Auto）
- 具备完善的日志记录系统，便于调试和故障排查

## 2. 项目结构

```
src/
├── lib/                        # VNA 控制模块
│   ├── __init__.py
│   ├── logger_config.py        # 日志配置模块
│   ├── vna_controller.py       # VNA 控制器类
│   ├── fluent_window.py        # GUI 实现
│   ├── rtk_module.py           # RTK 定位模块
│   └── rtk_module_bak.py       # RTK 定位模块备份
├── config/                     # 配置文件
│   └── config.json             # 配置文件
├── main_gui.py                 # GUI 主入口
├── main_nogui.py               # CLI 主入口
├── HWT905_ttl.py              # HWT905 陀螺仪接口（TTL通信）
├── 参考_rtk.py                # RTK 模块参考代码
├── GPR_Processsing_Script/     # GPR 数据处理脚本
│   ├── b_scan_visualization.py # B扫描可视化脚本
│   └── [DEPRECATED]...         # 已废弃的脚本
└── logs/                       # 日志文件目录
```

## 3. 快速上手指南

### 3.1 环境搭建

1. **安装Python环境**：
   - 推荐使用Python 3.10
   - 使用Conda环境管理依赖包

2. **安装必要依赖**：
   ```bash
   pip install pyvisa
   pip install pyqt6
   pip install pyqt6-fluent-widgets
   pip install keysight-ktna  # Keysight官方驱动
   pip install pyserial       # 用于RTK串口通信
   ```

3. **硬件连接**：
   - 将USB-VNA设备通过USB线连接到计算机
   - 确保VNA前面板已开启HiSLIP和Drive Access功能
   - 如需RTK定位，将RTK模块通过串口连接

### 3.2 代码结构理解

1. **核心控制器** ([vna_controller.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py))：
   - 使用PyVISA库与设备通信
   - 封装SCPI命令，提供高级接口
   - 包含设备连接、数据采集、目录操作等功能

2. **GUI界面** ([fluent_window.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py))：
   - 使用PyQt6-Fluent-Widgets构建现代化界面
   - 包含设备控制、数据配置、采集模式、状态显示等功能区
   - 实现多线程数据采集，避免界面卡顿

3. **RTK定位** ([rtk_module.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/rtk_module.py))：
   - 通过串口与RTK模块通信
   - 解析NMEA协议数据（GGA、RMC、GSA等）
   - 实时显示GPS位置、卫星数、定位类型等信息

## 4. 界面开发指南

### 4.1 界面结构

GUI 界面主要分为以下几个功能区域：

1. **设备连接区域** - 包含设备列表、连接/断开按钮等
2. **RTK定位模块区域** - 包含RTK串口选择、波特率设置、启用开关等
3. **数据配置区域** - 包含数据类型、范围、格式等配置选项
4. **采集模式区域** - 包含点测、定次采集、连续采集三种模式
5. **状态信息区域** - 显示运行状态和RTK定位信息

### 4.2 添加界面内容

#### 4.2.1 添加新的配置选项

在 [create_config_section()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L395-L565) 方法中添加新的配置控件。

示例：
```python
def create_config_section(self):
    # ... 现有代码 ...
    
    # 添加新配置项示例
    new_config_layout = QHBoxLayout()
    new_label = QLabel('新配置项:')
    self.new_config_edit = LineEdit()
    new_config_layout.addWidget(new_label)
    new_config_layout.addWidget(self.new_config_edit)
    config_group_layout.addLayout(new_config_layout)
    
    # ... 现有代码 ...
```

#### 4.2.2 添加新的采集模式

1. 在 [create_acquisition_mode_section()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L567-L648) 方法中添加新的模式页面
2. 在 [on_mode_changed()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L771-L782) 方法中添加新模式的处理逻辑
3. 添加相应的信号连接到 [setup_connections()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L647-L693) 方法中

示例：
```python
def create_acquisition_mode_section(self):
    # ... 现有代码 ...
    
    # 添加新模式页面
    self.new_mode_page = QGroupBox("新模式参数")
    new_layout = QHBoxLayout(self.new_mode_page)
    new_layout.setSpacing(15)  # 设置控件间距
    new_layout.setContentsMargins(15, 15, 15, 15)  # 设置边距
    
    self.new_mode_button = PrimaryPushButton('新模式按钮')
    self.new_mode_button.setEnabled(False)
    new_layout.addWidget(self.new_mode_button)
    new_layout.addStretch()  # 添加弹性空间
    
    # 添加到堆叠部件
    self.mode_stacked_widget.addWidget(self.new_mode_page)
    
    # ... 现有代码 ...

def on_mode_changed(self):
    # ... 现有代码 ...
    elif self.mode_config.Mode.value == "new_mode":
        self.mode_stacked_widget.setCurrentIndex(3)  # 根据实际索引调整
```

#### 4.2.3 添加新的状态显示控件

在 [create_status_section()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L695-L720) 方法中添加新的状态显示控件。

### 4.3 界面布局规范

为保持界面一致性，请遵循以下布局规范：

1. 使用 GroupBox 容器组织功能区域，提高界面可读性
2. 设置统一的控件间距：`setSpacing(15)`
3. 设置统一的边距：`setContentsMargins(15, 15, 15, 15)`
4. 为按钮添加明确的标签，提高操作可识别性
5. 在布局末尾添加弹性空间（`addStretch()`），实现控件对齐
6. 保持一致的视觉风格，增强界面层次感

## 5. 功能开发和绑定

### 5.1 核心控制功能

核心控制功能位于 [vna_controller.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py) 文件中，该文件实现了 [VNAController](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py#L19-L313) 类，封装了与 VNA 设备通信的所有方法。

### 5.2 添加新的控制命令

在 [vna_controller.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py) 文件中添加新的方法：

```python
def new_command(self, parameter):
    """
    新命令的描述
    
    Args:
        parameter (str): 命令参数
        
    Returns:
        str: 设备返回的响应
    """
    command = f":NEW:COMMAND {parameter}"
    return self.query(command)
```

### 5.3 在界面中使用新功能

在 [fluent_window.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py) 中通过 [self.vna_controller](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L326-L326) 对象调用新添加的方法：

```python
# 在按钮点击事件处理方法中
def on_new_button_clicked(self):
    if self.vna_controller:
        try:
            result = self.vna_controller.new_command("parameter")
            self.log_message(f"新命令执行结果: {result}")
        except Exception as e:
            self.log_message(f"执行新命令时出错: {str(e)}")
```

### 5.4 功能绑定

在 [setup_connections()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L647-L693) 方法中将界面控件与功能方法进行绑定：

```python
def setup_connections(self):
    # ... 现有代码 ...
    self.new_button.clicked.connect(self.on_new_button_clicked)
```

## 6. 工作线程开发

对于耗时操作，需要使用工作线程避免阻塞 GUI。项目中已经实现了几种工作线程：

- [DataDumpWorker](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L54-L85) - 定次采集工作线程
- [ContinuousDumpWorker](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L88-L129) - 连续采集工作线程
- [PointDumpWorker](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L132-L193) - 点测采集工作线程
- [SinglePointDumpWorker](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L196-L249) - 单次点测工作线程

### 6.1 添加新的工作线程

创建新的工作线程类继承自 [QThread](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L33-L33)：

```python
class NewWorker(QThread):
    # 定义信号
    progress_updated = pyqtSignal(int)  # 进度信号
    finished_signal = pyqtSignal(bool, str)  # 完成信号
    
    def __init__(self, vna_controller, parameters):
        super().__init__()
        self.vna_controller = vna_controller
        # 初始化其他参数
        
    def run(self):
        # 实现具体的工作逻辑
        try:
            # 执行操作
            self.finished_signal.emit(True, "操作成功完成")
        except Exception as e:
            self.finished_signal.emit(False, f"操作失败: {str(e)}")
```

## 7. RTK模块集成

项目集成了RTK高精度定位模块，支持实时GPS位置显示和数据记录：

### 7.1 RTK模块功能

- 实时显示GPS时间、卫星数、定位类型、经纬度和海拔
- 支持多种定位模式（单点定位、RTK固定解、RTK浮点解等）
- 可配置数据存储频率（1Hz-20Hz）
- 支持数据导出为CSV格式

### 7.2 RTK模块开发

如需扩展RTK功能，在 [rtk_module.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/rtk_module.py) 中添加新功能：

```python
def new_rtk_feature(self):
    """
    添加新的RTK功能
    """
    # 实现新的RTK功能
    pass
```

### 7.3 RTK状态显示

RTK状态显示在 [RTKStatusBar](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L252-L375) 类中实现，该类继承自 [HeaderCardWidget](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/fluent_window.py#L252-L252)，提供实时的GPS信息展示。

## 8. 日志系统

项目使用统一的日志系统，各模块都有自己的日志记录器：

- GUI 模块: [vna_window.log](file:///C:/Users/unive/Desktop/usbvna_v202511/src/logs/vna_window.log)
- 控制器模块: [vna_controller.log](file:///C:/Users/unive/Desktop/usbvna_v202511/src/logs/vna_controller.log)
- 主程序模块: `vna_main.log`
- GUI 入口: [vna_gui.log](file:///C:/Users/unive/Desktop/usbvna_v202511/src/logs/vna_gui.log)

在代码中使用日志记录：

```python
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## 9. 开发注意事项

### 9.1 界面开发注意事项

1. 遵循现有的界面布局规范，使用 GroupBox 容器组织功能区域
2. 保持统一的控件间距（15px）和边距（15px）
3. 为新添加的按钮和控件添加明确的标签
4. 在布局末尾添加弹性空间（addStretch()）实现控件对齐
5. 在GUI主线程中更新界面元素，避免在工作线程中直接修改UI

### 9.2 功能开发注意事项

1. 所有与设备的交互都应通过 [VNAController](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py#L19-L313) 类进行
2. 耗时操作必须使用工作线程，避免阻塞 GUI
3. 添加适当的异常处理和错误提示
4. 为新功能添加日志记录
5. 确保设备资源的正确释放（在适当时候调用 [close_device()](file:///C:/Users/unive/Desktop/usbvna_v202511/src/lib/vna_controller.py#L162-L186)）

### 9.3 代码规范

1. 遵循 Python 标准编码规范
2. 为类和方法添加详细的文档字符串
3. 使用有意义的变量和方法命名
4. 保持代码的一致性和可读性
5. 注释关键代码段，特别是复杂的SCPI命令或算法

## 10. 测试和调试

### 10.1 日志调试

通过查看各模块的日志文件进行问题排查：

- [logs/vna_gui.log](file:///C:/Users/unive/Desktop/usbvna_v202511/logs/vna_gui.log) - GUI 主程序日志
- [logs/vna_window.log](file:///C:/Users/unive/Desktop/usbvna_v202511/logs/vna_window.log) - 窗口模块日志
- [logs/vna_controller.log](file:///C:/Users/unive/Desktop/usbvna_v202511/logs/vna_controller.log) - 控制器模块日志

### 10.2 功能测试

1. 在 [main_nogui.py](file:///C:/Users/unive/Desktop/usbvna_v202511/src/main_nogui.py) 中测试新的控制命令
2. 在 GUI 中测试完整的用户交互流程
3. 验证异常处理和错误恢复能力
4. 测试RTK模块的连接和数据接收

## 11. 部署和打包

项目可以使用 PyInstaller 进行打包，生成可执行文件。

### 11.1 打包配置规范

1. 使用 `.ico` 格式图标文件
2. 在 EXE 配置中通过 `icon` 参数指定图标路径
3. 减少包含的资源，只包含必要的数据和模块
4. 可使用 UPX 压缩减小文件大小

### 11.2 环境部署

1. 确保目标系统安装了Python 3.10环境
2. 安装必要的依赖包（PyVISA、PyQt6等）
3. 安装Keysight VNA驱动程序
4. 配置串口权限（Linux系统）

通过遵循以上开发维护说明，您可以有效地在项目中添加新的界面元素、功能和改进现有代码。如有任何疑问，请参考现有代码实现或联系项目负责人。