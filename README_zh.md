# USB-VNA (P9731B) 控制程序

## 项目简介

本项目是用于控制 Keysight USB 矢量网络分析仪(VNA)的 Python 脚本，通过 PyVISA 库实现对设备的连接、控制和数据采集功能。适用于 P973X 系列 USB-VNA 设备，主要用于探地雷达(GPR)数据采集。

References: 

- [KeySight Controlling the VNA Using Python](https://helpfiles.keysight.com/csg/pxivna/Programming/GPIB_Example_Programs/Controlling_the_VNA_Using_Python.htm)
- [PyVISA](https://pyvisa.readthedocs.io/en/latest/introduction/getting.html)

## 作者信息

贡献者：Linn  
邮箱：[universe_yuan@icloud.com](https://pyvisa.readthedocs.io/en/latest/introduction/getting.html)  
版权所有 (c) 2025 by Linn, All Rights Reserved.

## 环境配置要求

### 系统要求
- 操作系统：Windows 7 或更高版本（推荐 Windows 10/11）、Linux 或 macOS
- Python 版本：Python 3.10（项目使用工程目录下的 Conda 环境）
- USB-VNA 设备：Keysight P973X 系列
- 设备驱动：Keysight Network Analyzers Python Instrument Drivers (版本 V2.0.2)

### 软件依赖
项目使用工程目录下的 Conda 环境，其中已包含运行所需的所有依赖包：
- Python 3.10
- PyVISA
- PyQt6
- PyQt6-Fluent-Widgets
- Keysight Network Analyzers Python Instrument Drivers (V2.0.2)

驱动程序已包含在项目中的压缩包 [keysight_ktna_V2.0.2_python3.10_64-bit_binary_package.zip](keysight_ktna_V2.0.2_python3.10_64-bit_binary_package.zip) 内，并已在 Conda 环境中安装完毕。

### 可选依赖（用于数据可视化等）
```bash
pip install numpy
pip install matplotlib
pip install scipy
```

## 项目结构

```
src/
├── vna_package/                # VNA控制模块
│   ├── __init__.py
│   ├── logger_config.py        # 日志配置模块
│   ├── vna_controller.py       # VNA控制器类
│   └── fluent_window.py        # GUI界面实现
├── main_gui.py                 # GUI主程序入口
├── main_nogui.py               # 命令行主程序入口
└── logs/                       # 日志文件目录
```

## 使用说明

### 基本使用方法
在项目 Conda 环境中运行GUI主程序：
```bash
python src/main_gui.py
```

或者运行命令行版本：
```bash
python src/main_nogui.py
```

### GUI界面功能说明

GUI界面基于PyQt6-Fluent-Widgets开发，提供直观易用的操作界面，主要功能包括：

1. **设备连接管理**
   - 设备自动发现与手动输入
   - 设备连接与断开
   - 获取设备ID信息
   - 查看和切换设备目录

2. **数据采集配置**
   - 数据类型选择（CSV、SDP、SNP）
   - 数据范围设置（Trace、Displayed、Channel、Auto）
   - 数据格式选择（Displayed、RI、MA、DB）
   - 测量编号设置（-1到100）
   - 文件前缀设置
   - 采集间隔设置（0.01s-10s）

3. **三种采集模式**

   **点测模式**
   - 单次采集：每次点击采集指定数量的数据，每点击一次为一组
   - 连续点测：持续采集点测数据直到手动停止
   - 适用于需要按需采集的场景

   **定次采集模式**
   - 采集指定次数的数据文件
   - 适用于需要固定数量数据的实验

   **连续采集模式**
   - 持续采集数据直到手动停止
   - 实时显示采集进度
   - 适用于长时间连续监测场景

### VNAController 类说明
该类提供了控制 USB VNA 设备的基本方法：

1. `__init__()` - 初始化 VISA 资源管理器
2. `list_devices()` - 列出所有连接的 VISA 设备
3. `open_device(resource_name)` - 打开指定的 VISA 设备
4. `close_device()` - 关闭当前打开的设备
5. `query(command)` - 向设备发送查询命令并返回响应
6. `write(command)` - 向设备发送命令（无返回值）
7. `read()` - 从设备读取响应
8. `check_instrument_info()` - 检查仪器信息（*IDN?）
9. `catalog(path)` - 获取指定路径的目录内容
10. `cdir(path)` - 切换到指定目录
11. `data_dump(filename, data_type, scope, data_format, selector)` - 数据转储到文件

### 日志记录
程序使用 logging 模块记录操作日志，日志文件保存在 `src/logs/` 目录下：
- vna_controller.log - VNA 控制器模块日志
- vna_gui.log - GUI界面日志
- vna_main.log - 命令行主程序日志

日志级别包括 DEBUG、INFO、WARNING、ERROR 和 CRITICAL。

## 注意事项

1. 确保 USB VNA 设备已正确连接并安装了驱动程序
2. 运行程序前检查设备是否被其他程序占用
3. 根据实际设备修改设备资源名称
4. 如果遇到连接问题，尝试使用 NI-MAX 或 Keysight Connection Expert 工具检测设备
5. 避免电磁干扰，保持设备温度稳定，确保设备散热良好
6. 定期校准设备以确保测量精度
7. 设备需要在VNA前面板开启HiSLIP以及Drive Access以连接访问，如下图所示：
![Remote_Interface.png](archive/Remote_Interface.png)
![Interface_solved.png](archive/Interface_solved.png)

## 故障排除

### 找不到设备
- 检查 USB 连接是否正常
- 确认设备驱动是否正确安装
- 使用 `list_devices()` 方法查看是否能检测到设备

### 通信超时
- 增加设备超时设置
- 检查设备是否处于忙碌状态
- 确认 SCPI 命令格式是否正确

### GUI界面问题
- 确保已安装 PyQt6 和 PyQt6-Fluent-Widgets
- 检查屏幕分辨率和缩放设置
- 如出现界面显示异常，尝试重置界面设置