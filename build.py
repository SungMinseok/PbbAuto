"""
PyInstaller build script
Automatically builds EXE and embeds version info
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime


def load_version_info():
    """Load version info from version.json"""
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARNING] Failed to load version info: {e}")
        return {'version': '0.0.0-dev', 'build_date': datetime.now().strftime("%Y-%m-%d")}


def create_version_file():
    """Create Windows version info file for embedding"""
    version_info = load_version_info()
    version = version_info.get('version', '2025.01.01.0000')

    version_parts = version.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')

    file_version_parts = []
    for i, part in enumerate(version_parts[:4]):
        try:
            num = int(part)
            if num > 65535:
                if i == 0 and num > 2000:
                    num = num % 100  # 2025 → 25
                else:
                    num = 65535
            file_version_parts.append(str(num))
        except ValueError:
            file_version_parts.append('0')

    display_version = version
    file_version = ','.join(file_version_parts)

    version_file_content = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({file_version}),
    prodvers=({file_version}),
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

    print(f"[DONE] Version file created: {display_version}")
    return 'version_info.txt'


def create_spec_file():
    """Generate PyInstaller spec file dynamically"""
    # Ensure version.json exists
    if not os.path.exists('version.json'):
        print("[WARNING] version.json not found, creating default one...")
        with open('version.json', 'w', encoding='utf-8') as f:
            json.dump({
                "version": "0.0.0-dev",
                "build_date": datetime.now().strftime("%Y-%m-%d")
            }, f, indent=2)

    datas_list = ["('version.json', '.')"]

    for folder in ['bundles', 'preset', 'design']:
        if os.path.exists(folder):
            datas_list.append(f"('{folder}', '{folder}')")

    datas_str = ",\n        ".join(datas_list)

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],  # Include current directory
    binaries=[],
    datas=[
        {datas_str},
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
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'unittest',
        'distutils',
        'pydoc',
        'extension-output-ms-dotnettools.vscode-dotnet-runtime-#1-.NET Install Tool',
        'ms-dotnettools.vscode-dotnet-runtime'
    ],
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
    name='BundleEditor',
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
    version='version_info.txt',
    icon=None,
)
"""
    with open('PbbAuto.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print("[DONE] Spec file created: PbbAuto.spec")
    return 'PbbAuto.spec'


def build_exe(spec_file):
    """Run PyInstaller build"""
    print("\n" + "=" * 60)
    print("Starting EXE build...")
    print("=" * 60 + "\n")

    for folder in ['build', 'dist']:
        shutil.rmtree(folder, ignore_errors=True)

    try:
        cmd = ['pyinstaller', '--clean', spec_file]
        subprocess.run(cmd, check=True)
        print("\n[DONE] Build successful! EXE located in: dist/Bundle Editor.exe")
        return True
    except Exception as e:
        print(f"\n[FAILED] Build failed: {e}")
        return False


def clean_build():
    """Remove temporary files"""
    for d in ['build', '__pycache__']:
        shutil.rmtree(d, ignore_errors=True)
    for f in ['version_info.txt']:
        if os.path.exists(f):
            os.remove(f)
    print("[CLEANUP] Cleanup completed!")


def main():
    print("=" * 60)
    print("PbbAuto Build Script")
    print("=" * 60)

    version_info = load_version_info()
    print(f"Version: {version_info.get('version', 'unknown')}")
    print(f"Build date: {version_info.get('build_date', 'unknown')}")

    print("\n[1/4] Creating version file...")
    create_version_file()

    print("\n[2/4] Creating spec file...")
    spec_file = create_spec_file()

    print("\n[3/4] Building EXE...")
    if not build_exe(spec_file):
        sys.exit(1)

    print("\n[4/4] Cleaning up...")
    clean_build()

    print("\nBuild completed successfully!")
    print("Generated: dist/BundleEditor.exe")


if __name__ == '__main__':
    sys.exit(main())
