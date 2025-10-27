# 로컬 빌드 및 GitHub 배포 자동화 가이드

이 문서는 Python 프로젝트를 로컬에서 빌드하고 GitHub Release로 배포하는 시스템 구축 방법을 설명합니다.

**배포 방식**: 로컬 빌드 후 수동 배포 (GitHub Actions 미사용)

## 목차
1. [전체 구조 개요](#전체-구조-개요)
2. [버전 관리 시스템](#버전-관리-시스템)
3. [로컬 빌드 설정](#로컬-빌드-설정)
4. [GitHub Release 배포](#github-release-배포)
5. [배포 워크플로우](#배포-워크플로우)
6. [파일 구조 및 설명](#파일-구조-및-설명)
7. [(선택) GitHub Actions 자동 배포](#선택-github-actions-자동-배포)

---

## 전체 구조 개요

```
프로젝트/
├── version.json           # 버전 정보 및 changelog
├── update_version.py      # 버전 자동 업데이트 스크립트
├── build.py              # PyInstaller 빌드 스크립트
├── deploy_local.py       # 로컬 빌드 후 GitHub 배포
├── changelog.txt         # 릴리즈 노트 작성용 임시 파일
├── token.json            # GitHub Token 및 Webhook URL (gitignore 필수)
└── dist/
    └── BundleEditor.zip  # 빌드된 실행 파일 패키지
```

**배포 흐름**:
1. 로컬에서 `build.py` 실행 → EXE 빌드 및 ZIP 생성
2. `deploy_local.py` 실행 → GitHub Release 생성 및 ZIP 업로드
3. 사용자는 앱 내 자동 업데이트 기능으로 새 버전 다운로드

---

## 버전 관리 시스템

### 버전 형식
**형식**: `1.0-YY.MM.DD.HHMM`

- **메이저.마이너**: `1.0` (고정)
- **날짜/시간**: 빌드 시점의 연/월/일/시분
- **예시**: `1.0-25.10.26.1430` (2025년 10월 26일 14시 30분)

### version.json 구조

```json
{
  "version": "1.0-25.10.26.1430",
  "build_date": "2025-10-26",
  "update_url": "https://api.github.com/repos/{owner}/{repo}/releases/latest",
  "changelog": [
    {
      "version": "1.0-25.10.26.1430",
      "date": "2025-10-26",
      "changes": [
        "새 기능 추가",
        "버그 수정"
      ]
    }
  ]
}
```

### update_version.py

버전을 자동으로 업데이트하는 스크립트입니다.

```python
"""
버전 자동 업데이트 스크립트
현재 시간 기반으로 version.json을 업데이트합니다.
"""

import json
from datetime import datetime
import sys


def update_version(changelog_message=None):
    """version.json을 현재 시간 기반으로 업데이트"""
    
    # 현재 시간 기반 버전 생성 (1.0-YY.MM.DD.HHMM)
    now = datetime.now()
    new_version = now.strftime("1.0-%y.%m.%d.%H%M")
    build_date = now.strftime("%Y-%m-%d")
    
    print(f"새 버전: {new_version}")
    print(f"빌드 날짜: {build_date}")
    
    try:
        # 기존 version.json 읽기
        with open('version.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        old_version = data.get('version', 'unknown')
        print(f"이전 버전: {old_version}")
        
        # 버전 업데이트
        data['version'] = new_version
        data['build_date'] = build_date
        
        # 변경사항 메시지가 있으면 changelog에 추가
        if changelog_message:
            new_changelog = {
                "version": new_version,
                "date": build_date,
                "changes": [changelog_message]
            }
            
            # 기존 changelog 앞에 추가
            if 'changelog' not in data:
                data['changelog'] = []
            data['changelog'].insert(0, new_changelog)
            
            print(f"변경사항 추가: {changelog_message}")
        
        # 파일 저장
        with open('version.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("\n✅ version.json 업데이트 완료!")
        print(f"   버전: {new_version}")
        print(f"   날짜: {build_date}")
        
        return new_version
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # 커맨드라인 인자로 변경사항 메시지 받기
    changelog_msg = None
    if len(sys.argv) > 1:
        changelog_msg = ' '.join(sys.argv[1:])
    
    version = update_version(changelog_msg)
    print(f"\n태그 생성 명령어:")
    print(f"  git tag -a v{version} -m \"Release v{version}\"")
    print(f"  git push origin v{version}")
```

**사용법**:
```bash
# 버전만 업데이트
python update_version.py

# 변경사항과 함께 업데이트
python update_version.py "새 기능 추가 및 버그 수정"
```

---

## 로컬 빌드 설정

### build.py - PyInstaller 빌드 스크립트

이 스크립트는 Python 애플리케이션을 실행 파일로 패키징합니다.

**주요 기능**:
1. Windows 버전 정보 파일 생성
2. PyInstaller spec 파일 동적 생성
3. EXE 빌드 및 ZIP 패키징
4. 임시 파일 정리

**버전 형식 처리**:

```python
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
        # 레거시 형식 처리 (하위 호환성)
        version_parts = version.split('.')
        # ... 기존 로직 ...
```

**사용법**:
```bash
python build.py
```

**생성되는 파일**:
- `dist/BundleEditor.exe` (빌드 후 자동 삭제)
- `dist/BundleEditor.zip` (최종 배포 파일)

---

## GitHub Release 배포

### deploy_local.py - 로컬에서 GitHub Release 생성

이 스크립트는 로컬에서 빌드된 파일을 GitHub Release로 업로드합니다.

**주요 기능**:
1. `dist/BundleEditor.zip` 확인
2. `changelog.txt` 파일로 릴리즈 노트 작성
3. GitHub API를 통해 Release 생성
4. ZIP 파일 업로드
5. Slack Webhook 알림 (선택)

**사용 이유**: 
- Windows Defender 오탐 문제 방지 (로컬 빌드가 더 안전)
- 빌드 환경 통제 (로컬 Python 환경 사용)
- 릴리즈 노트 작성의 유연성

**핵심 코드**:

```python
def create_github_release(version, changelog, token, zip_path):
    """GitHub 릴리즈 생성 및 파일 업로드"""
    repo_owner = "SungMinseok"  # GitHub 사용자명
    repo_name = "PbbAuto"       # 저장소 이름
    tag_name = f"{version}"
    
    # 1. changelog.txt 파일 열기 및 사용자 편집 대기
    os.startfile("changelog.txt")
    input("👉 changelog.txt 편집 완료 후 엔터를 누르세요...")
    
    # 2. 파일 내용 읽기
    with open("changelog.txt", 'r', encoding='utf-8') as f:
        changelog_content = f.read().strip()
    
    # 3. Release 데이터 구성
    release_data = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Release {version}",
        "body": f"## 변경사항\n\n{changelog_content}\n\n**자체 업데이트 가능 버전**",
        "draft": False,
        "prerelease": False
    }
    
    # 4. GitHub API로 Release 생성
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
    response = requests.post(url, json=release_data, headers=headers)
    
    # 5. ZIP 파일 업로드
    upload_url = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/releases/{release_id}/assets"
    # ... 파일 업로드 로직 ...
```

**사용법**:
```bash
python deploy_local.py
```

**실행 흐름**:
1. `dist/BundleEditor.zip` 존재 여부 확인
2. 버전 정보 출력 및 확인 요청 (`y` 입력)
3. `changelog.txt` 파일이 자동으로 열림
4. 사용자가 릴리즈 노트 작성 후 저장
5. 콘솔로 돌아와 엔터 입력
6. GitHub Release 생성 및 ZIP 업로드
7. Slack 알림 선택 (선택사항)

---

## 배포 워크플로우

### 전체 배포 프로세스

```bash
# 1. 버전 업데이트
python update_version.py "변경사항 메시지"
# 출력 예시: 새 버전: 1.0-25.10.26.1430

# 2. 로컬 빌드
python build.py
# 결과: dist/BundleEditor.zip 생성

# 3. 변경사항 커밋 및 푸시
git add .
git commit -m "버전 업데이트: 1.0-25.10.26.1430"
git push

# 4. GitHub Release 배포
python deploy_local.py
# - changelog.txt 편집
# - GitHub Release 생성
# - ZIP 파일 업로드
# - Slack 알림 (선택)
```

### 상세 단계별 설명

#### Step 1: 버전 업데이트
```bash
python update_version.py "새 기능 추가 및 버그 수정"
```
- `version.json` 파일이 자동 업데이트됨
- 새 버전: `1.0-25.10.26.1430` (현재 시간 기반)
- changelog에 변경사항 추가

#### Step 2: 로컬 빌드
```bash
python build.py
```
실행 과정:
1. `version_info.txt` 생성 (Windows 버전 정보)
2. `PbbAuto.spec` 파일 생성 (PyInstaller 설정)
3. PyInstaller로 EXE 빌드
4. `dist/BundleEditor.zip` 생성 (EXE + version.json)
5. 임시 파일 정리 (build 폴더, EXE 파일 삭제)

#### Step 3: Git 커밋 및 푸시
```bash
git add .
git commit -m "버전 업데이트: 1.0-25.10.26.1430"
git push
```
- 변경된 파일들을 원격 저장소에 반영

#### Step 4: GitHub Release 배포
```bash
python deploy_local.py
```
실행 과정:
1. `dist/BundleEditor.zip` 존재 확인
2. 배포 확인 프롬프트 (`y` 입력)
3. `changelog.txt` 파일이 자동으로 열림
4. 릴리즈 노트 작성 후 저장
5. 콘솔로 돌아와 엔터 입력
6. GitHub Release 생성
7. ZIP 파일 업로드
8. Slack 알림 선택 (있는 경우)

**changelog.txt 예시**:
```
* [2025-10-26] 새 기능: 사용자 인증 시스템 추가
* [2025-10-26] 개선: UI 반응속도 30% 향상
* [2025-10-26] 버그 수정: 파일 저장 시 인코딩 오류 해결
* [2025-10-26] 버그 수정: 메모리 누수 문제 해결
```

---

## 파일 구조 및 설명

### 1. version.json
- 현재 버전 정보 및 변경 이력 저장
- 애플리케이션 내 자동 업데이트 시스템에서 참조
- **필수 필드**: `version`, `build_date`, `update_url`, `changelog`

### 2. update_version.py
- 버전 번호를 현재 시간 기반으로 자동 생성
- changelog 항목 추가
- **커맨드라인 인자**: 변경사항 메시지 (선택사항)

### 3. build.py
- PyInstaller를 사용한 EXE 빌드
- Windows 버전 정보 임베딩
- ZIP 패키지 생성 및 정리
- **출력**: `dist/BundleEditor.zip`

### 4. deploy_local.py
- 로컬 빌드 후 GitHub Release 생성
- changelog.txt 파일로 릴리즈 노트 작성
- Slack Webhook 알림 지원
- **필수**: `token.json` (GitHub Token 포함)

### 5. changelog.txt
- 릴리즈 노트 작성용 임시 파일
- `deploy_local.py` 실행 시 자동으로 열림
- 사용자가 변경사항을 직접 작성
- GitHub Release의 본문(body)으로 사용됨

### 6. token.json (gitignore 필수!)
```json
{
  "github_token": "ghp_xxxxxxxxxxxxxxxxxxxx",
  "webhook_qa": "https://hooks.slack.com/services/...",
  "webhook_dev": "https://hooks.slack.com/services/..."
}
```

**GitHub Token 생성 방법**:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" 클릭
3. 권한 선택: `repo` (전체) 체크
4. 생성된 토큰을 `token.json`에 저장

---

## 주요 기능 설명

### 1. 버전 형식 변환 로직

**표시용**: `1.0-25.10.26.1430`  
**Windows 파일 버전**: `1,0,251026,1430`

Windows 버전 정보는 각 부분이 0-65535 범위여야 하므로:
- Major: `1`
- Minor: `0`
- Build: `251026` (yymmdd)
- Revision: `1430` (hhmm)

### 2. 로컬 빌드 방식의 장점

- **Windows Defender 오탐 방지**: GitHub Actions 빌드보다 로컬 빌드가 바이러스 오탐률이 낮음
- **빌드 환경 통제**: 로컬 Python 환경을 직접 관리
- **빠른 디버깅**: 빌드 오류 시 즉시 수정 가능
- **릴리즈 노트 유연성**: `changelog.txt`로 상세한 릴리즈 노트 작성 가능

### 3. 배포 후 알림

`deploy_local.py`는 Slack Webhook을 통해 배포 알림을 전송합니다:
```python
def send_slack_notification(version, changelog, webhook_url):
    """Slack Webhook으로 릴리즈 알림 전송"""
    message = {
        "text": f":rocket: *BundleEditor {version}* 업데이트\n"
                f"• 업데이트 방법: 앱 재실행 또는 Help-업데이트 확인 버튼 클릭\n"
                f"• 변경사항: {changelog}\n"
    }
    # ... Webhook POST 로직 ...
```

---

## 문제 해결

### 1. dist/BundleEditor.zip 파일이 없음
**증상**: `deploy_local.py` 실행 시 "파일이 존재하지 않습니다" 오류
```bash
❌ dist/BundleEditor.zip 파일이 존재하지 않습니다!
```

**해결**:
```bash
python build.py  # 먼저 빌드 실행
python deploy_local.py  # 그 다음 배포
```

### 2. GitHub Token 오류
**증상**: 
```bash
❌ GitHub 토큰을 찾을 수 없습니다.
```

**해결**:
1. `token.json` 파일 존재 확인
2. GitHub Token 형식 확인 (`ghp_`로 시작)
3. Token 권한 확인 (repo 권한 필요)

### 3. 릴리즈 생성 실패 (409 Conflict)
**증상**: 
```bash
❌ 릴리즈 생성 실패: 409
```

**원인**: 동일한 버전의 Release가 이미 존재

**해결**:
```bash
# GitHub에서 기존 Release 삭제 또는
# 새 버전으로 업데이트
python update_version.py "재배포"
python build.py
python deploy_local.py
```

### 4. 빌드 실패
**증상**: `build.py` 실행 시 오류 발생

**체크리스트**:
1. Python 3.11 설치 확인: `python --version`
2. 의존성 설치: `pip install -r requirements.txt`
3. PyInstaller 설치: `pip install pyinstaller`
4. `version.json` 파일 존재 확인

### 5. changelog.txt 파일이 열리지 않음
**증상**: `deploy_local.py` 실행 시 파일이 열리지 않음

**해결**:
1. 수동으로 `changelog.txt` 파일 생성 및 편집
2. 또는 코드 수정:
```python
# deploy_local.py에서
os.startfile("changelog.txt")
# 위 줄을 주석 처리하고 직접 에디터로 열기
```

---

## 체크리스트

### 초기 설정 (최초 1회)
- [ ] Python 3.11 설치 확인
- [ ] `requirements.txt` 확인 및 의존성 설치
  ```bash
  pip install -r requirements.txt
  pip install pyinstaller
  ```
- [ ] `version.json` 생성 및 초기 버전 설정
  ```json
  {
    "version": "1.0-25.01.01.0000",
    "build_date": "2025-01-01",
    "update_url": "https://api.github.com/repos/{owner}/{repo}/releases/latest",
    "changelog": []
  }
  ```
- [ ] `token.json` 생성 및 GitHub Token 추가
  ```json
  {
    "github_token": "ghp_xxxxxxxxxxxxxxxxxxxx"
  }
  ```
- [ ] `.gitignore`에 `token.json` 추가
- [ ] PyInstaller spec 파일 확인 (`PbbAuto.spec`)

### 매 배포 시 (반복)
- [ ] 1. 코드 변경사항 완료 및 테스트
- [ ] 2. 버전 업데이트
  ```bash
  python update_version.py "변경사항 메시지"
  ```
- [ ] 3. 로컬 빌드
  ```bash
  python build.py
  ```
- [ ] 4. 빌드 결과 확인 (`dist/BundleEditor.zip` 존재)
- [ ] 5. Git 커밋 및 푸시
  ```bash
  git add .
  git commit -m "버전 업데이트: 1.0-25.10.26.1430"
  git push
  ```
- [ ] 6. GitHub Release 배포
  ```bash
  python deploy_local.py
  ```
- [ ] 7. `changelog.txt` 편집 (릴리즈 노트 작성)
- [ ] 8. 콘솔에서 엔터 입력하여 배포 진행
- [ ] 9. Slack 알림 전송 (선택사항)
- [ ] 10. GitHub Release 페이지에서 배포 확인
  ```
  https://github.com/{owner}/{repo}/releases
  ```

---

## (선택) GitHub Actions 자동 배포

현재는 로컬 빌드 방식을 사용하지만, 향후 GitHub Actions를 사용하고 싶다면 아래 내용을 참고하세요.

### .github/workflows/build-and-release.yml

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*' # v1.0-25.10.26.1430 형식의 태그

permissions:
  contents: write

jobs:
  build:
    runs-on: windows-latest
    timeout-minutes: 30

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build
      run: python build.py
    
    - name: Create Release
      uses: softprops/action-gh-release@v2
      with:
        files: dist/BundleEditor.zip
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitHub Actions 사용 시 워크플로우

```bash
# 1. 버전 업데이트
python update_version.py "변경사항"

# 2. 커밋 및 태그
git add .
git commit -m "버전 업데이트"
git tag -a v1.0-25.10.26.1430 -m "Release"

# 3. 태그 푸시 (자동 빌드 트리거)
git push origin v1.0-25.10.26.1430
```

**장점**:
- 자동 빌드 및 배포
- 로컬 환경 불필요

**단점**:
- Windows Defender 오탐 가능성 높음
- 빌드 시간 더 소요
- 빌드 환경 통제 어려움

---

## 참고 자료

### GitHub API
- [GitHub REST API - Releases](https://docs.github.com/en/rest/releases/releases)
- [Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

### PyInstaller
- [PyInstaller 공식 문서](https://pyinstaller.org/)
- [Version Information (Windows)](https://pyinstaller.org/en/stable/usage.html#capturing-windows-version-data)

### 버전 관리
- [Semantic Versioning](https://semver.org/)
- [Calendar Versioning (CalVer)](https://calver.org/)

### Python Requests
- [Requests 라이브러리](https://requests.readthedocs.io/)

---

## 다른 프로젝트에 적용하기

이 가이드를 다른 프로젝트에 적용할 때 수정해야 할 부분:

### 1. 저장소 정보 (deploy_local.py)
```python
repo_owner = "SungMinseok"  # → 본인의 GitHub 사용자명
repo_name = "PbbAuto"       # → 저장소 이름
```

### 2. 실행 파일 이름 (build.py, deploy_local.py)
```python
# build.py
exe_file = dist_dir / "BundleEditor.exe"  # → 본인의 앱 이름
zip_filename = f"BundleEditor_{version}.zip"

# deploy_local.py
exe_path = 'dist/BundleEditor.exe'
```

### 3. 버전 형식 (선택사항)
```python
# update_version.py
new_version = now.strftime("1.0-%y.%m.%d.%H%M")  # 원하는 형식으로 변경
```

### 4. update_url (version.json)
```json
{
  "update_url": "https://api.github.com/repos/{owner}/{repo}/releases/latest"
}
```

---

## FAQ

**Q: 매번 빌드해야 하나요?**  
A: 네, 코드 변경 시마다 빌드가 필요합니다. `build.py`로 빌드하고 `deploy_local.py`로 배포합니다.

**Q: 버전을 수동으로 관리할 수 있나요?**  
A: 가능합니다. `version.json` 파일을 직접 수정하면 됩니다. 하지만 `update_version.py`를 사용하면 자동으로 시간 기반 버전이 생성되어 편리합니다.

**Q: GitHub Actions를 꼭 사용해야 하나요?**  
A: 아니요. 이 프로젝트는 로컬 빌드 방식을 사용합니다. GitHub Actions는 선택사항입니다.

**Q: Slack 알림이 필수인가요?**  
A: 아니요. `token.json`에 Webhook URL이 없으면 알림을 건너뜁니다.

**Q: changelog.txt는 매번 작성해야 하나요?**  
A: 네, `deploy_local.py` 실행 시 릴리즈 노트를 작성해야 합니다. 이전 내용을 복사해서 수정하면 편리합니다.

---

## 라이센스

이 가이드는 자유롭게 사용 및 수정 가능합니다.

---

**작성일**: 2025-10-26  
**버전**: 1.1  
**배포 방식**: 로컬 빌드 + 수동 배포

