# -*- coding: utf-8 -*-
"""
Author       : MuseLinn
Date         : 2025-07-26 16:05:07
LastEditors  : MuseLinn
LastEditTime : 2025-07-27 16:23:50
FilePath     : \\usbvna\\pyvisa_ctrl.py
Description  : For KeySight USB VNA control via PyVISA

Copyright (c) 2025 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

import pyvisa as visa

# DEBUG标志，设置为True时会打印调试信息
DEBUG = False

def debug_print(*args, **kwargs):
    """调试打印函数，只有当DEBUG标志为True时才打印信息"""
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)


# rm = pyvisa.ResourceManager()

# VNA Control Class
class VNAController:
    """A class to control a KeySight USB VNA using PyVISA."""

    # Initialize the VISA Resource Manager and session
    def __init__(self):
        self.rm = visa.ResourceManager()
        debug_print("VISA Resource Manager initialized")
        self.session = None

    def list_devices(self):
        """List all connected VISA devices."""
        resources = self.rm.list_resources()
        debug_print(f"Found resources: {resources}")
        return resources

    def open_device(self, resource_name):
        """Open a VISA device."""
        try:
            debug_print(f"Opening device: {resource_name}")
            self.session = self.rm.open_resource(resource_name)
            debug_print(f"Device opened successfully: {self.session}")
            return self.session
        except visa.VisaIOError as e:
            print(f"Error opening device {resource_name}: {e}")
            return None

    def close_device(self):
        """Close the opened VISA device."""
        if self.session:
            try:
                debug_print("Closing device")
                self.session.close()
            except visa.VisaIOError as e:
                print(f"Error closing device: {e}")
            finally:
                self.session = None
                debug_print("Device closed")

    def query(self, command):
        """Send a command to the device and return the response."""
        if not self.session:
            print("No device session is open.")
            return None
        try:
            debug_print(f"Sending command: {command}")
            # 检查是否有query方法，如果有则直接使用
            if hasattr(self.session, 'query'):
                response = self.session.query(command)
                debug_print(f"Response received: {response}")
                return response
            # 否则尝试使用write和read方法组合
            elif hasattr(self.session, 'write') and hasattr(self.session, 'read'):
                self.session.write(command)
                response = self.session.read()
                debug_print(f"Response received: {response}")
                return response
            else:
                print("Device does not support query, write, or read methods.")
                return None
        except visa.VisaIOError as e:
            print(f"Error querying device: {e}")
            return None


# Main Code: Device Connection Test
if __name__ == "__main__":
    debug_print("Starting VNA Controller")
    vna_controller = VNAController()

    # List connected devices
    devices = vna_controller.list_devices()
    print("Connected VISA devices:", devices)

    # Open a device (replace 'USB0::0x0957::0x0607::MY12345678::INSTR' with your device's resource name)
    if devices:
        # device = vna_controller.open_device('devices[0]')
        # NOTE: Theoretically, the resource name could be accessed by list_devices() function. But in my case, the resource name is not accessible.
        # For controlling KeySight VNA(P9371B) with PyVISA, we should enable HiSLIP
        device = vna_controller.open_device('TCPIP0::DESKTOP-U2340VT::hislip_PXI0_CHASSIS1_SLOT1_INDEX0::INSTR')
        if device:
            print(f"Device {device} opened successfully.")
            # Perform operations with the device here
            device.timeout = 20000
            debug_print(f"Device timeout set to {device.timeout}ms")
            print("Querying device for IDN...")
            print(vna_controller.query("*IDN?"))  # Query the device ID

            # Close the device after operations
            vna_controller.close_device()
            print("Device closed successfully.")
    else:
        print("No VISA devices found.")
    debug_print("VNA Controller finished")