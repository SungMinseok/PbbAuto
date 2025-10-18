@echo off
chcp 65001 >nul
REM ==========================================
REM PbbAuto 빠른 배포 스크립트
REM ==========================================
echo.
echo ========================================
echo PbbAuto 빠른 배포 스크립트
echo ========================================
echo.

echo [1/7] version.json 자동 업데이트...
echo.
set /p CHANGELOG_MSG="변경사항 입력 (Enter=자동 배포): "
if "%CHANGELOG_MSG%"=="" (
    set CHANGELOG_MSG=자동 배포
)

REM Python으로 version.json 업데이트
python update_version.py "%CHANGELOG_MSG%"

REM 업데이트된 버전 읽기
for /f "tokens=2 delims=:" %%V in ('python -c "import json; f=open('version.json','r',encoding='utf-8'); d=json.load(f); print('version:'+d['version']); f.close()"') do set VERSION=%%V

echo.
echo 생성된 버전: %VERSION%
echo.

echo.
echo [2/7] 로컬 변경사항 확인...
git status

echo.
echo [3/7] 변경사항 커밋...
set /p COMMIT_MSG="커밋 메시지 입력 (Enter=기본): "
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=v%VERSION% 배포 - %CHANGELOG_MSG%
)

git add .
git commit -m "%COMMIT_MSG%"

echo.
echo [4/7] 메인 브랜치에 푸시...
git push origin main

echo.
echo [5/7] 태그 생성 (v%VERSION%)...
git tag -a v%VERSION% -m "Release v%VERSION%"

echo.
echo [6/7] 태그 푸시 (자동 빌드 트리거)...
git push origin v%VERSION%

echo.
echo [7/7] 완료!
echo.
echo ========================================
echo GitHub Actions에서 자동 빌드 중...
echo ========================================
echo.
echo 다음 링크에서 빌드 진행상황 확인:
echo https://github.com/SungMinseok/PbbAuto/actions
echo.
echo 빌드 완료 후 릴리스 페이지:
echo https://github.com/SungMinseok/PbbAuto/releases
echo.
pause

