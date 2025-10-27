@echo off
chcp 65001 >nul
setlocal ENABLEDELAYEDEXPANSION

set PY311_PATH=C:\Python311\python.exe

if not exist "%PY311_PATH%" (
    echo [ERROR] Python 3.11 경로가 존재하지 않습니다: %PY311_PATH%
    pause
    exit /b
)

:: requirements.txt 선택
for /f "delims=" %%i in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $ofd = New-Object Windows.Forms.OpenFileDialog; $ofd.Filter = 'Text files (*.txt)|*.txt'; $ofd.Title = 'requirements.txt 파일 선택'; if ($ofd.ShowDialog() -eq 'OK') { $ofd.FileName }"') do set REQUIREMENTS_PATH=%%i

if "%REQUIREMENTS_PATH%"=="" (
    echo [ERROR] requirements.txt 파일이 선택되지 않았습니다.
    pause
    exit /b
)

:: 가상환경 설치 위치 폴더 선택
for /f "delims=" %%j in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $fbd = New-Object Windows.Forms.FolderBrowserDialog; $fbd.Description = '가상환경을 만들 폴더 선택'; if ($fbd.ShowDialog() -eq 'OK') { $fbd.SelectedPath }"') do set VENV_TARGET_DIR=%%j

if "%VENV_TARGET_DIR%"=="" (
    echo [ERROR] 폴더가 선택되지 않았습니다.
    pause
    exit /b
)

:: 가상환경 폴더명 사용자 입력
set /p VENV_NAME=[INPUT] 생성할 가상환경 폴더명을 입력하세요 (예: pbbauto): 

if "%VENV_NAME%"=="" (
    echo [ERROR] 폴더명이 입력되지 않았습니다.
    pause
    exit /b
)

set VENV_DIR=%VENV_TARGET_DIR%\%VENV_NAME%
echo [INFO] Creating virtual environment with Python 3.11 at: %VENV_DIR%
"%PY311_PATH%" -m venv "%VENV_DIR%"

echo [INFO] Upgrading pip, setuptools, wheel...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel

echo [INFO] Installing packages from: %REQUIREMENTS_PATH%
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS_PATH%"

echo [DONE] Python 3.11 (64bit) 가상환경 및 패키지 설치 완료!
pause
