# 🔧 PyInstaller 오류 해결 가이드

## 문제 상황
```
Exception: Qt plugin directory 'C:/Users/???/OneDrive/???????/pubg/PbbAuto/venv_py311/Lib/site-packages/PyQt5/Qt5/plugins' does not exist!
```

## 발생 원인
1. **한글 경로 문제**: Windows에서 한글이 포함된 경로가 PyInstaller에서 제대로 인식되지 않음
2. **PyQt5 플러그인 디렉토리 누락**: PyQt5 설치 시 플러그인 디렉토리가 제대로 생성되지 않음

## 해결 방법

### 방법 1: PyQt5 완전 재설치 (권장)
```batch
REM 1. 가상환경 활성화
call venv_py311\Scripts\activate.bat

REM 2. 기존 PyQt5 완전 제거
pip uninstall PyQt5 PyQt5-Qt5 PyQt5_sip -y

REM 3. 캐시 정리
pip cache purge

REM 4. PyQt5 재설치 (특정 버전으로 고정)
pip install PyQt5==5.15.9

REM 5. 설치 확인
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 OK')"
```

### 방법 2: PySide2로 대체
```batch
REM 1. PyQt5 제거
pip uninstall PyQt5 PyQt5-Qt5 PyQt5_sip -y

REM 2. PySide2 설치
pip install PySide2

REM 3. 코드에서 import 변경 필요
REM from PyQt5.QtWidgets import * → from PySide2.QtWidgets import *
```

### 방법 3: 영문 경로로 이동
1. 프로젝트를 한글이 없는 경로로 이동
   - 예: `C:\projects\PbbAuto\`
2. 가상환경을 새로 생성하여 빌드

### 방법 4: PyInstaller 옵션 수정
```python
# build.py에서 다음 추가
import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ['QT_PLUGIN_PATH'] = ''
```

## 현재 상태
- ✅ Python 3.11 가상환경 생성 완료
- ✅ PyInstaller 6.16.0 설치 완료  
- ❌ PyQt5 플러그인 디렉토리 문제 해결 필요

## 다음 단계
1. 위 방법 중 하나를 선택하여 실행
2. 빌드 재시도
3. 필요시 한글 경로 문제 해결을 위한 프로젝트 이동 고려

---
*※ 한글 경로 문제는 Windows 환경에서 Python 개발 시 자주 발생하는 문제입니다.*

