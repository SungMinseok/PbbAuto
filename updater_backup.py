"""
자동 업데이트 시스템
GitHub Releases를 통한 버전 체크 및 업데이트
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import json
import os
import sys
import requests
import tempfile
import subprocess
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from packaging import version
import threading


class UpdateChecker:
    """버전 체크 및 업데이트 확인 클래스"""
    
    def __init__(self, version_file: str = "version.json"):
        self.version_file = version_file
        self.current_version = self._load_current_version()
        self.latest_info = None
        self.main_app = None  # main app 참조
    
    def set_main_app(self, main_app):
        """main app 참조 설정"""
        self.main_app = main_app
    
    def _log(self, message):
        """로그 메시지 출력 (main app이 있으면 사용, 없으면 print)"""
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)
    
    def _log_error(self, message):
        """에러 로그 메시지 출력 (main app이 있으면 사용, 없으면 print)"""
        if self.main_app and hasattr(self.main_app, 'log_error'):
            self.main_app.log_error(message)
        else:
            print(message)
        
    def _load_current_version(self) -> str:
        """현재 버전 정보 로드"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
        except Exception as e:
            self._log_error(f"버전 파일 로드 실패: {e}")
        return '0.0.0'
    
    def check_for_updates(self, update_url: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        업데이트 확인
        
        Args:
            update_url: GitHub Releases API URL (None이면 version.json에서 로드)
            
        Returns:
            (업데이트 가능 여부, 최신 버전 정보, 에러 메시지)
        """
        try:
            self._log("[DEBUG] UpdateChecker.check_for_updates 시작")
            # update_url이 없으면 version.json에서 가져오기
            if not update_url:
                update_url = self._get_update_url()
                self._log(f"[DEBUG] version.json에서 로드한 URL: {update_url}")
            
            if not update_url:
                error_msg = "업데이트 URL이 설정되지 않았습니다."
                self._log_error(error_msg)
                return False, None, error_msg
            
            self._log(f"업데이트 확인 중... (현재 버전: {self.current_version})")
            self._log(f"[DEBUG] GitHub API 호출: {update_url}")
            
            # GitHub API 호출
            response = requests.get(update_url, timeout=10)
            response.raise_for_status()
            self._log("[DEBUG] GitHub API 응답 수신 성공")
            
            release_info = response.json()
            
            # 최신 버전 정보 파싱
            latest_version = release_info['tag_name'].lstrip('v')
            
            self.latest_info = {
                'version': latest_version,
                'name': release_info.get('name', f'버전 {latest_version}'),
                'body': release_info.get('body', '변경사항이 없습니다.'),
                'published_at': release_info.get('published_at', ''),
                'assets': release_info.get('assets', [])
            }
            
            # 버전 비교
            self._log(f"[DEBUG] 버전 비교 - 현재: {self.current_version}, 최신: {latest_version}")
            if version.parse(latest_version) > version.parse(self.current_version):
                self._log(f"새로운 버전 발견: {latest_version}")
                self._log(f"[DEBUG] 반환 값: True, info, None")
                return True, self.latest_info, None
            else:
                self._log("최신 버전을 사용 중입니다.")
                self._log("[DEBUG] 반환 값: False, None, None")
                return False, None, None  # 에러 없음, 단지 최신 버전임
                
        except requests.RequestException as e:
            error_msg = f"업데이트 서버에 연결할 수 없습니다: {str(e)}"
            self._log_error(f"업데이트 확인 실패: {e}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"업데이트 확인 중 오류가 발생했습니다: {str(e)}"
            self._log_error(f"업데이트 확인 중 오류: {e}")
            return False, None, error_msg
    
    def _get_update_url(self) -> Optional[str]:
        """version.json에서 update_url 가져오기"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('update_url')
        except Exception as e:
            self._log_error(f"update_url 로드 실패: {e}")
        return None
    
    def get_download_url(self, asset_name: Optional[str] = None) -> Optional[str]:
        """
        다운로드 URL 가져오기
        
        Args:
            asset_name: 다운로드할 에셋 이름 (None이면 첫 번째 .exe 파일)
            
        Returns:
            다운로드 URL
        """
        if not self.latest_info or 'assets' not in self.latest_info:
            return None
        
        assets = self.latest_info['assets']
        
        if not assets:
            return None
        
        # 특정 에셋 이름이 지정된 경우
        if asset_name:
            for asset in assets:
                if asset['name'] == asset_name:
                    return asset['browser_download_url']
        
        # .exe 파일 찾기
        for asset in assets:
            if asset['name'].endswith('.exe'):
                return asset['browser_download_url']
        
        # 없으면 첫 번째 에셋
        return assets[0]['browser_download_url']


class UpdateDownloader:
    """업데이트 파일 다운로드 클래스"""
    
    def __init__(self):
        self.download_path = None
        self.progress_callback = None
        self.cancel_flag = False
        self.main_app = None  # main app 참조
    
    def set_main_app(self, main_app):
        """main app 참조 설정"""
        self.main_app = main_app
    
    def _log(self, message):
        """로그 메시지 출력 (main app이 있으면 사용, 없으면 print)"""
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)
    
    def _log_error(self, message):
        """에러 로그 메시지 출력 (main app이 있으면 사용, 없으면 print)"""
        if self.main_app and hasattr(self.main_app, 'log_error'):
            self.main_app.log_error(message)
        else:
            print(message)
        
    def download(self, url: str, progress_callback=None) -> Optional[str]:
        """
        파일 다운로드 (자동 재시작 + 이어받기 + 정체 감지 복구)
        """
        import time
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self.progress_callback = progress_callback
        self.cancel_flag = False
        temp_dir = tempfile.gettempdir()
        filename = os.path.basename(url.split('?')[0])
        self.download_path = os.path.join(temp_dir, filename)

        # requests 세션 (자동 재시도)
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        max_retries = 3
        retry_delay = 3
        last_downloaded = 0
        last_progress_time = 0
        stagnation_limit = 30  # 30초 동안 진행이 없으면 재시작

        for attempt in range(1, max_retries + 1):
            try:
                # 이어받기 설정
                headers = {}
                downloaded_size = 0
                if os.path.exists(self.download_path):
                    downloaded_size = os.path.getsize(self.download_path)
                    headers["Range"] = f"bytes={downloaded_size}-"

                self._log(f"[{attempt}/{max_retries}] 다운로드 시작 (이어받기 {downloaded_size} bytes)")

                response = session.get(url, headers=headers, stream=True, timeout=(5, 60))
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0)) + downloaded_size
                self._log(f"총 다운로드 크기: {total_size} bytes")

                mode = "ab" if downloaded_size > 0 else "wb"
                with open(self.download_path, mode) as f:
                    start_time = time.time()
                    last_downloaded = downloaded_size
                    last_progress_time = start_time

                    for chunk in response.iter_content(chunk_size=8192):
                        if self.cancel_flag:
                            self._log("다운로드 취소됨")
                            self._cleanup()
                            return None

                        if not chunk:
                            continue

                        f.write(chunk)
                        downloaded_size += len(chunk)

                        if self.progress_callback and total_size > 0:
                            self.progress_callback(downloaded_size, total_size)

                        # 5초마다 로그
                        now = time.time()
                        if now - last_progress_time > 5:
                            speed = (downloaded_size - last_downloaded) / (now - last_progress_time)
                            self._log(f"[DEBUG] {downloaded_size}/{total_size} bytes ({downloaded_size/total_size*100:.2f}%), {speed/1024:.1f} KB/s")
                            last_downloaded = downloaded_size
                            last_progress_time = now

                        # 진행 정체 감지 (30초 이상 변동 없을 시)
                        if now - last_progress_time > stagnation_limit:
                            self._log_error("⚠️ 다운로드 정체 감지 — 자동 재시작 시도 중...")
                            raise TimeoutError("다운로드 정체 감지로 재시작")

                self._log(f"✅ 다운로드 완료: {self.download_path}")
                return self.download_path

            except Exception as e:
                import traceback
                self._log_error(f"오류 발생 (시도 {attempt}/{max_retries}): {e}")
                self._log_error(traceback.format_exc())

                if attempt < max_retries:
                    self._log(f"{retry_delay}초 후 자동 재시작 (이어받기 유지)...")
                    time.sleep(retry_delay)
                    continue
                else:
                    self._log_error("❌ 모든 재시도 실패 — 다운로드 중단됨.")
                    self._cleanup()
                    return None

    
    def cancel(self):
        """다운로드 취소"""
        self.cancel_flag = True
    
    def _cleanup(self):
        """임시 파일 정리"""
        if self.download_path and os.path.exists(self.download_path):
            try:
                os.remove(self.download_path)
            except Exception as e:
                self._log_error(f"임시 파일 삭제 실패: {e}")


class UpdateInstaller:
    """업데이트 설치 클래스"""
    
    @staticmethod
    def install_update(update_file: str, restart: bool = True, logger=None) -> bool:
        """
        업데이트 설치
        
        Args:
            update_file: 다운로드된 업데이트 파일 경로
            restart: 설치 후 재시작 여부
            
        Returns:
            설치 성공 여부
        """
        def _log(message):
            if logger and hasattr(logger, 'log'):
                logger.log(message)
            else:
                print(message)
        
        def _log_error(message):
            if logger and hasattr(logger, 'log_error'):
                logger.log_error(message)
            else:
                print(message)
        
        try:
            _log(f"업데이트 파일 확인: {update_file}")
            
            # 업데이트 파일 존재 여부 확인
            if not os.path.exists(update_file):
                _log_error(f"업데이트 파일을 찾을 수 없습니다: {update_file}")
                return False
            
            # 파일 크기 확인
            file_size = os.path.getsize(update_file)
            _log(f"업데이트 파일 크기: {file_size} bytes")
            
            if file_size < 1000000:  # 1MB 미만이면 이상함
                _log_error(f"업데이트 파일이 너무 작습니다: {file_size} bytes")
                return False
            
            # 현재 실행 파일 경로
            current_exe = sys.executable
            is_frozen = getattr(sys, 'frozen', False)
            
            _log(f"현재 실행 파일: {current_exe}")
            _log(f"Frozen 상태: {is_frozen}")
            
            if not is_frozen:
                _log("개발 모드에서는 업데이트를 설치할 수 없습니다.")
                _log(f"업데이트 파일 위치: {update_file}")
                return False
            
            # 현재 실행 파일 접근 권한 체크
            if not os.access(os.path.dirname(current_exe), os.W_OK):
                _log_error(f"실행 파일 디렉토리에 쓰기 권한이 없습니다: {os.path.dirname(current_exe)}")
                return False
            
            # 업데이트 스크립트 생성
            _log("업데이트 스크립트 생성 중...")
            updater_script = UpdateInstaller._create_updater_script(
                current_exe, update_file, restart, logger
            )
            
            if not updater_script:
                _log_error("업데이트 스크립트 생성 실패")
                return False
            
            _log(f"업데이트 스크립트 생성됨: {updater_script}")
            
            # 별도 프로세스로 업데이트 스크립트 실행
            if sys.platform == 'win32':
                # Windows: 더 안전한 방식으로 배치 파일 실행
                _log("Windows 업데이트 스크립트 실행...")
                _log(f"스크립트 경로: {updater_script}")
                
                try:
                    # 방법 1: shell=True 사용 (경로 문제 해결)
                    process = subprocess.Popen(
                        updater_script,
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                        cwd=os.path.dirname(current_exe)
                    )
                    _log(f"업데이트 프로세스 시작됨 (shell=True): PID {process.pid}")
                except Exception as e:
                    _log_error(f"shell=True 방식 실패, 대안 시도: {e}")
                    try:
                        # 방법 2: start 명령어 사용
                        process = subprocess.Popen(
                            ['cmd', '/c', 'start', '/min', updater_script],
                            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                            cwd=os.path.dirname(current_exe)
                        )
                        _log(f"업데이트 프로세스 시작됨 (start 명령어): PID {process.pid}")
                    except Exception as e2:
                        _log_error(f"start 명령어도 실패: {e2}")
                        # 방법 3: 직접 실행 (마지막 시도)
                        process = subprocess.Popen(
                            [updater_script],
                            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                            cwd=os.path.dirname(current_exe)
                        )
                        _log(f"업데이트 프로세스 시작됨 (직접 실행): PID {process.pid}")
            else:
                # Linux/Mac: bash로 실행
                _log("Unix 업데이트 스크립트 실행...")
                process = subprocess.Popen(['bash', updater_script])
                _log(f"업데이트 프로세스 시작됨: PID {process.pid}")
            
            # 현재 앱 종료
            if restart:
                _log("3초 후 앱을 종료하고 업데이트를 설치합니다...")
                import time
                time.sleep(3)  # 스크립트가 시작할 시간을 줌
                sys.exit(0)
            
            return True
            
        except Exception as e:
            _log_error(f"업데이트 설치 실패: {e}")
            import traceback
            _log_error(f"상세 오류: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def _create_updater_script(current_exe: str, update_file: str, restart: bool, logger=None) -> Optional[str]:
        """
        업데이트 스크립트 생성
        
        Args:
            current_exe: 현재 실행 파일 경로
            update_file: 업데이트 파일 경로
            restart: 재시작 여부
            
        Returns:
            스크립트 파일 경로
        """
        try:
            temp_dir = tempfile.gettempdir()
            
            if sys.platform == 'win32':
                # Windows 배치 스크립트
                script_path = os.path.join(temp_dir, 'updater.bat')
                
                # 경로를 더 안전하게 처리 - 짧은 경로명 사용
                def get_safe_path(path):
                    """안전한 배치 스크립트용 경로 반환"""
                    try:
                        # Windows의 짧은 경로명 사용 (공백/특수문자 문제 해결)
                        import ctypes
                        from ctypes import wintypes
                        
                        GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
                        GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
                        GetShortPathNameW.restype = wintypes.DWORD
                        
                        buffer = ctypes.create_unicode_buffer(260)
                        if GetShortPathNameW(path, buffer, 260):
                            return buffer.value
                        else:
                            # 짧은 경로 변환 실패 시 원래 경로 사용 (추가 이스케이프 처리)
                            return path.replace('&', '^&').replace('(', '^(').replace(')', '^)')
                    except Exception:
                        # 변환 실패 시 원래 경로 사용 (추가 이스케이프 처리)
                        return path.replace('&', '^&').replace('(', '^(').replace(')', '^)')
                
                safe_current_exe = get_safe_path(current_exe)
                safe_update_file = get_safe_path(update_file)
                safe_backup = get_safe_path(current_exe + '.bak')
                
                # 디버깅 정보 출력
                if logger and hasattr(logger, 'log'):
                    logger.log(f"원래 실행 파일 경로: {current_exe}")
                    logger.log(f"안전한 실행 파일 경로: {safe_current_exe}")
                    logger.log(f"원래 업데이트 파일 경로: {update_file}")
                    logger.log(f"안전한 업데이트 파일 경로: {safe_update_file}")
                else:
                    print(f"원래 실행 파일 경로: {current_exe}")
                    print(f"안전한 실행 파일 경로: {safe_current_exe}")
                    print(f"원래 업데이트 파일 경로: {update_file}")
                    print(f"안전한 업데이트 파일 경로: {safe_update_file}")
                
                # ZIP 파일인지 확인하고 압축 해제 경로 설정
                temp_extract_dir = os.path.join(tempfile.gettempdir(), 'update_extract')
                safe_extract_dir = get_safe_path(temp_extract_dir)
                
                script_content = f"""@echo off
chcp 65001 > nul
echo 업데이트 설치 중...
timeout /t 2 /nobreak > nul

REM 압축 해제 디렉토리 생성
if exist "{safe_extract_dir}" rmdir /s /q "{safe_extract_dir}"
mkdir "{safe_extract_dir}"

REM ZIP 파일 압축 해제 (PowerShell 사용)
echo ZIP 파일 압축 해제 중...
powershell -command "Expand-Archive -Path '{safe_update_file}' -DestinationPath '{safe_extract_dir}' -Force"

REM 압축 해제 확인
if not exist "{safe_extract_dir}" (
    echo 압축 해제 실패!
    pause
    exit /b 1
)

REM 압축 해제된 EXE 파일 찾기 (BundleEditor.exe 또는 *.exe)
set "extracted_exe="
for /r "{safe_extract_dir}" %%f in (BundleEditor.exe) do (
    if exist "%%f" set "extracted_exe=%%f"
)

REM BundleEditor.exe가 없으면 첫 번째 .exe 파일 사용
if "%extracted_exe%"=="" (
    for /r "{safe_extract_dir}" %%f in (*.exe) do (
        if "%extracted_exe%"=="" set "extracted_exe=%%f"
    )
)

REM EXE 파일 찾기 확인
if "%extracted_exe%"=="" (
    echo 압축 해제된 폴더에서 EXE 파일을 찾을 수 없습니다!
    echo 압축 해제 폴더 내용:
    dir "{safe_extract_dir}" /s
    pause
    exit /b 1
)

echo 찾은 EXE 파일: %extracted_exe%

REM 현재 실행 파일 백업
if exist "{safe_backup}" del /f /q "{safe_backup}"
echo 현재 실행 파일 백업 중...
move "{safe_current_exe}" "{safe_backup}"

REM 새 버전 복사
echo 새 버전 설치 중...
copy /y "%extracted_exe%" "{safe_current_exe}"

REM 복사 성공 확인
if not exist "{safe_current_exe}" (
    echo 업데이트 복사 실패! 백업에서 복원합니다.
    move "{safe_backup}" "{safe_current_exe}"
    pause
    exit /b 1
)

REM 임시 파일들 삭제
echo 임시 파일 정리 중...
if exist "{safe_update_file}" del /f /q "{safe_update_file}"
if exist "{safe_extract_dir}" rmdir /s /q "{safe_extract_dir}"

echo 업데이트 완료!
"""
                
                if restart:
                    script_content += f'\necho 애플리케이션 재시작 중...\nstart "" "{safe_current_exe}"\n'
                
                script_content += '\necho 업데이트 스크립트 종료\ndel "%~f0"\n'  # 스크립트 자체 삭제
                
            else:
                # Linux/Mac 셸 스크립트
                script_path = os.path.join(temp_dir, 'updater.sh')
                
                script_content = f"""#!/bin/bash
echo "업데이트 설치 중..."
sleep 2

# 현재 실행 파일 백업
if [ -f "{current_exe}.bak" ]; then
    rm "{current_exe}.bak"
fi
mv "{current_exe}" "{current_exe}.bak"

# 새 버전 복사
cp "{update_file}" "{current_exe}"
chmod +x "{current_exe}"

# 임시 파일 삭제
rm "{update_file}"

echo "업데이트 완료!"
"""
                
                if restart:
                    script_content += f'\n"{current_exe}" &\n'
                
                script_content += f'\nrm "{script_path}"\n'  # 스크립트 자체 삭제
            
            # 스크립트 파일 저장
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 실행 권한 부여 (Linux/Mac)
            if sys.platform != 'win32':
                os.chmod(script_path, 0o755)
            
            return script_path
            
        except Exception as e:
            if logger and hasattr(logger, 'log_error'):
                logger.log_error(f"업데이트 스크립트 생성 실패: {e}")
            else:
                print(f"업데이트 스크립트 생성 실패: {e}")
            return None


class AutoUpdater:
    """통합 자동 업데이트 관리자"""
    
    def __init__(self, version_file: str = "version.json"):
        self.checker = UpdateChecker(version_file)
        self.downloader = UpdateDownloader()
        self.update_available = False
        self.latest_info = None
        self.main_app = None  # main app 참조
    
    def set_main_app(self, main_app):
        """main app 참조 설정"""
        self.main_app = main_app
        # 하위 컴포넌트들에도 참조 전달
        self.checker.set_main_app(main_app)
        self.downloader.set_main_app(main_app)
    
    def _log(self, message):
        """로그 메시지 출력 (main app이 있으면 사용, 없으면 print)"""
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)
    
    def _log_error(self, message):
        """에러 로그 메시지 출력 (main app이 있으면 사용, 없으면 print)"""
        if self.main_app and hasattr(self.main_app, 'log_error'):
            self.main_app.log_error(message)
        else:
            print(message)
        
    def check_updates_async(self, callback=None):
        """
        비동기로 업데이트 확인
        
        Args:
            callback: 완료 콜백 함수 (has_update, info, error_msg)
        """
        def check_thread():
            try:
                self._log("[DEBUG] 업데이트 확인 스레드 시작")
                has_update, info, error_msg = self.checker.check_for_updates()
                self._log(f"[DEBUG] check_for_updates 결과 - has_update: {has_update}, error_msg: {error_msg}, info 타입: {type(info)}")
                
                self.update_available = has_update
                self.latest_info = info
                
                if callback:
                    try:
                        self._log("[DEBUG] 콜백 함수 호출 시도")
                        callback(has_update, info, error_msg)
                        self._log("[DEBUG] 콜백 함수 호출 성공")
                    except Exception as e:
                        self._log_error(f"업데이트 콜백 실행 중 오류: {e}")
                else:
                    self._log("[DEBUG] 콜백 함수가 None입니다.")
            except Exception as e:
                self._log_error(f"업데이트 확인 스레드 중 예상치 못한 오류: {e}")
                if callback:
                    try:
                        callback(False, None, f"업데이트 확인 중 내부 오류가 발생했습니다: {str(e)}")
                    except Exception as callback_error:
                        self._log_error(f"오류 콜백 실행 중 추가 오류: {callback_error}")
        
        self._log("[DEBUG] 스레드 생성 및 시작 시도")
        try:
            thread = threading.Thread(target=check_thread, daemon=True)
            thread.start()
            self._log("[DEBUG] 스레드 시작 성공")
        except Exception as e:
            self._log_error(f"업데이트 확인 스레드 시작 실패: {e}")
            if callback:
                try:
                    callback(False, None, f"업데이트 확인 시스템을 시작할 수 없습니다: {str(e)}")
                except Exception as callback_error:
                    self._log_error(f"오류 콜백 실행 중 추가 오류: {callback_error}")
    
    def download_and_install(self, progress_callback=None, completion_callback=None):
        """
        다운로드 및 설치
        
        Args:
            progress_callback: 진행률 콜백 (received, total)
            completion_callback: 완료 콜백 (success)
        """
        def download_thread():
            try:
                # 다운로드 URL 가져오기
                download_url = self.checker.get_download_url()
                
                if not download_url:
                    self._log_error("다운로드 URL을 찾을 수 없습니다.")
                    if completion_callback:
                        completion_callback(False)
                    return
                
                # 다운로드
                update_file = self.downloader.download(download_url, progress_callback)
                
                if not update_file:
                    if completion_callback:
                        completion_callback(False)
                    return
                
                # 설치
                try:
                    self._log("업데이트 설치 시작...")
                    success = UpdateInstaller.install_update(update_file, restart=True, logger=self.main_app)
                    self._log(f"설치 결과: {'성공' if success else '실패'}")
                    
                    if completion_callback:
                        completion_callback(success)
                        
                except Exception as install_error:
                    self._log_error(f"업데이트 설치 실패: {install_error}")
                    import traceback
                    self._log_error(f"상세 오류: {traceback.format_exc()}")
                    if completion_callback:
                        completion_callback(False)
                    
            except Exception as e:
                self._log_error(f"다운로드/설치 중 오류: {e}")
                import traceback
                self._log_error(f"상세 오류: {traceback.format_exc()}")
                if completion_callback:
                    completion_callback(False)
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
    
    def cancel_download(self):
        """다운로드 취소"""
        self.downloader.cancel()


if __name__ == '__main__':
    print("=== 업데이트 시스템 테스트 ===")
    
    updater = AutoUpdater()

    has_update, info, error_msg = updater.checker.check_for_updates()

    if error_msg:
        updater._log_error(f"에러: {error_msg}")
    elif has_update:
        updater._log(f"새 버전 발견: {info['version']}")
        updater._log(f"변경사항:\n{info['body']}")
        
        # 테스트용: 실제 업데이트 실행
        updater._log("테스트 모드: 새 버전 다운로드 및 설치 시도 중...")
        
        def progress(received, total):
            percent = (received / total) * 100
            updater._log(f"진행률: {percent:.2f}% ({received}/{total} bytes)")
        
        def done(success):
            if success:
                updater._log("✅ 업데이트 완료 (앱이 재시작됩니다).")
            else:
                updater._log_error("❌ 업데이트 실패.")
        
        updater.download_and_install(progress_callback=progress, completion_callback=done)
        
    else:
        updater._log("현재 최신 버전을 사용 중입니다.")
