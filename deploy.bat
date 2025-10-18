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

REM ======= 커밋 메시지 자동 모음 기능 추가 =======
set "COMMIT_MSG="
set /p COMMIT_MSG="커밋 메시지 입력 (Enter=자동): "
if "%COMMIT_MSG%"=="" (
    REM 최근 태그명 추출
    for /f "delims=" %%i in ('git describe --tags --abbrev=0') do set LAST_TAG=%%i

    REM 최근 태그~HEAD까지 커밋 메시지 임시 파일로 저장
    git log %LAST_TAG%..HEAD --oneline > recent_commits.txt

    REM 커밋 메시지 본문 생성
    set "AUTO_COMMIT_MSG=v%VERSION% 배포 - %CHANGELOG_MSG%\n[변경내역]"
    for /f "delims=" %%L in (recent_commits.txt) do (
        set "LINE=%%L"
        set "AUTO_COMMIT_MSG=!AUTO_COMMIT_MSG!\n- !LINE!"
    )

    REM 임시 파일 저장
    echo !AUTO_COMMIT_MSG! > commit_message.txt

    git add .
    git commit -F commit_message.txt
) else (
    git add .
    git commit -m "%COMMIT_MSG%"
)

REM 커밋 메시지 임시파일 삭제
if exist recent_commits.txt del recent_commits.txt
if exist commit_message.txt del commit_message.txt

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
