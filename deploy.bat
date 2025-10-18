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

REM 현재 시간 기반 버전 자동 생성 (1.0.yymmdd.hhmm 형식)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set YEAR=%datetime:~2,2%
set MONTH=%datetime:~4,2%
set DAY=%datetime:~6,2%
set HOUR=%datetime:~8,2%
set MINUTE=%datetime:~10,2%
set VERSION=1.0.%YEAR%%MONTH%%DAY%.%HOUR%%MINUTE%

echo 자동 생성된 버전: %VERSION%
echo.

echo.
echo [1/6] 로컬 변경사항 확인...
git status

echo.
echo [2/6] 변경사항 커밋...
set /p COMMIT_MSG="커밋 메시지 입력: "
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=v%VERSION% 배포
)

git add .
git commit -m "%COMMIT_MSG%"

echo.
echo [3/6] 메인 브랜치에 푸시...
git push origin main

echo.
echo [4/6] 태그 생성 (v%VERSION%)...
git tag -a v%VERSION% -m "Release v%VERSION%"

echo.
echo [5/6] 태그 푸시 (자동 빌드 트리거)...
git push origin v%VERSION%

echo.
echo [6/6] 완료!
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

