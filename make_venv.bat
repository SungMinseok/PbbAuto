@echo off
setlocal ENABLEDELAYEDEXPANSION

:: [0] Python 3.11 경로 지정 (64비트용)
set PY311_PATH=C:\Python311\python.exe

:: Python 3.11 존재 확인
if not exist "%PY311_PATH%" (
    echo [ERROR] Python 3.11 경로가 존재하지 않습니다: %PY311_PATH%
    pause
    exit /b
)

:: [1] requirements.txt 파일 선택
for /f "delims=" %%i in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $ofd = New-Object Windows.Forms.OpenFileDialog; $ofd.Filter = 'Text files (*.txt)|*.txt'; $ofd.Title = 'requirements.txt 파일 선택'; if ($ofd.ShowDialog() -eq 'OK') { $ofd.FileName }"') do set REQUIREMENTS_PATH=%%i

if "%REQUIREMENTS_PATH%"=="" (
    echo [ERROR] requirements.txt 파일이 선택되지 않았습니다.
    pause
    exit /b
)

:: [2] 가상환경을 생성할 폴더 선택
for /f "delims=" %%j in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $fbd = New-Object Windows.Forms.FolderBrowserDialog; $fbd.Description = '가상환경을 만들 폴더 선택'; if ($fbd.ShowDialog() -eq 'OK') { $fbd.SelectedPath }"') do set VENV_TARGET_DIR=%%j

if "%VENV_TARGET_DIR%"=="" (
    echo [ERROR] 폴더가 선택되지 않았습니다.
    pause
    exit /b
)

:: [3] 가상환경 생성 (Python 3.11 사용)
set VENV_DIR=%VENV_TARGET_DIR%\venv
echo [INFO] Creating virtual environment with Python 3.11 at: %VENV_DIR%
"%PY311_PATH%" -m venv "%VENV_DIR%"

:: [4] 가상환경 활성화
echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: [5] pip 최신화
echo [INFO] Upgrading pip, setuptools, wheel...
pip install --upgrade pip setuptools wheel

:: [6] 패키지 설치
echo [INFO] Installing packages from: %REQUIREMENTS_PATH%
pip install -r "%REQUIREMENTS_PATH%"

:: [7] 완료 메시지
echo [DONE] Python 3.11 (64bit) 가상환경 및 패키지 설치 완료!
pause