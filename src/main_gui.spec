# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# 获取当前目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
lib_path = os.path.join(current_dir, 'lib')

a = Analysis(
    ['main_gui.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[(lib_path, 'lib')],
    hiddenimports=['lib', 'lib.vna_controller', 'lib.logger_config', 'lib.fluent_window'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 添加图标
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gpr_daq_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 指定图标文件
    icon=r'C:\Users\unive\Desktop\usbvna\src\lib\app_logo.png'  # {{ edit_1 }}
)

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='gpr_daq_gui'
)