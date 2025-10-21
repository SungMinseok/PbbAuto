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
    zip_filename = f"BundleEditor_{version}.zip"
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

def load_token_data():
    """token.json 로드"""
    token_path = Path("token.json")
    if not token_path.exists():
        print("❌ token.json 파일이 없습니다.")
        return None
    try:
        with open(token_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ token.json 읽기 실패: {e}")
        return None

def get_github_token():
    """GitHub 토큰 가져오기 (token.json에서 읽기)"""
    token_data = load_token_data()
    if token_data and "github_token" in token_data:
        print("✅ token.json에서 GitHub 토큰을 불러왔습니다.")
        return token_data["github_token"]
    
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        print("⚙️  환경변수 GITHUB_TOKEN에서 토큰을 불러왔습니다.")
        return token
    
    print("❌ GitHub 토큰을 찾을 수 없습니다.")
    return None



def create_github_release(version, changelog, token, zip_path):
    """GitHub 릴리즈 생성 및 파일 업로드"""
    print(f"\n[2/4] GitHub 릴리즈 생성 중... ({version})")
    
    repo_owner = "SungMinseok"
    repo_name = "BundleEditor"
    tag_name = f"{version}"
    
    # 릴리즈 데이터
    release_data = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Release {version}",
        "body": f"## 변경사항\n- {changelog}\n\n **자체 업데이트 가능 버전**",
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
        
def send_slack_notification(version, changelog, webhooks):
    """Slack Webhook으로 릴리즈 알림 전송"""
    message = {
        "text": f":rocket: *BundleEditor {version}* 업데이트\n"
                f"• 앱 다운로드 경로: //\n"
                #업데이트 방법 
                f"• 업데이트 방법: 앱 재실행 또는 Help-업데이트 확인 버튼 클릭\n"
                f"• 변경사항: {changelog}\n"
                #f"• 릴리즈 링크: https://github.com/SungMinseok/BundleEditor/releases/tag/{version}"
    }

    for name, url in webhooks.items():
        if not url.startswith("https://hooks.slack.com/services/"):
            continue
        try:
            response = requests.post(url, json=message)
            if response.status_code == 200:
                print(f"✅ Slack 알림 전송 성공 ({name})")
            else:
                print(f"⚠️ Slack 알림 실패 ({name}): {response.status_code}")
        except Exception as e:
            print(f"⚠️ Slack 알림 중 오류 ({name}): {e}")

def choose_webhook(webhooks: dict) -> str:
    keys = list(webhooks.keys())
    print("\n🔔 사용할 Slack Webhook을 선택하세요:")
    for i, k in enumerate(keys, 1):
        print(f"{i}. {k}")

    while True:
        try:
            choice = int(input("번호 입력 (취소하려면 0): ").strip())
            if choice == 0:
                print("Slack 알림 전송 취소됨.")
                return None
            elif 1 <= choice <= len(keys):
                selected_key = keys[choice - 1]
                print(f"✅ 선택된 Webhook: {selected_key}")
                return webhooks[selected_key]
            else:
                print("⚠️ 잘못된 번호입니다. 다시 입력하세요.")
        except ValueError:
            print("⚠️ 숫자를 입력해주세요.")

def main():
    print("=" * 60)
    print("BundleEditor 로컬 빌드 배포 스크립트")
    print("=" * 60)
    
    version_info = load_version_info()
    if not version_info:
        return 1

    version = version_info.get("version")
    changelog = version_info.get("changelog", [{}])[0].get("changes", ["자동 배포"])[0]

    print(f"버전: {version}")
    print(f"변경사항: {changelog}")

    zip_path = Path("dist/BundleEditor.zip")
    if not zip_path.exists():
        print("\n❌ dist/BundleEditor.zip 파일이 존재하지 않습니다!")
        return 1

    print(f"\n🚀 {version} 릴리즈를 GitHub에 배포하시겠습니까?")
    response = input("계속하려면 'y'를 입력하세요: ").lower().strip()
    if response != 'y':
        print("배포 취소됨")
        return 0

    token = get_github_token()
    if not token:
        return 1

    token_data = load_token_data()
    webhooks = {k: v for k, v in (token_data or {}).items() if k.startswith("webhook_")}

    try:
        if not create_github_release(version, changelog, token, zip_path):
            return 1

        print("\n" + "=" * 60)
        print("✅ GitHub 릴리즈 완료!")
        print("=" * 60)
        print(f"릴리즈 URL: https://github.com/SungMinseok/BundleEditor/releases/tag/{version}")

        # 🔔 Slack 알림 전송
        if webhooks:
            webhook_url = choose_webhook(webhooks)
            if webhook_url:
                send_slack_notification(version, changelog, webhook_url)
        else:
            print("⚠️ token.json에 Slack Webhook 정보가 없습니다.")

        return 0

    except Exception as e:
        print(f"\n❌ 배포 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        cleanup_files(zip_path)


if __name__ == "__main__":
    sys.exit(main())