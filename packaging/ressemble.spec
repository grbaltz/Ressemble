# -*- mode: python ; coding: utf-8 -*-
#
# Builds a standalone Ressemble app for whichever OS this runs on.
# PyInstaller can't cross-compile -- run this once per target platform
# (see .github/workflows/build.yml, which does exactly that in CI).
#
#   pyinstaller packaging/ressemble.spec --noconfirm --clean --distpath dist
#
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# PyInstaller exec()s spec files rather than importing them, so __file__
# isn't available here -- it injects SPECPATH (this file's directory) instead.
REPO_ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(REPO_ROOT / "src" / "fonts" / "Avenir Black.ttf"), "src/fonts"),
    (str(REPO_ROOT / "src" / "fonts" / "Times New Roman.ttf"), "src/fonts"),
]
binaries = []
hiddenimports = []

# PySide6 and pymupdf both ship platform-specific binaries/plugins/data
# that PyInstaller's default import analysis won't find on its own.
for pkg in ("PySide6", "pymupdf", "rapidfuzz"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    [str(REPO_ROOT / "main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt6"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Ressemble",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Ressemble",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Ressemble.app",
        bundle_identifier="com.rebalance.ressemble",
    )
