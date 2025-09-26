
# -*- mode: python ; coding: utf-8 -*-

import sys
sys.setrecursionlimit(5000)

block_cipher = None

a = Analysis(
    ['E:\Desktop\keyboard_simulator\keyboard_simulator_gui.py'],
    pathex=['E:\\Desktop\\keyboard_simulator\\src'],
    binaries=[],
    datas=[],
    hiddenimports=['keyboard', 'keyboard_simulator', 'keyboard_simulator.cli', 'keyboard_simulator.config', 'keyboard_simulator.encoding', 'keyboard_simulator.logging_config', 'keyboard_simulator.simulator', 'keyboard_simulator.tasks', 'tkinterdnd2', 'tkinterdnd2.TkinterDnD'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KeyboardSimulatorGUI',
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
    icon=None,  # You can specify an icon path here, e.g., 'assets/icon.ico'
)
