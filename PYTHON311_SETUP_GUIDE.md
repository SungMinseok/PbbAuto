# 🐍 Python 3.11 환경 설정 가이드

Python 3.13에서 빌드 오류가 발생하므로 Python 3.11로 전환합니다.

## 📋 단계별 설정 방법

### 1. Python 3.11 가상환경 생성
**명령 프롬프트(CMD)에서 실행:**
```cmd
py -3.11-32 -m venv venv_py311
```

### 2. 가상환경 활성화
```cmd
venv_py311\Scripts\activate
```

### 3. Python 버전 확인
```cmd
python --version
```
> **예상 결과**: `Python 3.11.x`

### 4. pip 업그레이드
```cmd
python -m pip install --upgrade pip
```

### 5. 패키지 설치
```cmd
pip install -r requirements.txt
```

### 6. 빌드 테스트
```cmd
python build.py
```

## 🚀 빌드 성공 후 다음 단계

### 옵션 1: 로컬 배포 스크립트 사용
```cmd
python deploy_local.py
```

### 옵션 2: 기존 deploy.bat 사용
```cmd
deploy.bat
```

## ⚠️ 문제 해결

### Python 3.11이 설치되지 않은 경우
1. [Python 공식 사이트](https://www.python.org/downloads/)에서 Python 3.11.x 다운로드
2. 설치 시 "Add Python to PATH" 체크
3. 설치 완료 후 위 단계 반복

### 가상환경 활성화 확인
- 프롬프트 앞에 `(venv_py311)`이 표시되어야 함
- 예: `(venv_py311) C:\Users\...\PbbAuto>`

### PyInstaller 호환성 확인
```cmd
pip show pyinstaller
```
> **결과**: 버전 6.16.0 이상이어야 함

## 🔄 가상환경 종료/재활성화

### 종료
```cmd
deactivate
```

### 재활성화 (다음에 사용할 때)
```cmd
venv_py311\Scripts\activate
```

## 📊 Python 버전별 호환성

| Python 버전 | PyInstaller | 빌드 상태 |
|-------------|-------------|-----------|
| **3.11** | ✅ 호환 | ✅ 권장 |
| 3.13 | ❌ 문제 | ❌ 피해야 함 |
| 3.9 | ✅ 호환 | ⚠️ 구버전 |

## 🎯 완료 확인

빌드가 성공하면 다음과 같이 표시됩니다:
```
[DONE] Build successful! EXE located in: dist/BundleEditor.exe
```

성공하면 `dist/BundleEditor.exe` 파일이 생성됩니다!

