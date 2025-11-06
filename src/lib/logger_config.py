# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2025-07-28 17:30:00
LastEditors  : Linn
LastEditTime : 2025-07-28 17:30:00
FilePath     : \\usbvna\\src\\lib\\logger_config.py
Description  : 日志配置模块，提供统一的日志配置功能

Copyright (c) 2025 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

import logging
import colorlog
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name, log_file=None, level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """
    配置并返回一个日志记录器
    
    Args:
        name (str): 日志记录器名称
        log_file (str, optional): 日志文件路径，默认为None
        level (int): 日志级别，默认为INFO
        max_bytes (int): 单个日志文件的最大字节数，默认为10MB
        backup_count (int): 保留的备份日志文件数量，默认为5个
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建彩色控制台处理器
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置彩色日志格式
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    
    # 将控制台处理器添加到日志记录器
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，则添加文件处理器
    if log_file:
        # 确保日志文件目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 创建轮转文件处理器
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(logging.DEBUG)
        
        # 设置日志格式
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        # 将文件处理器添加到日志记录器
        logger.addHandler(file_handler)
    
    return logger