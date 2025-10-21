@echo off
chcp 65001 >nul
REM ==========================================
REM PbbAuto Local Build Deploy Script
REM ==========================================
echo.
echo ========================================
echo PbbAuto Local Build Deploy Script
echo ========================================
echo.

echo [0/6] Activate virtual environment...
echo.

set VENV1=C:\pyenvs\pbbauto\Scripts\activate.bat
call "%VENV1%"
echo.
echo [1/6] Update version.json...
echo.
set /p CHANGELOG_MSG="Input changelog (Enter=Auto Deploy): "
if "%CHANGELOG_MSG%"=="" (
    set CHANGELOG_MSG=Auto Deploy
)

REM Update version.json
python update_version.py "%CHANGELOG_MSG%"

REM Get version from version.json
for /f "tokens=2 delims=:" %%V in ('python -c "import json; f=open('version.json','r',encoding='utf-8'); d=json.load(f); print('version:'+d['version']); f.close()"') do set VERSION=%%V

echo.
echo Version generated: %VERSION%
echo.

echo.
echo [2/6] Local Build (EXE)...
python build.py
if errorlevel 1 (
    echo ❌ Build failed!
    pause
    exit /b 1
)

echo.
echo [3/6] Check local changes...
git status

echo.
echo [4/6] Commit changes...
set /p COMMIT_MSG="Commit message (Enter=Default): "
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=Local Build v%VERSION% - %CHANGELOG_MSG%
)

git add .
git commit -m "%COMMIT_MSG%"

echo.
echo [5/6] Push to main...
git push origin main

echo.
echo [6/6] Deploy to GitHub Releases...
echo ⚠️  GitHub Token이 필요합니다 (환경변수 GITHUB_TOKEN 또는 직접 입력)
python deploy_local.py

echo.
echo ========================================
echo ✅ Local Build Deploy Complete!
echo ========================================
echo GitHub: https://github.com/SungMinseok/PbbAuto/releases

pause
