"""PyInstaller spec file for building Receipt Analyzer executable."""

# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

block_cipher = None

# Data files to include
datas = []

# Add assets if they exist
assets_dir = project_root / 'receipt_analyzer' / 'assets'
if assets_dir.exists():
    datas.append((str(assets_dir), 'assets'))

# Hidden imports for modules that PyInstaller might miss
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'PIL',
    'PIL.Image',
    'yaml',
    'csv',
    'json',
    'sqlite3',
    'threading',
    'queue',
    'datetime',
    'pathlib',
    'receipt_analyzer.core',
    'receipt_analyzer.gui',
    'receipt_analyzer.gui.tabs',
]

# Optional imports that may not be available
optional_imports = [
    'fitz',          # PyMuPDF
    'pytesseract',   # Tesseract OCR
    'cv2',           # OpenCV
    'pdf2image',     # PDF2Image
    'pyperclip',     # Clipboard support
]

# Add optional imports if available
for module in optional_imports:
    try:
        __import__(module)
        hiddenimports.append(module)
    except ImportError:
        pass

a = Analysis(
    ['receipt_analyzer/main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='ReceiptAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file here if available
)