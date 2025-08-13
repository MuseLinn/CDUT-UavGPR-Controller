# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2025-07-26 16:05:07
LastEditors  : Linn
LastEditTime : 2025-07-29 09:30:00
FilePath     : \\usbvna\\src\\vna_package\\vna_controller.py
Description  : VNA Controller class for KeySight USB VNA control via PyVISA

Copyright (c) 2025 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

import pyvisa as visa
from .logger_config import setup_logger

# 创建日志记录器
logger = setup_logger("vna_controller", "logs/vna_controller.log", level=10)  # 10对应DEBUG级别


class VNAController:
    """A class to control a KeySight USB VNA using PyVISA."""

    def __init__(self):
        """
        Initialize the VISA Resource Manager
        """
        self.rm = None
        self.P9371B_VISA = None
        try:
            self.rm = visa.ResourceManager()
            logger.debug("VISA Resource Manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize VISA Resource Manager: {e}")
            # 不抛出异常，允许对象创建成功但标记为未初始化状态
            self.rm = None

    def __del__(self):
        """
        Destructor to ensure proper cleanup
        """
        try:
            self.close_device()
            # 不要在这里关闭资源管理器，可能导致堆栈问题
        except Exception as e:
            logger.error(f"Error in destructor: {e}")

    def list_devices(self):
        """List all connected VISA devices."""
        if not self.rm:
            logger.error("Resource Manager not initialized")
            return []
        try:
            resources = self.rm.list_resources()
            logger.debug(f"Found resources: {resources}")
            return resources
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []

    def set_timeout(self, timeout_ms):
        """Set the device timeout in milliseconds."""
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return False
        try:
            self.P9371B_VISA.timeout = timeout_ms
            logger.debug(f"Device timeout set to {timeout_ms}ms")
            return True
        except Exception as e:
            logger.error(f"Error setting device timeout: {e}")
            return False

    def open_device(self, resource_name):
        """Open a VISA device."""
        if not self.rm:
            logger.error("Resource Manager not initialized")
            return None
        try:
            logger.debug(f"Opening device: {resource_name}")
            # 在打开新设备前确保之前的设备已关闭
            self.close_device()
            self.P9371B_VISA = self.rm.open_resource(resource_name)
            # 设置默认超时时间
            self.P9371B_VISA.timeout = 5000  # 5秒超时
            logger.debug(f"Device {self.P9371B_VISA} opened successfully")
            return self.P9371B_VISA
        except visa.VisaIOError as e:
            logger.error(f"Error opening device {resource_name}: {e}")
            return None
        except visa.VisaTypeError as e:
            logger.error(f"Type error opening device {resource_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error opening device {resource_name}: {e}")
            return None

    def close_device(self):
        """Close the opened VISA device."""
        if self.P9371B_VISA:
            try:
                logger.debug("Closing device")
                # 先清除设备状态
                try:
                    if hasattr(self.P9371B_VISA, 'clear'):
                        self.P9371B_VISA.clear()
                except Exception as e:
                    logger.warning(f"Could not clear device: {e}")
                
                self.P9371B_VISA.close()
                logger.debug("Device closed successfully")
            except visa.VisaIOError as e:
                logger.error(f"Error closing device: {e}")
            except Exception as e:
                logger.error(f"Unexpected error closing device: {e}")
            finally:
                self.P9371B_VISA = None
                logger.debug("Device reference cleared")

    def read(self):
        """Read a response from the device."""
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return None
            
        try:
            logger.debug("Reading response from device")
            # 检查是否有read方法
            if hasattr(self.P9371B_VISA, 'read'):
                response = self.P9371B_VISA.read()
                logger.debug(f"Response received: {response}")
                return response
            else:
                logger.error("Device does not support read method.")
                return None
        except visa.VisaIOError as e:
            logger.error(f"Error reading from device: {e}")
            return None
        except AttributeError as e:
            logger.error(f"Attribute error reading from device: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading from device: {e}")
            return None

    def query(self, command):
        """Send a command to the device and return the response."""
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return None
            
        try:
            logger.debug(f"Sending command: {command}")
            # 检查是否有query方法，如果有则直接使用（目前KeySight为此方法）
            if hasattr(self.P9371B_VISA, 'query'):
                response = self.P9371B_VISA.query(command)
                logger.debug(f"Response received: {response}")
                return response
            # 否则尝试使用write和read方法组合
            elif hasattr(self.P9371B_VISA, 'write') and hasattr(self.P9371B_VISA, 'read'):
                self.P9371B_VISA.write(command)
                response = self.P9371B_VISA.read()
                logger.debug(f"Response received: {response}")
                return response
            else:
                logger.error("Device does not support query, write, or read methods.")
                return None
        except visa.VisaIOError as e:
            logger.error(f"Error querying device: {e}")
            return None
        except AttributeError as e:
            logger.error(f"Attribute error querying device: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying device: {e}")
            return None

    def write(self, command):
        """Send a command to the device without expecting a response."""
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return False
            
        try:
            logger.debug(f"Sending command: {command}")
            # 检查是否有write方法
            if hasattr(self.P9371B_VISA, 'write'):
                self.P9371B_VISA.write(command)
                logger.debug("Command sent successfully")
                return True
            else:
                logger.error("Device does not support write method.")
                return False
        except visa.VisaIOError as e:
            logger.error(f"Error writing to device: {e}")
            return False
        except AttributeError as e:
            logger.error(f"Attribute error writing to device: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing to device: {e}")
            return False

    def check_instrument_info(self):
        """Check the instrument information."""
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return None
            
        try:
            logger.debug("Checking instrument information")
            # 检查设备是否支持query方法
            if hasattr(self.P9371B_VISA, 'query'):
                response = self.P9371B_VISA.query("*IDN?")
                logger.debug(f"Device ID: {response}")
                return response
            else:
                logger.error("Device does not support query method")
                # 尝试使用write和read方法组合
                if hasattr(self.P9371B_VISA, 'write') and hasattr(self.P9371B_VISA, 'read'):
                    self.P9371B_VISA.write("*IDN?")
                    response = self.P9371B_VISA.read()
                    logger.debug(f"Device ID: {response}")
                    return response
                else:
                    logger.error("Device does not support write and read methods")
                    return None
        except visa.VisaIOError as e:
            logger.error(f"Error checking instrument information: {e}")
            return None
        except AttributeError as e:
            logger.error(f"Attribute error checking instrument information: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error checking instrument information: {e}")
            return None

    def catalog(self, path):
        """Get the catalog of the remote directory."""
        # 检查设备是否支持query方法
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return None
            
        if not hasattr(self.P9371B_VISA, 'query'):
            logger.warning("Device does not support query method.")
            return None
            
        return self.query(f":MMEMory:CATalog:FILE? \"{path}\"")

    def cdir(self, path):
        """goto a directory from current work dir on the computer."""
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return None
            
        try:
            # FIXED
            # :MMEMory:CDIRectory is a read-write command, while using it without '?', it will set the dir and return nothing
            # folder = self.P9371B_VISA.query(':MMEMory:CDIRectory?')
            # WRONG: response = self.query(f":MMEMory:CDIRectory \"{path}\"")
            
            # 检查设备是否支持write方法
            if not hasattr(self.P9371B_VISA, 'write'):
                logger.error("Device does not support write method.")
                return None
                
            self.P9371B_VISA.write(f":MMEMory:CDIRectory \"{path}\"")
            logger.debug(f"Current Remote directory set to '{path}'")
            
            # 检查设备是否支持query方法
            if hasattr(self.P9371B_VISA, 'query'):
                return self.P9371B_VISA.query(':MMEMory:CDIRectory?')
            else:
                logger.warning("Device does not support query method for directory check")
                return path  # 返回路径作为成功标识
        except visa.VisaIOError as e:
            logger.error(f"VISA IO Error setting directory: {e}")
            return None
        except AttributeError as e:
            logger.error(f"Attribute error setting directory: {e}")
            return None
        except Exception as e:
            logger.error(f"Error setting directory: {e}")
            return None

    # FIXED: 这里的数据存储的参数是否正确，需要验证，直接观察不易确认
    def data_dump(self, filename, data_type="CSV Formatted Data", scope="Trace", data_format="Displayed", selector=-1):
        """
        Dump data from the VNA to a file.

        Args:
            filename (str): 文件的命名及拓展名
            data_type (str, optional): 文件类型，默认csv
            scope (str, optional): 存储的数据量（Trace，Displayed，Channel，Auto），默认Trace
            data_format (str, optional): 数据的形式（Displayed，RI，MA，DB），默认Displayed
            selector (int, optional): 数据测量编号选择，默认-1（Use when scope = Displayed）

        Returns:
            Status
        """
        if not self.P9371B_VISA:
            logger.warning("No device session is open.")
            return None
        try:
            logger.debug(f"Dumping data to file: {filename}")

            # DONE: TIMEOUT ERROR
            # 2025-07-29-00:13@Linn Solution: Use write instead of query, because :MMEMory:STORe:DATA is a write-only command.
            # response = self.query(f":MMEMory:STORe:DATA \"{filename}\", \"{type}\", \"{scope}\", \"{format}\", {selector}")
            self.P9371B_VISA.write(f":MMEMory:STORe:DATA \"{filename}\", \"{data_type}\", \"{scope}\", \"{data_format}\", {selector}")

            return True
        except visa.VisaIOError as e:
            logger.error(f"Error dumping data: {e}")
            return None