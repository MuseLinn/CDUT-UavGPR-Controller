# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# 获取当前目录的绝对路径 - 使用sys.argv[0]获取spec文件路径
spec_file_path = sys.argv[0]
current_dir = os.path.dirname(os.path.abspath(spec_file_path))
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

# 添加图标 - 修正路径为项目内的图标文件
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
    # 修正图标路径
    icon=r'lib/app_logo.png'
)

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='gpr_daq_gui'
)