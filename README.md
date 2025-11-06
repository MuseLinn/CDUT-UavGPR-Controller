# USB-VNA (P9731B) Control Program

## Project Overview

This project provides Python scripts for controlling Keysight USB Vector Network Analyzers (VNA), utilizing the PyVISA library for device connection, control, and data acquisition. It is compatible with the P973X series USB-VNA devices and supports essential measurement workflows.

References:

- [KeySight Controlling the VNA Using Python](https://helpfiles.keysight.com/csg/pxivna/Programming/GPIB_Example_Programs/Controlling_the_VNA_Using_Python.htm)
- [PyVISA](https://pyvisa.readthedocs.io/en/latest/introduction/getting.html)

## Author Information

Contributor: Linn  
Email: [universe_yuan@icloud.com](mailto:universe_yuan@icloud.com)  
Copyright (c) 2025 by Linn, All Rights Reserved.

## Environment Requirements

### System Requirements
- Operating System: Windows 7 or higher (Windows 10/11 recommended), Linux, or macOS
- Python Version: Python 3.10 (project uses a Conda environment in the project directory)
- USB-VNA Device: Keysight P973X Series
- Device Driver: Keysight Network Analyzers Python Instrument Drivers (Version V2.0.2)

### Software Dependencies
The project uses a Conda environment in the project directory, which includes all necessary dependencies:
- Python 3.10
- PyVISA
- PyQt6
- PyQt6-Fluent-Widgets
- Keysight Network Analyzers Python Instrument Drivers (V2.0.2)

The driver package is included in the archive [keysight_ktna_V2.0.2_python3.10_64-bit_binary_package.zip] and should be installed within the Conda environment.

### Optional Dependencies (for data visualization, etc.)
```bash
pip install numpy
pip install matplotlib
pip install scipy
```

## Project Structure

```
src/
├── lib/                        # VNA control module
│   ├── __init__.py
│   ├── logger_config.py        # Logging configuration module
│   ├── vna_controller.py       # VNA controller class
│   └── fluent_window.py        # GUI implementation
├── config/                     # Configuration files
│   └── config.json             # Configuration file
├── main_gui.py                 # GUI main entry point
├── main_nogui.py               # CLI main entry point
└── logs/                       # Log files directory
```

## Usage

### Basic Usage
Run the GUI main program in the Conda environment:
```bash
python src/main_gui.py
```

Or run the command-line version:
```bash
python src/main_nogui.py
```

### GUI Features

The GUI is built with PyQt6-Fluent-Widgets, providing an intuitive interface with the following main functionalities:

1. **Device Connection Management**
   - Device auto-discovery and manual input
   - Device connection and disconnection
   - Retrieve device ID information
   - View and switch device directories

2. **Data Acquisition Configuration**
   - Data type selection (CSV, SDP, SNP)
   - Data scope selection (Trace, Displayed, Channel, Auto)
   - Data format selection (Displayed, RI, MA, DB)
   - Measurement index setting (from -1 to 100)
   - File prefix setting
   - Acquisition interval setting (0.01s-10s)

3. **Three Acquisition Modes**

   **Point Measurement Mode**
   - Single acquisition: each click collects a specified amount of data, one set per click
   - Continuous point measurement: continuously collects point data until stopped manually
   - Suitable for on-demand data collection

   **Fixed Times Acquisition Mode**
   - Collects a specified number of data files
   - Useful for experiments requiring a fixed amount of data

   **Continuous Acquisition Mode**
   - Continuously collects data until stopped manually
   - Real-time display of acquisition progress
   - Suitable for long-term monitoring

### VNAController Class Overview

This class provides basic methods for controlling the USB VNA device:

1. `__init__()` - Initialize VISA resource manager
2. `list_devices()` - List all connected VISA devices
3. `open_device(resource_name)` - Open the specified VISA device
4. `close_device()` - Close the currently opened device
5. `query(command)` - Send a query command to the device and return the response
6. `write(command)` - Send a command to the device (no return value)
7. `read()` - Read response from the device
8. `check_instrument_info()` - Check instrument information (*IDN?)
9. `catalog(path)` - Get directory contents at the specified path
10. `cdir(path)` - Change to the specified directory
11. `data_dump(filename, data_type, scope, data_format, selector)` - Dump data to file

### Logging

The program uses the logging module to record operation logs, saved under `src/logs/`:
- vna_controller.log - VNA controller module logs
- vna_gui.log - GUI logs
- vna_main.log - CLI main program logs

Log levels include DEBUG, INFO, WARNING, ERROR, and CRITICAL.

## Notes

1. Ensure the USB VNA device is properly connected and the driver is installed.
2. Before running the program, check if the device is occupied by other programs.
3. Modify the device resource name as needed for your setup.
4. If connection issues occur, use NI-MAX or Keysight Connection Expert to detect the device.
5. Avoid electromagnetic interference, maintain stable device temperature, and ensure proper cooling.
6. Calibrate the device regularly for accurate measurements.
7. The VNA front panel should enable HiSLIP and Drive Access for remote connection, as shown below:
![Remote_Interface.png](archive/Remote_Interface.png)
![Interface_solved.png](archive/Interface_solved.png)

## Troubleshooting

### Device Not Found
- Check USB connection
- Confirm driver installation
- Use `list_devices()` to check for device detection

### Communication Timeout
- Increase device timeout setting
- Check if the device is busy
- Confirm correct SCPI command formatting

### GUI Issues
- Ensure PyQt6 and PyQt6-Fluent-Widgets are installed
- Check screen resolution and scaling settings
- If the interface appears abnormal, try resetting GUI settings

```
