@echo off
chcp 65001 >nul
REM ==========================================
REM PbbAuto Fast Deploy Script (No ZIP creation)
REM ==========================================
echo.
echo ========================================
echo PbbAuto Fast Deploy Script
echo ========================================
echo.

echo [1/7] Update version.json...
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
echo [2/7] Check local changes...
git status

echo.
echo [3/7] Commit changes...
set /p COMMIT_MSG="Commit message (Enter=Default): "
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=v%VERSION% Release - %CHANGELOG_MSG%
)

git add .
git commit -m "%COMMIT_MSG%"

echo.
echo [4/7] Push to main...
git push origin main

echo.
echo [5/7] Create tag (v%VERSION%)...
git tag -a v%VERSION% -m "Release v%VERSION%"

echo.
echo [6/7] Push tag (Triggers GitHub Actions)...
git push origin v%VERSION%

echo.
echo [7/7] Done! Check build progress in Actions.
echo ========================================
echo https://github.com/SungMinseok/PbbAuto/actions
echo ========================================
start https://github.com/SungMinseok/PbbAuto/actions/workflows/build-and-release.yml

pause
