@echo off
setlocal ENABLEDELAYEDEXPANSION

REM =====================================================
REM [1] 버전 구성 (형식: Release yyyy.MM.dd.HHmm)
REM =====================================================
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy.MM.dd.HHmm"') do set DATE_VER=%%i
set VERSION_STR=Release %DATE_VER%

REM version.txt 생성
echo %VERSION_STR% > version.txt
echo [INFO] Generated version.txt with version: %VERSION_STR%

REM =====================================================
REM [2] 가상환경 활성화
REM =====================================================
call C:\myvenv\bundleeditor\Scripts\activate.bat

REM =====================================================
REM [3] PyInstaller 빌드
REM =====================================================
echo [INFO] Building BundleEditor.exe using PyInstaller...
start /wait pyinstaller --upx-dir C:\upx-4.2.4-win64 -F -w -i ico.ico --name BundleEditor main.py

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b %errorlevel%
)

REM =====================================================
REM [4] 기존 zip 삭제
REM =====================================================
if exist BundleEditor.zip del BundleEditor.zip

REM =====================================================
REM [5] zip 생성
REM =====================================================
echo [INFO] Creating new BundleEditor.zip file...

powershell Compress-Archive -Path dist\BundleEditor.exe, config.json, version.txt, ico.ico, qss -DestinationPath BundleEditor.zip

echo [INFO] Done. Final version: %VERSION_STR%
pause