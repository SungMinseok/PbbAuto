"""
PyInstaller 빌드 스크립트
EXE 파일 생성 및 버전 정보 임베딩
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


def load_version_info():
    """version.json에서 버전 정보 로드"""
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"버전 정보 로드 실패: {e}")
        return {'version': '1.0.0'}


def create_version_file():
    """
    Windows용 버전 파일 생성
    PyInstaller에서 EXE 파일에 버전 정보를 임베딩하는 데 사용
    """
    version_info = load_version_info()
    version = version_info.get('version', '1.0.0.0')
    
    # 버전을 4자리 형식으로 변환
    # 예: 1.0.251018.1530 -> 이미 4자리
    # 예: 1.0.0 -> 1.0.0.0
    version_parts = version.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')
    
    # 4자리로 제한하고 각 파트가 65535를 초과하지 않도록 처리
    file_version_parts = []
    for part in version_parts[:4]:
        try:
            num = int(part)
            # Windows 버전은 각 파트가 0-65535 범위여야 함
            if num > 65535:
                num = 65535
            file_version_parts.append(str(num))
        except ValueError:
            file_version_parts.append('0')
    
    file_version = '.'.join(file_version_parts)
    
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
        StringStruct(u'FileDescription', u'PbbAuto - 자동화 테스트 도구'),
        StringStruct(u'FileVersion', u'{file_version}'),
        StringStruct(u'InternalName', u'PbbAuto'),
        StringStruct(u'LegalCopyright', u'Copyright 2025'),
        StringStruct(u'OriginalFilename', u'PbbAuto.exe'),
        StringStruct(u'ProductName', u'PbbAuto'),
        StringStruct(u'ProductVersion', u'{file_version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_file_content)
    
    print(f"버전 파일 생성 완료: {file_version}")
    return 'version_info.txt'


def create_spec_file():
    """PyInstaller spec 파일 생성"""
    
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
    name='PbbAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',  # 버전 정보 파일
    icon=None,  # TODO: 아이콘 파일 추가
)
"""
    
    with open('PbbAuto.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("Spec 파일 생성 완료: PbbAuto.spec")
    return 'PbbAuto.spec'


def build_exe(spec_file):
    """PyInstaller로 EXE 빌드"""
    print("\n" + "="*60)
    print("EXE 빌드 시작...")
    print("="*60 + "\n")
    
    # 빌드 전에 build/dist 폴더 정리
    print("기존 빌드 파일 정리 중...")
    if os.path.exists('build'):
        try:
            shutil.rmtree('build')
            print("  build/ 삭제 완료")
        except Exception as e:
            print(f"  build/ 삭제 실패 (무시): {e}")
    
    if os.path.exists('dist'):
        try:
            shutil.rmtree('dist')
            print("  dist/ 삭제 완료")
        except Exception as e:
            print(f"  dist/ 삭제 실패 (무시): {e}")
    
    print()
    
    try:
        # PyInstaller 실행 (--clean 제거)
        cmd = ['pyinstaller', spec_file]
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("✅ 빌드 성공!")
            print("="*60)
            print(f"실행 파일: dist/PbbAuto.exe")
            return True
        else:
            print("\n❌ 빌드 실패")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 빌드 중 오류 발생: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ PyInstaller가 설치되지 않았습니다.")
        print("다음 명령어로 설치하세요: pip install pyinstaller")
        return False




def clean_build():
    """빌드 임시 파일 정리"""
    print("\n빌드 임시 파일 정리 중...")
    
    dirs_to_clean = ['build', '__pycache__']
    files_to_clean = ['version_info.txt']
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  삭제: {d}/")
    
    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)
            print(f"  삭제: {f}")
    
    print("정리 완료!")


def main():
    """메인 빌드 프로세스"""
    print("="*60)
    print("PbbAuto 빌드 스크립트")
    print("="*60)
    
    # 버전 정보 로드 및 표시
    version_info = load_version_info()
    print(f"\n버전: {version_info.get('version', '알 수 없음')}")
    print(f"빌드 날짜: {version_info.get('build_date', '알 수 없음')}")
    
    # 1. 버전 파일 생성
    print("\n[1/4] 버전 파일 생성...")
    version_file = create_version_file()
    
    # 2. Spec 파일 생성
    print("\n[2/4] Spec 파일 생성...")
    spec_file = create_spec_file()
    
    # 3. EXE 빌드
    print("\n[3/4] EXE 빌드...")
    if not build_exe(spec_file):
        print("\n빌드 실패!")
        return 1
    
    # 4. 정리
    print("\n[4/4] 정리...")
    clean_build()
    
    print("\n" + "="*60)
    print("✅ 모든 빌드 작업 완료!")
    print("="*60)
    print("\n생성된 파일:")
    print("  - dist/PbbAuto.exe")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

