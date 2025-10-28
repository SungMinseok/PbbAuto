"""
PyInstaller build script
Automatically builds EXE and embeds version info
"""

import os
import sys
import json
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

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
    version = version_info.get('version', '1.0-25.01.01.0000')

    # 버전 형식: 1.0-yy.mm.dd.hhmm
    # Windows 버전 형식: 1,0,yymmdd,hhmm
    if '-' in version:
        # 1.0-yy.mm.dd.hhmm → [1, 0, yy, mm, dd, hhmm]로 분할
        major_minor, date_time = version.split('-')
        major, minor = major_minor.split('.')
        date_time_parts = date_time.split('.')
        
        # Windows 버전은 숫자 4개: major.minor.yymmdd.hhmm
        if len(date_time_parts) >= 4:
            yy, mm, dd, hhmm = date_time_parts[:4]
            yymmdd = f"{yy}{mm}{dd}"
            file_version_parts = [major, minor, yymmdd, hhmm]
        else:
            file_version_parts = ['1', '0', '0', '0']
    else:
        # 레거시 형식 (yyyy.mm.dd.hhmm)
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
import os
import sys

block_cipher = None

# PyQt5 플러그인 수동 수집
def collect_pyqt5_data():
    datas = []
    binaries = []
    
    try:
        import PyQt5
        pyqt5_path = os.path.dirname(PyQt5.__file__)
        print(f"[DEBUG] PyQt5 path: {{pyqt5_path}}")
        
        # Qt5/plugins 디렉토리 찾기
        plugins_dir = os.path.join(pyqt5_path, 'Qt5', 'plugins')
        if not os.path.exists(plugins_dir):
            plugins_dir = os.path.join(pyqt5_path, 'Qt', 'plugins')
        
        print(f"[DEBUG] Plugins dir: {{plugins_dir}}, exists: {{os.path.exists(plugins_dir)}}")
        
        if os.path.exists(plugins_dir):
            # platforms 플러그인 (필수)
            platforms_dir = os.path.join(plugins_dir, 'platforms')
            if os.path.exists(platforms_dir):
                for file in os.listdir(platforms_dir):
                    if file.endswith('.dll'):
                        src = os.path.join(platforms_dir, file)
                        datas.append((src, 'PyQt5/Qt5/plugins/platforms'))
                        print(f"[DEBUG] Added platform plugin: {{file}}")
            
            # 기타 플러그인 디렉토리들
            for plugin_type in ['styles', 'imageformats', 'iconengines']:
                plugin_dir = os.path.join(plugins_dir, plugin_type)
                if os.path.exists(plugin_dir):
                    for file in os.listdir(plugin_dir):
                        if file.endswith('.dll'):
                            src = os.path.join(plugin_dir, file)
                            datas.append((src, f'PyQt5/Qt5/plugins/{{plugin_type}}'))
        
        # Qt5/bin 디렉토리의 DLL 파일들
        qt5_bin_dir = os.path.join(pyqt5_path, 'Qt5', 'bin')
        if not os.path.exists(qt5_bin_dir):
            qt5_bin_dir = os.path.join(pyqt5_path, 'Qt', 'bin')
        
        if os.path.exists(qt5_bin_dir):
            for file in os.listdir(qt5_bin_dir):
                if file.endswith('.dll'):
                    src = os.path.join(qt5_bin_dir, file)
                    binaries.append((src, '.'))
        
        print(f"[DEBUG] Collected {{len(datas)}} data files and {{len(binaries)}} binaries")
    except Exception as e:
        print(f"Warning: Could not collect PyQt5 data: {{e}}")
    
    return datas, binaries

pyqt5_datas, pyqt5_binaries = collect_pyqt5_data()

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=pyqt5_binaries,
    datas=[
        {datas_str},
    ] + pyqt5_datas,
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        'pyautogui',
        'pygetwindow',
        'win32gui',
        'win32con',
        'win32api',
        'pywintypes',
        'pydirectinput',
        'pytesseract',
        'openpyxl',
        'PIL',
        'requests',
        'packaging',
        'unittest',
    ],
    hookspath=[os.getcwd()],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
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
    icon='probe.ico',
)
"""
    with open('PbbAuto.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print("[DONE] Spec file created: PbbAuto.spec")
    return 'PbbAuto.spec'


def force_remove_directory(path):
    """강제로 디렉토리 삭제 (Windows 권한 문제 해결)"""
    if not os.path.exists(path):
        return
    
    try:
        # 먼저 일반 삭제 시도
        shutil.rmtree(path, ignore_errors=True)
        
        # 여전히 존재하면 attrib으로 읽기 전용 해제 후 재시도
        if os.path.exists(path):
            print(f"[INFO] Removing read-only attributes from {path}...")
            try:
                subprocess.run(f'attrib -R "{path}\\*" /S /D', shell=True, check=False, 
                             capture_output=True, timeout=10)
            except:
                pass
            
            # 다시 삭제 시도
            shutil.rmtree(path, ignore_errors=True)
        
        # 그래도 존재하면 rd 명령 사용
        if os.path.exists(path):
            print(f"[INFO] Using rd command to remove {path}...")
            try:
                subprocess.run(f'rd /s /q "{path}"', shell=True, check=False,
                             capture_output=True, timeout=10)
            except:
                pass
    except Exception as e:
        print(f"[WARNING] Could not fully remove {path}: {e}")


def build_exe(spec_file):
    """Run PyInstaller build"""
    print("\n" + "=" * 60)
    print("Starting EXE build...")
    print("=" * 60 + "\n")

    # EXE가 이미 존재하면 빌드 건너뛰기
    exe_path = 'dist/BundleEditor.exe'
    zip_path = 'dist/BundleEditor.zip'
    if os.path.exists(exe_path):
        print(f"[SKIP] EXE already exists: {exe_path}")
        return True
    if os.path.exists(zip_path):
        print(f"[SKIP] ZIP already exists: {zip_path}")
        return True

    # 빌드 폴더 강제 삭제
    print("[INFO] Cleaning build directories...")
    for folder in ['build', 'dist']:
        force_remove_directory(folder)
    
    print("[INFO] Build directories cleaned.")

    try:
        # PyQt5 경로 설정
        import PyQt5
        pyqt5_path = os.path.dirname(PyQt5.__file__)
        qt_plugin_path = os.path.join(pyqt5_path, 'Qt5', 'plugins')
        
        # 환경 변수 설정
        env = os.environ.copy()
        env['QT_PLUGIN_PATH'] = qt_plugin_path
        env['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugin_path, 'platforms')
        
        # PyInstaller를 Python 모듈로 직접 호출 (출력을 직접 표시)
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', spec_file]
        print(f"[INFO] Running command: {' '.join(cmd)}")
        print(f"[INFO] QT_PLUGIN_PATH={qt_plugin_path}")
        result = subprocess.run(cmd, check=False, env=env)
        
        if result.returncode != 0:
            raise Exception(f"PyInstaller failed with code {result.returncode}")
        
        # EXE 파일 생성 확인
        exe_path = 'dist/BundleEditor.exe'
        if not os.path.exists(exe_path):
            raise Exception(f"EXE file not found at: {exe_path}")
        
        print("\n[DONE] Build successful! EXE located in: dist/BundleEditor.exe")
        return True
    except Exception as e:
        print(f"\n[FAILED] Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_zip_package():
    """Create BundleEditor.zip with BundleEditor.exe and version.json"""
    exe_path = 'dist/BundleEditor.exe'
    version_json_path = 'version.json'
    zip_path = 'dist/BundleEditor.zip'
    
    # ZIP이 이미 존재하면 생성 건너뛰기
    if os.path.exists(zip_path):
        print(f"[SKIP] ZIP already exists: {zip_path}")
        return True
    
    if not os.path.exists(exe_path):
        print(f"[ERROR] BundleEditor.exe not found at: {exe_path}")
        return False
    
    if not os.path.exists(version_json_path):
        print(f"[ERROR] version.json not found at: {version_json_path}")
        return False
    
    try:
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(exe_path, 'BundleEditor.exe')
            zipf.write(version_json_path, 'version.json')
        
        print(f"[DONE] Zip package created: {zip_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create zip package: {e}")
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

    print("\n[1/5] Creating version file...")
    create_version_file()

    print("\n[2/5] Creating spec file...")
    spec_file = create_spec_file()

    print("\n[3/5] Building EXE...")
    if not build_exe(spec_file):
        sys.exit(1)

    print("\n[4/5] Creating zip package...")
    if not create_zip_package():
        sys.exit(1)

    print("\n[5/5] Cleaning up...")
    clean_build()

    # ❌ dist/BundleEditor.exe 삭제
    exe_path = Path("dist/BundleEditor.exe")
    if exe_path.exists():
        exe_path.unlink()
        print(f"[INFO] Deleted executable: {exe_path}")
    else:
        print(f"[INFO] No executable to delete at: {exe_path}")

    print("\nBuild completed successfully!")
    print("Generated files:")
    print("  - dist/BundleEditor.zip")


if __name__ == '__main__':
    sys.exit(main())
