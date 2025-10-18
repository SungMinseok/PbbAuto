"""
PyInstaller build script
Create EXE file and embed version information
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


def load_version_info():
    """Load version info from version.json"""
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load version info: {e}")
        return {'version': '1.0.0'}


def create_version_file():
    """
    Create Windows version file
    Used by PyInstaller to embed version info in EXE
    """
    version_info = load_version_info()
    version = version_info.get('version', '2025.01.01.0000')
    
    # CalVer format: YYYY.MM.DD.HHMM
    # Windows version file requires each part to be 0-65535
    # YYYY always exceeds 65535, so needs processing
    
    version_parts = version.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')
    
    # For Windows version file: limit each part to 0-65535 range
    file_version_parts = []
    for i, part in enumerate(version_parts[:4]):
        try:
            num = int(part)
            # If first part (YYYY) exceeds 65535, limit it
            if num > 65535:
                # Convert YYYY -> YY (2025 -> 25)
                if i == 0 and num > 2000:
                    num = num % 100  # 2025 -> 25
                else:
                    num = 65535
            file_version_parts.append(str(num))
        except ValueError:
            file_version_parts.append('0')
    
    file_version = '.'.join(file_version_parts)
    display_version = version  # Original version to display
    
    version_file_content = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({','.join(file_version_parts)}),
    prodvers=({','.join(file_version_parts)}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'PbbAuto Team'),
        StringStruct(u'FileDescription', u'PbbAuto - Automation Test Tool'),
        StringStruct(u'FileVersion', u'{display_version}'),
        StringStruct(u'InternalName', u'PbbAuto'),
        StringStruct(u'LegalCopyright', u'Copyright 2025'),
        StringStruct(u'OriginalFilename', u'PbbAuto.exe'),
        StringStruct(u'ProductName', u'PbbAuto'),
        StringStruct(u'ProductVersion', u'{display_version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_file_content)
    
    print(f"Version file created: {display_version} (Windows: {file_version})")
    return 'version_info.txt'


def create_spec_file():
    """Create PyInstaller spec file"""
    
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('version.json', '.'),
        ('bundles', 'bundles'),
        ('preset', 'preset'),
        ('design', 'design'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'pyautogui',
        'pygetwindow',
        'pydirectinput',
        'pytesseract',
        'openpyxl',
        'PIL',
        'requests',
        'packaging',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Bundle Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',  # Version info file
    icon=None,  # TODO: Add icon file
)
"""
    
    with open('PbbAuto.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("Spec file created: PbbAuto.spec")
    return 'PbbAuto.spec'


def build_exe(spec_file):
    """Build EXE with PyInstaller"""
    print("\n" + "="*60)
    print("Starting EXE build...")
    print("="*60 + "\n")
    
    # Clean build/dist folders before building
    print("Cleaning existing build files...")
    if os.path.exists('build'):
        try:
            shutil.rmtree('build')
            print("  build/ deleted")
        except Exception as e:
            print(f"  build/ deletion failed (ignored): {e}")
    
    if os.path.exists('dist'):
        try:
            shutil.rmtree('dist')
            print("  dist/ deleted")
        except Exception as e:
            print(f"  dist/ deletion failed (ignored): {e}")
    
    print()
    
    try:
        # Run PyInstaller (without --clean)
        cmd = ['pyinstaller', spec_file]
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("Build successful!")
            print("="*60)
            print(f"Executable: dist/Bundle Editor.exe")
            return True
        else:
            print("\nBuild failed")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\nError during build: {e}")
        return False
    except FileNotFoundError:
        print("\nPyInstaller is not installed.")
        print("Install it with: pip install pyinstaller")
        return False




def clean_build():
    """Clean up build temporary files"""
    print("\nCleaning up build files...")
    
    dirs_to_clean = ['build', '__pycache__']
    files_to_clean = ['version_info.txt']
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  Deleted: {d}/")
    
    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)
            print(f"  Deleted: {f}")
    
    print("Cleanup completed!")


def main():
    """Main build process"""
    print("="*60)
    print("PbbAuto Build Script")
    print("="*60)
    
    # Load and display version info
    version_info = load_version_info()
    print(f"\nVersion: {version_info.get('version', 'unknown')}")
    print(f"Build date: {version_info.get('build_date', 'unknown')}")
    
    # 1. Create version file
    print("\n[1/4] Creating version file...")
    version_file = create_version_file()
    
    # 2. Create spec file
    print("\n[2/4] Creating spec file...")
    spec_file = create_spec_file()
    
    # 3. Build EXE
    print("\n[3/4] Building EXE...")
    if not build_exe(spec_file):
        print("\nBuild failed!")
        return 1
    
    # 4. Clean up
    print("\n[4/4] Cleaning up...")
    clean_build()
    
    print("\n" + "="*60)
    print("Build completed successfully!")
    print("="*60)
    print("\nGenerated files:")
    print("  - dist/Bundle Editor.exe")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

