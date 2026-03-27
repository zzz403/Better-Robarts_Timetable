"""
Setup script for creating macOS app bundle
"""
import os
from pathlib import Path

# PyInstaller spec file content
spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.py', '.'),
        ('script.py', '.'),
        ('requirements.txt', '.'),
        ('README.md', '.'),
        ('uoft_study_rooms.csv', '.'),
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'pandas',
        'sqlite3',
        'requests',
        'datetime',
        'os',
        'json',
        'csv',
        'time',
        'webbrowser',
        'threading',
        'subprocess',
        'socket',
        'pathlib',
        'importlib.util',
        'altair',
        'plotly',
        'click',
        'tornado',
        'tzlocal',
        'pyarrow'
    ],
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
    [],
    exclude_binaries=True,
    name='UofT Study Rooms',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UofT Study Rooms',
)

app = BUNDLE(
    coll,
    name='UofT Study Rooms.app',
    icon=None,
    bundle_identifier='ca.utoronto.studyrooms',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'UofT Study Rooms',
        'CFBundleDisplayName': 'UofT Study Rooms',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': 'True',
    },
)
'''

# Write the spec file
with open('UofT_Study_Rooms.spec', 'w') as f:
    f.write(spec_content)

print("✅ Created PyInstaller spec file: UofT_Study_Rooms.spec")
print("\n📋 To build the macOS app, run:")
print("pip install pyinstaller")
print("pyinstaller UofT_Study_Rooms.spec")
print("\n📁 The app will be created in the 'dist' folder")