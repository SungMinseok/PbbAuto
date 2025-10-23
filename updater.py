"""
자동 업데이트 시스템 (앱 폴더 기반)
GitHub Releases를 통한 버전 체크 및 업데이트

정석 방식:
1. 버전 체크 (GitHub API)
2. 다운로드 (앱 폴더)
3. 압축 해제 (앱 폴더)
4. 배치 스크립트로 파일 교체
5. 앱 재시작

단독 실행 테스트:
python updater.py
"""

# 로그 설정
try:
    import logger_setup
except ImportError:
    pass

import json
import os
import sys
import requests
import subprocess
import shutil
import zipfile
from typing import Optional, Dict, Any, Tuple
from packaging import version as version_parser
import threading
import time


class UpdateChecker:
    """버전 체크 클래스"""

    def __init__(self, version_file: str = "version.json"):
        self.version_file = version_file
        self.current_version = self._load_current_version()
        self.main_app = None

    def set_main_app(self, main_app):
        self.main_app = main_app

    def _log(self, message):
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)

    def _log_error(self, message):
        if self.main_app and hasattr(self.main_app, 'log_error'):
            self.main_app.log_error(message)
        else:
            print(message)

    def _load_current_version(self) -> str:
        """현재 버전 로드"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
        except Exception as e:
            print(f"버전 파일 로드 실패: {e}")
        return '0.0.0'

    def check_for_updates(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """업데이트 확인"""
        try:
            self._log("서버에서 최신 버전 확인 중...")

            api_url = "https://api.github.com/repos/SungMinseok/PbbAuto/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data['tag_name'].lstrip('v')

            self._log(f"현재 버전: {self.current_version}")
            self._log(f"최신 버전: {latest_version}")

            if version_parser.parse(latest_version) > version_parser.parse(self.current_version):
                download_url = None
                for asset in release_data.get('assets', []):
                    if asset['name'].endswith('.zip'):
                        download_url = asset['browser_download_url']
                        break

                if not download_url:
                    return False, None, "다운로드 가능한 ZIP 파일이 없습니다."

                update_info = {
                    'version': latest_version,
                    'download_url': download_url,
                    'release_notes': release_data.get('body', ''),
                    'published_at': release_data.get('published_at', '')
                }

                self._log(f"새로운 버전 발견: {latest_version}")
                return True, update_info, None
            else:
                self._log("현재 최신 버전을 사용 중입니다.")
                return False, None, None

        except requests.exceptions.RequestException as e:
            error_msg = f"네트워크 오류: {e}"
            self._log_error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"업데이트 확인 중 오류: {e}"
            self._log_error(error_msg)
            return False, None, error_msg


class UpdateDownloader:
    """다운로드 클래스"""

    def __init__(self):
        self.main_app = None
        self.cancel_flag = False

    def set_main_app(self, main_app):
        self.main_app = main_app

    def _log(self, message):
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)

    def _log_error(self, message):
        if self.main_app and hasattr(self.main_app, 'log_error'):
            self.main_app.log_error(message)
        else:
            print(message)

    def download(self, url: str, progress_callback=None) -> Optional[str]:
        """ZIP 파일을 앱 폴더에 다운로드"""
        download_path = None
        try:
            # 현재 실행 중인 앱 경로
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.abspath(os.path.dirname(__file__))

            download_path = os.path.join(base_dir, "BundleEditor_update.zip")

            self._log(f"다운로드 시작: {url}")
            self._log(f"저장 위치: {download_path}")

            # 타임아웃을 충분히 길게 설정 (연결: 30초, 읽기: 300초)
            response = requests.get(url, stream=True, timeout=(30, 300))
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            self._log(f"다운로드 크기: {total_size / (1024*1024):.2f} MB")

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancel_flag:
                        self._log("다운로드 취소됨")
                        # 취소 시 파일 삭제
                        if os.path.exists(download_path):
                            os.remove(download_path)
                        return None
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            self._log(f"✅ 다운로드 완료: {download_path}")
            self._log(f"다운로드된 크기: {downloaded / (1024*1024):.2f} MB")
            
            # 다운로드 크기 검증
            if total_size > 0 and downloaded < total_size:
                self._log_error(f"⚠️ 불완전한 다운로드: {downloaded}/{total_size} bytes")
                if os.path.exists(download_path):
                    os.remove(download_path)
                return None
            
            # ZIP 저장 후 출처 태그 제거 (Windows Defender 차단 방지)
            try:
                zone_file = download_path + ":Zone.Identifier"
                if os.path.exists(zone_file):
                    os.remove(zone_file)
                    self._log("Zone.Identifier 제거 완료")
            except Exception as e:
                self._log(f"Zone.Identifier 제거 실패 (무시): {e}")
            
            return download_path

        except requests.exceptions.Timeout as e:
            self._log_error(f"다운로드 타임아웃: {e}")
            if download_path and os.path.exists(download_path):
                os.remove(download_path)
            return None
        except requests.exceptions.RequestException as e:
            self._log_error(f"네트워크 오류: {e}")
            if download_path and os.path.exists(download_path):
                os.remove(download_path)
            return None
        except Exception as e:
            self._log_error(f"다운로드 실패: {e}")
            import traceback
            self._log_error(traceback.format_exc())
            if download_path and os.path.exists(download_path):
                os.remove(download_path)
            return None

    def cancel(self):
        """다운로드 취소"""
        self.cancel_flag = True


# 수정된 updater.py: BAT 파일 제거, 직접 압축 해제 및 EXE 교체 방식

# 이하 생략된 공통 코드...

class UpdateInstaller:
    """설치 클래스: 배치 스크립트를 통한 EXE 교체"""

    @staticmethod
    def install_update(zip_path: str, restart: bool = True, logger=None) -> bool:
        def _log(msg): print(msg) if not logger else logger.log(msg)
        def _log_error(msg): print(msg) if not logger else logger.log_error(msg)

        try:
            _log("업데이트 설치 시작...")

            # 실행 파일 경로
            current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath("BundleEditor.exe")
            current_dir = os.path.dirname(current_exe)
            extract_dir = os.path.join(current_dir, "update_extract")
            exe_name = os.path.basename(current_exe)

            # 기존 압축 해제 폴더 삭제 및 재생성
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            os.makedirs(extract_dir, exist_ok=True)

            _log(f"ZIP 압축 해제 중... ({zip_path})")
            time.sleep(1)  # Defender 안정화 대기
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            _log("✅ 압축 해제 완료")

            # 배치 스크립트 생성
            bat_path = os.path.join(current_dir, "update_installer.bat")
            _log(f"배치 스크립트 생성 중... ({bat_path})")

            bat_content = f"""@echo off
chcp 65001 > nul
echo ========================================
echo Bundle Editor Update Installation...
echo ========================================

echo.

REM Wait for process termination
echo [1/5] Waiting for current process to terminate...
ping 127.0.0.1 -n 3 > nul REM Wait 2 seconds + a
taskkill /F /IM "{exe_name}" > nul 2>&1
ping 127.0.0.1 -n 2 > nul REM Wait 1 second + a
echo ✓ Process terminated

echo.

REM PROCESS RELEASE WAIT (5 seconds)
echo [1.5/5] Waiting for process to release file handles (5s)...
ping 127.0.0.1 -n 6 > nul REM Wait 5 seconds + a
echo ✓ Wait complete
echo.

REM File copy
echo [2/5] Copying files...
xcopy /E /I /H /Y "{extract_dir}\\*" "{current_dir}\\" > nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ File copy failed
    pause  REM <--- 복사 실패 시 멈춤
    exit /b 1
)
echo ✓ Files copied
REM pause  REM <--- 복사 성공 시 멈춤
echo.

REM Cleanup
echo [3/5] Cleaning up temporary files...
if exist "{zip_path}" del /F /Q "{zip_path}" > nul 2>&1
if exist "{extract_dir}" rmdir /S /Q "{extract_dir}" > nul 2>&1
echo ✓ Cleanup complete
echo.

REM Restart
echo [4/5] Starting new version...
start "" "{current_exe}"
ping 127.0.0.1 -n 2 > nul REM Wait 1 second + a
echo ✓ Restart complete
echo.

REM Self-delete batch file
echo [5/5] Cleaning up installer script...
ping 127.0.0.1 -n 3 > nul REM Wait 2 seconds + a
REM pause
(goto) 2>nul & del "%~f0"
"""

            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)

            _log("✅ 배치 스크립트 생성 완료")

            time.sleep(5)
            # 배치 파일 실행 (숨겨진 창에서)
            if restart:
                _log("🚀 업데이트 설치 스크립트 실행 중...")
                _log("⚠️ 잠시 후 프로그램이 자동으로 재시작됩니다.")
                
                #time.sleep(2)
                # 수정된 코드 (CMD 창 노출):
                os.startfile(bat_path)
                # 현재 프로세스 종료 (배치 스크립트가 처리함)
                time.sleep(3)
                sys.exit(0)

            return True

        except Exception as e:
            _log_error(f"❌ 업데이트 실패: {e}")
            import traceback
            _log_error(traceback.format_exc())
            return False

# 나머지 AutoUpdater, main 실행부는 유지



class AutoUpdater:
    """통합 자동 업데이트 관리자"""

    def __init__(self, version_file: str = "version.json"):
        self.checker = UpdateChecker(version_file)
        self.downloader = UpdateDownloader()
        self.update_available = False
        self.latest_info = None
        self.main_app = None

    def set_main_app(self, main_app):
        self.main_app = main_app
        self.checker.set_main_app(main_app)
        self.downloader.set_main_app(main_app)

    def _log(self, message):
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)

    def _log_error(self, message):
        if self.main_app and hasattr(self.main_app, 'log_error'):
            self.main_app.log_error(message)
        else:
            print(message)

    def check_updates_async(self, callback=None):
        """비동기로 업데이트 확인"""
        def check_thread():
            try:
                has_update, info, error_msg = self.checker.check_for_updates()
                self.update_available = has_update
                self.latest_info = info
                if callback:
                    callback(has_update, info, error_msg or "")
            except Exception as e:
                self._log_error(f"업데이트 확인 스레드 오류: {e}")
                if callback:
                    callback(False, None, str(e))

        threading.Thread(target=check_thread, daemon=True).start()

    def check_updates_sync(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        [동기적] 업데이트를 확인하고 결과를 반환합니다.
        메인 스레드에서 실행되어야 하며, GUI를 잠시 멈출 수 있습니다.
        """
        self._log("[동기] 서버에서 업데이트 확인 시작...")
        
        try:
            # UpdateChecker의 핵심 로직을 직접 호출합니다. (네트워크 I/O 발생)
            has_update, info, error_msg = self.checker.check_for_updates()
            
            self.update_available = has_update
            self.latest_info = info
            
            if has_update:
                self._log(f"[동기] 새 버전 발견: {info['version']}")
            else:
                self._log("[동기] 현재 최신 버전입니다.")
                
            return has_update, info, error_msg
            
        except Exception as e:
            error_msg = f"업데이트 확인 중 오류 발생: {e}"
            self._log_error(error_msg)
            return False, None, error_msg

    def download_and_install(self, progress_callback=None, completion_callback=None):
        """다운로드 및 설치"""
        def install_thread():
            try:
                if not self.latest_info:
                    self._log_error("업데이트 정보가 없습니다.")
                    if completion_callback:
                        completion_callback(False)
                    return

                download_url = self.latest_info.get('download_url')
                if not download_url:
                    self._log_error("다운로드 URL이 없습니다.")
                    if completion_callback:
                        completion_callback(False)
                    return

                self._log("업데이트 다운로드 시작...")
                zip_path = self.downloader.download(download_url, progress_callback)

                if not zip_path:
                    self._log_error("다운로드 실패")
                    if completion_callback:
                        completion_callback(False)
                    return

                self._log("다운로드 완료, 설치 시작...")
                    
                # install_update가 성공적으로 실행되면 sys.exit(0)을 호출하고 프로세스를 종료합니다.
                # 만약 False를 반환하거나 예외가 발생하면 아래 completion_callback이 호출됩니다.
                success = UpdateInstaller.install_update(zip_path, restart=True, logger=self.main_app)
                
                # NOTE: 만약 install_update 내부에서 sys.exit(0)에 도달하면 이 아래 코드는 실행되지 않습니다.
                
                if completion_callback:
                    # sys.exit(0)에 도달하지 못하고 실패했을 때만 콜백을 호출하여 앱에 알림
                    completion_callback(success)

            except Exception as e:
                self._log_error(f"업데이트 다운로드/설치 오류: {e}")
                import traceback
                self._log_error(traceback.format_exc())
                if completion_callback:
                    completion_callback(False)

        threading.Thread(target=install_thread, daemon=True).start()


# ==================== 단독 실행 테스트 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("BundleEditor 업데이트 테스트")
    print("=" * 60)
    print()

    updater = AutoUpdater()
    print("[1] 서버에서 최신 버전 확인 중...")
    has_update, info, error_msg = updater.checker.check_for_updates()

    if error_msg:
        print(f"❌ 오류: {error_msg}")
        sys.exit(1)

    if not has_update:
        print("✅ 현재 최신 버전입니다.")
        sys.exit(0)

    print(f"✅ 새로운 버전 발견: {info['version']}")
    print(f"   다운로드 URL: {info['download_url']}")
    print()

    # response = input("업데이트를 진행하시겠습니까? (y/n): ")
    # if response.lower() != 'y':
    #     print("업데이트 취소됨")
    #     sys.exit(0)

    # print()
    print("[2] 다운로드 중...")

    def progress_callback(received, total):
        percent = (received / total * 100) if total > 0 else 0
        print(f"\r진행률: {percent:.1f}% ({received}/{total} bytes)", end='')

    zip_path = updater.downloader.download(info['download_url'], progress_callback)
    print()

    if not zip_path:
        print("❌ 다운로드 실패")
        sys.exit(1)

    print("✅ 다운로드 완료")
    print()
    print("[3] 설치 시작...")

    success = UpdateInstaller.install_update(zip_path, restart=True)

    if success:
        print()
        print("=" * 60)
        print("✅ 업데이트 테스트 완료!")
        print("=" * 60)
        print("배치 스크립트가 백그라운드에서 실행 중입니다.")
    else:
        print("❌ 설치 실패")
        sys.exit(1)
