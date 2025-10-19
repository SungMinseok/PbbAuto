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
        파일 다운로드
        
        Args:
            url: 다운로드 URL
            progress_callback: 진행률 콜백 함수 (received, total)
            
        Returns:
            다운로드된 파일 경로
        """
        self.progress_callback = progress_callback
        self.cancel_flag = False
        
        try:
            self._log(f"다운로드 시작: {url}")
            
            # 임시 파일 생성
            temp_dir = tempfile.gettempdir()
            filename = os.path.basename(url.split('?')[0])  # 쿼리 파라미터 제거
            self.download_path = os.path.join(temp_dir, filename)
            
            # 다운로드
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(self.download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancel_flag:
                        self._log("다운로드 취소됨")
                        self._cleanup()
                        return None
                    
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if self.progress_callback and total_size > 0:
                            self.progress_callback(downloaded_size, total_size)
            
            self._log(f"다운로드 완료: {self.download_path}")
            return self.download_path
            
        except requests.RequestException as e:
            self._log_error(f"다운로드 실패: {e}")
            self._cleanup()
            return None
        except Exception as e:
            self._log_error(f"다운로드 중 오류: {e}")
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
                # Windows: cmd로 실행
                _log("Windows 업데이트 스크립트 실행...")
                process = subprocess.Popen(
                    ['cmd', '/c', f'"{updater_script}"'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                    cwd=os.path.dirname(current_exe)
                )
                _log(f"업데이트 프로세스 시작됨: PID {process.pid}")
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
                
                script_content = f"""@echo off
echo 업데이트 설치 중...
timeout /t 2 /nobreak > nul

REM 현재 실행 파일 백업
if exist "{current_exe}.bak" del "{current_exe}.bak"
move "{current_exe}" "{current_exe}.bak"

REM 새 버전 복사
copy "{update_file}" "{current_exe}"

REM 임시 파일 삭제
del "{update_file}"

echo 업데이트 완료!
"""
                
                if restart:
                    script_content += f'\nstart "" "{current_exe}"\n'
                
                script_content += '\ndel "%~f0"\n'  # 스크립트 자체 삭제
                
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
    # 테스트 코드
    print("=== 업데이트 시스템 테스트 ===")
    
    updater = AutoUpdater()
    has_update, info, error_msg = updater.checker.check_for_updates()
    
    if error_msg:
        updater._log_error(f"에러: {error_msg}")
    elif has_update:
        updater._log(f"새 버전: {info['version']}")
        updater._log(f"변경사항:\n{info['body']}")
    else:
        updater._log("최신 버전입니다.")

