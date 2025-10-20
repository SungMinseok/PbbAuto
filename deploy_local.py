"""
로컬 빌드 후 GitHub 릴리즈 배포 스크립트
Windows Defender 문제 해결을 위한 로컬 빌드 방식
"""

import os
import sys
import json
import zipfile
import requests
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def load_version_info():
    """버전 정보 로드"""
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 버전 정보 로드 실패: {e}")
        return None


def create_zip_package(version):
    """빌드된 EXE와 필요 파일들을 ZIP으로 패키징"""
    print("\n[1/4] ZIP 패키지 생성 중...")
    
    # dist 폴더 확인
    dist_dir = Path("dist")
    exe_file = dist_dir / "BundleEditor.exe"
    
    if not exe_file.exists():
        print(f"❌ EXE 파일을 찾을 수 없습니다: {exe_file}")
        return None
    
    # ZIP 파일명
    zip_filename = f"BundleEditor_v{version}.zip"
    zip_path = Path(zip_filename)
    
    # 기존 ZIP 파일 삭제
    if zip_path.exists():
        zip_path.unlink()
    
    # ZIP 생성
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # EXE 파일 추가
        zipf.write(exe_file, "BundleEditor.exe")
        
        # 필요한 폴더들 추가
        folders_to_include = ['bundles', 'preset', 'design']
        for folder in folders_to_include:
            folder_path = Path(folder)
            if folder_path.exists():
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to('.')
                        zipf.write(file_path, arcname)
        
        # 버전 파일 추가
        if Path('version.json').exists():
            zipf.write('version.json', 'version.json')
    
    print(f"✅ ZIP 패키지 생성 완료: {zip_path}")
    return zip_path


def get_github_token():
    """GitHub 토큰 가져오기"""
    # 환경변수에서 토큰 가져오기
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    
    # 사용자 입력으로 토큰 받기
    print("\n⚠️  GitHub Personal Access Token이 필요합니다.")
    print("GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)")
    print("필요한 권한: repo (Full control of private repositories)")
    print()
    token = input("GitHub Token을 입력하세요: ").strip()
    
    if not token:
        print("❌ 토큰이 입력되지 않았습니다.")
        return None
    
    return token


def create_github_release(version, changelog, token, zip_path):
    """GitHub 릴리즈 생성 및 파일 업로드"""
    print(f"\n[2/4] GitHub 릴리즈 생성 중... (v{version})")
    
    repo_owner = "SungMinseok"
    repo_name = "PbbAuto"
    tag_name = f"v{version}"
    
    # 릴리즈 데이터
    release_data = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Release v{version}",
        "body": f"## 변경사항\n- {changelog}\n\n⚠️ **로컬 빌드 버전**: Windows Defender 호환성 개선",
        "draft": False,
        "prerelease": False
    }
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 릴리즈 생성
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
    response = requests.post(url, json=release_data, headers=headers)
    
    if response.status_code != 201:
        print(f"❌ 릴리즈 생성 실패: {response.status_code}")
        print(response.text)
        return False
    
    release_id = response.json()['id']
    print(f"✅ 릴리즈 생성 완료 (ID: {release_id})")
    
    # 파일 업로드
    print(f"[3/4] ZIP 파일 업로드 중...")
    upload_url = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/releases/{release_id}/assets"
    
    with open(zip_path, 'rb') as f:
        upload_headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/zip"
        }
        params = {
            "name": zip_path.name
        }
        
        response = requests.post(upload_url, headers=upload_headers, params=params, data=f)
    
    if response.status_code != 201:
        print(f"❌ 파일 업로드 실패: {response.status_code}")
        print(response.text)
        return False
    
    print(f"✅ 파일 업로드 완료: {zip_path.name}")
    return True


def cleanup_files(zip_path):
    """임시 파일 정리"""
    print(f"\n[4/4] 임시 파일 정리...")
    
    try:
        if zip_path and zip_path.exists():
            zip_path.unlink()
            print(f"✅ ZIP 파일 삭제: {zip_path}")
    except Exception as e:
        print(f"⚠️  파일 정리 중 오류: {e}")


def main():
    print("=" * 60)
    print("PbbAuto 로컬 빌드 배포 스크립트")
    print("=" * 60)
    
    # 버전 정보 확인
    version_info = load_version_info()
    if not version_info:
        return 1
    
    version = version_info.get('version')
    changelog = version_info.get('changelog', [{}])[0].get('changes', ['자동 배포'])[0]
    
    print(f"버전: {version}")
    print(f"변경사항: {changelog}")
    
    # dist 폴더 확인
    if not Path("dist/BundleEditor.exe").exists():
        print("\n❌ 빌드된 EXE 파일이 없습니다!")
        print("먼저 'python build.py'를 실행하여 빌드를 완료하세요.")
        return 1
    
    # 사용자 확인
    print(f"\n🚀 v{version} 릴리즈를 GitHub에 배포하시겠습니까?")
    response = input("계속하려면 'y'를 입력하세요: ").lower().strip()
    if response != 'y':
        print("배포 취소됨")
        return 0
    
    # GitHub 토큰 확인
    token = get_github_token()
    if not token:
        return 1
    
    zip_path = None
    try:
        # ZIP 패키지 생성
        zip_path = create_zip_package(version)
        if not zip_path:
            return 1
        
        # GitHub 릴리즈 생성 및 업로드
        if not create_github_release(version, changelog, token, zip_path):
            return 1
        
        print("\n" + "=" * 60)
        print("✅ 배포 완료!")
        print("=" * 60)
        print(f"릴리즈 URL: https://github.com/SungMinseok/PbbAuto/releases/tag/v{version}")
        print("사용자들이 이제 업데이트를 받을 수 있습니다.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 배포 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # 정리
        cleanup_files(zip_path)


if __name__ == "__main__":
    sys.exit(main())