@echo off
chcp 65001 >nul
REM ==========================================
REM PbbAuto Fast Deploy Script (for Actions)
REM ==========================================
echo.
echo ========================================
echo PbbAuto Fast Deploy Script
echo ========================================
echo.

echo [1/5] Update version.json...
set /p CHANGELOG_MSG="Input changelog (Enter=Auto Deploy): "
if "%CHANGELOG_MSG%"=="" (
    set CHANGELOG_MSG=Auto Deploy
)

python update_version.py "%CHANGELOG_MSG%"

REM Read version from version.json
for /f "tokens=2 delims=:" %%V in ('python -c "import json; f=open('version.json','r',encoding='utf-8'); d=json.load(f); print('version:'+d['version']); f.close()"') do set VERSION=%%V

echo.
echo Version generated: %VERSION%
echo.

echo [2/5] Build project...
REM Insert your build command here (ex: python build.py)
python build.py

echo.
echo [3/5] Copy version.json to dist\
copy /Y version.json dist\

echo.
echo [4/5] Zip exe and version.json...
cd dist
tar -a -c -f BundleEditor_%VERSION%.zip "Bundle Editor.exe" version.json
cd ..

echo.
echo [5/5] All packaging done! Now push and let Actions release the zip.
echo ========================================
echo Zip path: dist\BundleEditor_%VERSION%.zip
echo ========================================
echo.
pause
