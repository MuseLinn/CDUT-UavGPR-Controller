# VNA实时数据流传输与处理系统测试

本目录包含VNA实时数据流传输与处理系统的测试实现，包括服务器端、地面端功能和性能评估模块。

## 目录结构

```
vna_streaming_test/
├── test_server.py        # 服务器端测试实现
├── test_ground.py        # 地面端测试实现
├── test_performance.py   # 性能评估测试实现
└── README.md             # 本说明文件
```

## 功能说明

### 1. 服务器端测试 (`test_server.py`)

- **功能**：实现VNA设备的实时数据流读取、缓存、CSV写入和远程传输
- **核心组件**：
  - `SimpleVNAController`：与VNA设备通信，读取A-Scan时域数据
  - `DataCache`：实现数据缓存机制，确保数据可靠性
  - `DataWriter`：将实时数据流以CSV格式持续写入文件
  - `DataTransmitter`：实现数据远程传输功能，确保数据同步传输至地面端
  - `VNAServer`：整合上述组件，实现完整的服务器端功能

### 2. 地面端测试 (`test_ground.py`)

- **功能**：接收服务器端传输的实时数据流、存储和可视化
- **核心组件**：
  - `DataReceiver`：接收服务器端传输的实时数据流，处理分片数据重组
  - `DataStorage`：将接收到的数据以与服务器端相同的CSV格式持续写入文件
  - `BScanPlotter`：实现B-Scan实时绘制功能，确保数据接收后能立即可视化展示
  - `VNAGroundStation`：整合上述组件，实现完整的地面端功能

### 3. 性能评估测试 (`test_performance.py`)

- **功能**：评估系统的性能表现，包括带宽需求、传输延迟、丢包率和实时处理性能
- **核心组件**：
  - `PerformanceAnalyzer`：性能分析器，用于分析系统的性能表现
  - `EnhancedDataTransmitter`：增强版数据传输类，带性能分析功能
  - `EnhancedDataReceiver`：增强版数据接收类，带性能分析功能
  - `PerformanceTest`：性能测试类，用于测试系统性能

## 使用方法

### 1. 服务器端测试

1. **配置参数**：在 `test_server.py` 文件中修改以下参数：
   - `DEVICE_NAME`：VNA设备名称
   - `SERVER_IP`：服务器IP地址
   - `SERVER_PORT`：服务器端口
   - `ACQUISITION_PERIOD_MS`：采集周期（毫秒）

2. **运行服务器端**：
   ```bash
   python test_server.py
   ```

### 2. 地面端测试

1. **配置参数**：在 `test_ground.py` 文件中修改以下参数：
   - `LOCAL_IP`：本地IP地址
   - `LOCAL_PORT`：本地端口
   - `NUM_TRACES`：绘制的道数

2. **运行地面端**：
   ```bash
   python test_ground.py
   ```

### 3. 性能评估测试

1. **配置参数**：在 `test_performance.py` 文件中修改以下参数：
   - `SERVER_IP`：服务器IP地址
   - `SERVER_PORT`：服务器端口
   - `LOCAL_IP`：本地IP地址
   - `LOCAL_PORT`：本地端口

2. **运行性能测试**：
   ```bash
   python test_performance.py
   ```

## 性能评估

性能评估测试会生成详细的性能报告，包括：

1. **带宽需求分析**：量化评估在不同A-Scan采样间隔条件下系统对网络带宽的需求
2. **传输延迟分析**：分析数据传输延迟等关键性能指标
3. **丢包率分析**：记录和分析数据传输的丢包率
4. **处理性能分析**：评估实时数据处理与可视化的性能表现
5. **性能报告**：生成详细的性能评估报告，保存为JSON文件

## 注意事项

1. **网络配置**：确保服务器端和地面端之间的网络连接正常，特别是使用内网穿透时，需要正确配置frp客户端和服务器。
2. **VNA设备**：确保VNA设备已正确连接并配置，服务器端测试需要访问真实的VNA设备。
3. **参数调整**：根据实际网络环境和VNA设备性能，调整采集周期、数据包大小等参数，以获得最佳性能。
4. **权限问题**：确保测试脚本有足够的权限读写文件和使用网络端口。

## 依赖项

- **Python 3.7+**
- **pyvisa**：用于与VNA设备通信
- **numpy**：用于数据处理
- **pyqtgraph**：用于B-Scan实时绘制
- **PyQt5**：pyqtgraph的依赖项
- **frp**：用于内网穿透（可选，根据网络环境而定）

## 安装依赖

```bash
pip install pyvisa numpy pyqtgraph PyQt5
```

## 总结

本测试实现提供了一套完整的VNA实时数据流传输与处理系统，包括服务器端、地面端功能和性能评估模块。通过这些测试，可以验证系统的功能正确性和性能表现，为后续无网通信采用的数据链路模块选型提供参考。
