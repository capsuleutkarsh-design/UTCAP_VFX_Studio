# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['qasync', 'psycopg2', 'psycopg2.pool', 'psycopg2.extras', 'PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'numpy', 'pandas', 'cv2', 'OpenImageIO', 'keyring', 'keyring.backends', 'win32ctypes', 'win32ctypes.core', 'cryptography', 'openpyxl', 'fileseq', 'PyOpenColorIO', 'opentimelineio', 'opentimelineio.adapters', 'opentimelineio.plugins']
hiddenimports += collect_submodules('ut_vfx.gui.plugins')
hiddenimports += collect_submodules('ut_vfx.plugins')
from PyInstaller.utils.hooks import collect_all
datas_qasync, binaries_qasync, hiddenimports_qasync = collect_all('qasync')
hiddenimports += hiddenimports_qasync
a = Analysis(
    ['ut_vfx\\gatekeeper_main.py'],
    pathex=[],
    binaries=[] + binaries_qasync,
    datas=[('ut_vfx/data', 'ut_vfx/data'), ('ut_vfx/assets', 'ut_vfx/assets'), ('ut_vfx/default_config.json', 'ut_vfx'), ('ut_vfx/icons', 'ut_vfx/icons'), ('ut_vfx/resources', 'ut_vfx/resources'), ('ut_vfx/bin/ffmpeg.exe', 'ut_vfx/bin'), ('ut_vfx/bin/ffprobe.exe', 'ut_vfx/bin'), ('ut_vfx/core/help_content.json', 'ut_vfx/core'), ('ut_vfx/gui/tabs/vfx_dashboard_pro/config', 'ut_vfx/gui/tabs/vfx_dashboard_pro/config'), ('ut_vfx/gui/tabs/vfx_dashboard_pro/sample_project.xlsx', 'ut_vfx/gui/tabs/vfx_dashboard_pro')] + datas_qasync,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pytest', 'sphinx', 'IPython', 'notebook', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui'],
    noarchive=False,
    optimize=0,
)


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UTVFX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ut_vfx\\icons\\app_icon.ico'],
)

server_a = Analysis(
    ['ut_server\\main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pytest', 'sphinx', 'IPython', 'notebook', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui'],
    noarchive=False,
    optimize=0,
)


server_pyz = PYZ(server_a.pure)

server_exe = EXE(
    server_pyz,
    server_a.scripts,
    [],
    exclude_binaries=True,
    name='UT_Server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ut_vfx\\icons\\server_icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    server_exe,
    server_a.binaries,
    server_a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='UTVFX',
)
