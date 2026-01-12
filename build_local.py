'''
Author       : MuseLinn
Date         : 2026-01-12 17:53:30
LastEditors  : MuseLinn
LastEditTime : 2026-01-12 21:30:54
FilePath     : \CDUT_UavGPR_Controller_v202511\build_local.py
Description  : 

Copyright (c) 2026 by Linn email: universe_yuan@icloud.com, All Rights Reserved.
'''
#!/usr/bin/env python
"""
本地构建脚本 - 用于测试构建过程
"""
import os
import subprocess
import sys

def build_locally():
    """本地构建函数"""
    print("开始本地构建...")
    
    # 切换到 src 目录
    os.chdir('src')
    
    # 安装 PyInstaller（如果尚未安装）
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    # 构建可执行文件
    result = subprocess.run(['pyinstaller', 'main_gui.spec'], check=True)
    
    if result.returncode == 0:
        print("构建成功！生成的可执行文件位于 dist/ 目录")
        print(f"可执行文件路径: {os.path.abspath('dist/gpr_daq_gui.exe')}")
    else:
        print("构建失败！")

if __name__ == "__main__":
    build_locally()