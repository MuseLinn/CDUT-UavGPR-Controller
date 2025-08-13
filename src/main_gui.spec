# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# 获取当前目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
vna_package_path = os.path.join(current_dir, 'vna_package')

a = Analysis(
    ['main_gui.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[(vna_package_path, 'vna_package')],
    hiddenimports=['vna_package', 'vna_package.vna_controller', 'vna_package.logger_config', 'vna_package.fluent_window'],
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
    icon='GS_GPR探地雷达数据采集软件logo.png'  # {{ edit_1 }}
)

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='gpr_daq_gui'
)