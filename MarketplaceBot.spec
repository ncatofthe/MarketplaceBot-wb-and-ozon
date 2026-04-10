# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve()
SETTINGS_DIR = PROJECT_ROOT / "settings"

datas = [
    (str(SETTINGS_DIR / "config.example.json"), "settings"),
    (str(SETTINGS_DIR / "answers.example.json"), "settings"),
]

hiddenimports = [
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.scrolledtext",
]


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarketplaceBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="MarketplaceBot",
)
