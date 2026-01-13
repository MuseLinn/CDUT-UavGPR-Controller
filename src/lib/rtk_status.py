# -*- coding: utf-8 -*-
"""
Author       : Linn
Date         : 2026-01-13 02:04:03
LastEditors  : Linn
LastEditTime : 2026-01-13 12:10:00
FilePath     : \\usbvna\\src\\lib\\rtk_status.py
Description  : RTK状态栏组件

Copyright (c) 2026 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
"""

from datetime import datetime
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout)
from qfluentwidgets import (HeaderCardWidget, BodyLabel) # 添加RTK状态栏需要的组件

class RTKStatusBar(HeaderCardWidget):
    """RTK状态栏"""
    
    def __init__(self, parent=None):
        super().__init__()
        self.setTitle('RTK状态')
        
        # 创建标签
        self.time_label = BodyLabel("系统时间: --:--:--")
        self.satellite_label = BodyLabel("卫星数: -")
        self.fix_type_label = BodyLabel("定位类型: -")
        self.position_label = BodyLabel("位置: lat --.------, lon --.------, alt ----.- m")
        
        # 设置标签最小宽度
        self.time_label.setMinimumWidth(150)
        self.satellite_label.setMinimumWidth(80)
        self.fix_type_label.setMinimumWidth(100)
        
        # 创建垂直布局容器
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 创建第一行水平布局（时间信息）
        time_layout = QHBoxLayout()
        time_layout.setSpacing(10)
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        
        # 创建第二行水平布局（卫星数和定位类型）
        satellite_layout = QHBoxLayout()
        satellite_layout.setSpacing(10)
        satellite_layout.addWidget(self.satellite_label)
        satellite_layout.addWidget(self.fix_type_label)
        satellite_layout.addStretch()
        
        # 创建第三行水平布局（位置信息）
        position_layout = QHBoxLayout()
        position_layout.setSpacing(10)
        position_layout.addWidget(self.position_label)
        position_layout.addStretch()
        
        # 将三行布局添加到主布局
        layout.addLayout(time_layout)
        layout.addLayout(satellite_layout)
        layout.addLayout(position_layout)
        
        # 添加布局到视图
        self.viewLayout.addLayout(layout)
        
        # 缓存上一次显示的数据，避免不必要的更新
        self._last_display_data = {}
    
    def update_display(self, data):
        """高效更新显示内容，仅在数据变化时更新UI"""
        try:
            # 检查数据是否发生变化，避免不必要的UI更新
            updates = {}
            
            # 时间信息
            gps_time = data.get('utc_time', '')
            if gps_time and len(gps_time) >= 6:
                # 将GPS时间（UTC）转换为UTC+8
                try:
                    utc_hour = int(gps_time[:2])
                    utc8_hour = (utc_hour + 8) % 24
                    time_str = f"{utc8_hour:02d}:{gps_time[2:4]}:{gps_time[4:6]}"
                    time_text = f"GPS时间: {time_str}（已同步UTC+8）"
                except (ValueError, IndexError):
                    current_time = datetime.now().strftime("%H:%M:%S")
                    time_text = f"系统时间: {current_time} (GPS时间解析错误)"
            else:
                # 如果没有GPS时间，则显示系统时间
                current_time = datetime.now().strftime("%H:%M:%S")
                time_text = f"系统时间: {current_time}"
                
            if self._last_display_data.get('time') != time_text:
                self.time_label.setText(time_text)
                updates['time'] = time_text
                
            # 卫星数
            satellites = data.get('satellites', '-')
            # 如果是GSA数据，需要计算卫星数量
            if isinstance(satellites, list):
                # 过滤掉空的卫星ID
                valid_satellites = [sat for sat in satellites if sat.strip()]
                satellites = str(len(valid_satellites))
            satellite_text = f"卫星数: {satellites}"
            
            if self._last_display_data.get('satellites') != satellite_text:
                self.satellite_label.setText(satellite_text)
                updates['satellites'] = satellite_text
                
            # 定位类型 - 使用quality字段（来自GGA）而不是fix_type（来自GSA）
            quality = data.get('quality', '')  # GGA数据中的定位质量
            fix_type_text = ""
            if quality == '0':
                fix_type_text = "未定位"
            elif quality == '1':
                fix_type_text = "单点定位"
            elif quality == '2':
                fix_type_text = "伪距/SBAS"
            elif quality == '3':
                fix_type_text = "无效PPS"
            elif quality == '4':
                fix_type_text = "RTK固定解"
            elif quality == '5':
                fix_type_text = "RTK浮点解"
            elif quality == '6':
                fix_type_text = "正在估算"
            elif quality == '7':
                fix_type_text = "手动模式"
            elif quality == '8':
                fix_type_text = "RTK宽窄解"
            elif quality == '9':
                fix_type_text = "伪距（诺瓦泰615）"
            else:
                fix_type_text = "未知"
                    
            fix_type_display = f"定位类型: {fix_type_text}"
            
            if self._last_display_data.get('fix_type') != fix_type_display:
                self.fix_type_label.setText(fix_type_display)
                updates['fix_type'] = fix_type_display
                
            # 位置信息
            latitude = data.get('latitude', '--.------')
            longitude = data.get('longitude', '--.------')
            altitude = data.get('altitude', '----.-')
            position_text = f"位置: lat {latitude}, lon {longitude}, alt {altitude} m"
            
            if self._last_display_data.get('position') != position_text:
                self.position_label.setText(position_text)
                updates['position'] = position_text
                
            # 更新缓存
            self._last_display_data.update(updates)
            
            # 如果有任何更新，记录日志（用于调试）
            if updates:
                print(f"RTK状态栏更新: {list(updates.keys())}")
                
        except Exception as e:
            print(f"RTK状态栏更新时出错: {str(e)}")
