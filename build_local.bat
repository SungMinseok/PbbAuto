@echo off
chcp 65001 >nul
REM ==========================================
REM PbbAuto 로컬 빌드 스크립트
REM ==========================================
echo.
echo ========================================
echo PbbAuto 로컬 빌드 스크립트
echo ========================================
echo.

REM PyInstaller 설치 확인
echo [1/4] 의존성 확인...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller가 설치되지 않았습니다. 설치 중...
    pip install pyinstaller
)

echo.
echo [2/4] 빌드 시작...
python build.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo 빌드 실패!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo [3/4] 빌드 결과 확인...
if exist "dist\PbbAuto.exe" (
    echo ✓ PbbAuto.exe 생성 완료
    echo   크기: 
    dir dist\PbbAuto.exe | find "PbbAuto.exe"
) else (
    echo ✗ PbbAuto.exe 생성 실패
    pause
    exit /b 1
)

if exist "dist\PbbAuto_v*_portable.zip" (
    echo ✓ 포터블 패키지 생성 완료
    dir dist\PbbAuto_v*_portable.zip
) else (
    echo ✗ 포터블 패키지 생성 실패
)

echo.
echo [4/4] 완료!
echo.
echo ========================================
echo 빌드 성공!
echo ========================================
echo.
echo 생성된 파일 위치:
echo   - dist\PbbAuto.exe
echo   - dist\PbbAuto_v*_portable.zip
echo.
echo 테스트 실행하시겠습니까? (Y/N)
set /p RUN_TEST=
if /i "%RUN_TEST%"=="Y" (
    echo.
    echo 실행 중...
    start dist\PbbAuto.exe
)

pause

