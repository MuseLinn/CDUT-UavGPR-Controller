# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2025-07-28 17:02:03
LastEditors  : Linn
LastEditTime : 2026-01-13 04:50:00
FilePath     : \\usbvna\\src\\main_gui.py
Description  : Main program to control the USB-VNA P9371B, GPR DATA Acquisition Software

Copyright (c) 2026 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

import sys
# import os

# 将src目录添加到Python路径中，以便可以导入lib模块
# sys.path.append(os.path.join(os.path.dirname(__file__))) # 以下已作为包导入

# 从lib模块导入VNAController类和日志配置函数
from lib.logger_config import setup_logger
from lib.main_window import VNAControllerGUI

# NOTE: 创建日志记录器，使用轮转日志文件，每个文件最大10MB，保留5个备份文件
logger = setup_logger("vna_gui", "logs/vna_gui.log", level=10)  # 10对应DEBUG级别

from PyQt6.QtWidgets import (
    QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

def main():
    """主函数"""
    logger.debug("Starting VNA Controller GUI")
    
    app = QApplication(sys.argv)
    
    # 设置默认字体，解决字体发虚问题
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 设置高DPI适配，解决字体发虚问题 (PyQt6中移除了这些属性)
    # PyQt6默认启用了高DPI支持，无需手动设置
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 设置应用程序属性
    app.setApplicationName("CDUT-非显性滑坡延缓高效勘测技术装备研发")
    app.setApplicationVersion("0.8a")

    window = VNAControllerGUI()
    window.show()
    logger.info("GUI Windows opened")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()