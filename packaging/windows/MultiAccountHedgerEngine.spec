# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path.cwd()

datas = [
    (str(ROOT / "app.py"), "."),
    (str(ROOT / "launcher.py"), "."),
    (str(ROOT / "clients"), "clients"),
    (str(ROOT / "core"), "core"),
    (str(ROOT / "notify"), "notify"),
    (str(ROOT / "config" / "global_config.json"), "config"),
    (str(ROOT / "config" / "strategy_config.json"), "config"),
    (str(ROOT / "config" / "accounts.json.example"), "config"),
]
binaries = []
hiddenimports = []

for package in ["aiohttp", "websockets", "certifi"]:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports


a = Analysis(
    ["windows_engine.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
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
    name="MultiAccountHedgerEngine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MultiAccountHedgerEngine",
)
