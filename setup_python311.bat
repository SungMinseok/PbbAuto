@echo off
chcp 65001 >nul
REM ==========================================
REM Python 3.11 환경 설정 스크립트
REM ==========================================
echo.
echo ========================================
echo Python 3.11 환경 설정
echo ========================================
echo.

echo [1/4] Python 3.11 가상환경 생성...
py -3.11-32 -m venv venv_py311

echo.
echo [2/4] 가상환경 활성화...
call venv_py311\Scripts\activate.bat

echo.
echo [3/4] pip 업그레이드...
python -m pip install --upgrade pip

echo.
echo [4/4] 패키지 설치...
pip install -r requirements.txt

echo.
echo ========================================
echo ✅ Python 3.11 환경 설정 완료!
echo ========================================
echo.
echo 사용법:
echo 1. venv_py311\Scripts\activate.bat  (가상환경 활성화)
echo 2. python build.py                  (빌드 실행)
echo 3. deactivate                       (가상환경 비활성화)
echo.
pause

