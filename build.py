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
    version = version_info.get('version', '1.0.0')
    
    # 버전을 4자리 형식으로 변환 (예: 1.0.0 -> 1.0.0.0)
    version_parts = version.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')
    file_version = '.'.join(version_parts[:4])
    
    version_file_content = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({','.join(version_parts[:4])}),
    prodvers=({','.join(version_parts[:4])}),
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
    
    try:
        # PyInstaller 실행
        cmd = ['pyinstaller', '--clean', spec_file]
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


def create_portable_package():
    """포터블 버전 패키징"""
    version_info = load_version_info()
    version = version_info.get('version', '1.0.0')
    
    package_name = f"PbbAuto_v{version}_portable"
    package_dir = Path('dist') / package_name
    
    print(f"\n포터블 패키지 생성 중: {package_name}")
    
    try:
        # 패키지 디렉토리 생성
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # EXE 파일 복사
        shutil.copy('dist/PbbAuto.exe', package_dir / 'PbbAuto.exe')
        
        # 필수 파일/폴더 복사
        files_to_copy = [
            'version.json',
            'bundles',
            'preset',
            'README.md'  # 있다면
        ]
        
        for item in files_to_copy:
            if os.path.exists(item):
                if os.path.isfile(item):
                    shutil.copy(item, package_dir / item)
                else:
                    shutil.copytree(item, package_dir / item, dirs_exist_ok=True)
        
        # README 파일 생성
        readme_content = f"""PbbAuto v{version}
=====================

자동화 테스트 도구

사용 방법:
1. PbbAuto.exe를 실행하세요
2. Tesseract OCR 경로를 설정하세요
3. 명령어를 추가하고 실행하세요

자세한 내용은 GitHub 저장소를 참조하세요.

빌드 날짜: {datetime.now().strftime('%Y-%m-%d')}
"""
        
        with open(package_dir / 'README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # ZIP으로 압축
        shutil.make_archive(
            str(Path('dist') / package_name),
            'zip',
            package_dir
        )
        
        print(f"✅ 포터블 패키지 생성 완료: dist/{package_name}.zip")
        return True
        
    except Exception as e:
        print(f"❌ 패키지 생성 실패: {e}")
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
    print("\n[1/5] 버전 파일 생성...")
    version_file = create_version_file()
    
    # 2. Spec 파일 생성
    print("\n[2/5] Spec 파일 생성...")
    spec_file = create_spec_file()
    
    # 3. EXE 빌드
    print("\n[3/5] EXE 빌드...")
    if not build_exe(spec_file):
        print("\n빌드 실패!")
        return 1
    
    # 4. 포터블 패키지 생성
    print("\n[4/5] 포터블 패키지 생성...")
    create_portable_package()
    
    # 5. 정리
    print("\n[5/5] 정리...")
    clean_build()
    
    print("\n" + "="*60)
    print("✅ 모든 빌드 작업 완료!")
    print("="*60)
    print("\n생성된 파일:")
    print("  - dist/PbbAuto.exe")
    print(f"  - dist/PbbAuto_v{version_info.get('version')}_portable.zip")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

