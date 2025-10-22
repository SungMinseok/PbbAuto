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

                self._log(f"✅ 새로운 버전 발견: {latest_version}")
                return True, update_info, None
            else:
                self._log("✅ 현재 최신 버전을 사용 중입니다.")
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


class UpdateInstaller:
    """설치 클래스"""

    @staticmethod
    def install_update(zip_path: str, restart: bool = True, logger=None) -> bool:
        def _log(msg):
            if logger and hasattr(logger, 'log'):
                logger.log(msg)
            else:
                print(msg)

        def _log_error(msg):
            if logger and hasattr(logger, 'log_error'):
                logger.log_error(msg)
            else:
                print(msg)

        try:
            _log("업데이트 설치 시작...")

            # 실행 파일 경로
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                current_exe = os.path.abspath("BundleEditor.exe")

            current_dir = os.path.dirname(current_exe)
            _log(f"설치 디렉토리: {current_dir}")

            # 압축 해제 폴더 (앱 폴더 내부)
            extract_dir = os.path.join(current_dir, "update_extract")
            _log(f"압축 해제 폴더: {extract_dir}")
            
            if os.path.exists(extract_dir):
                _log("기존 압축 해제 폴더 삭제 중...")
                shutil.rmtree(extract_dir, ignore_errors=True)
            
            _log("압축 해제 폴더 생성 중...")
            os.makedirs(extract_dir, exist_ok=True)

            _log(f"ZIP 파일 압축 해제 중... ({zip_path})")
            _log("Windows Defender 안정화 대기 중... (2초)")
            time.sleep(2)  # Defender 안정화 대기 (증가)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    _log(f"압축 파일 내 항목 수: {len(file_list)}")
                    _log("압축 해제 시작...")
                    zip_ref.extractall(extract_dir)
                _log("✅ 압축 해제 완료")
            except zipfile.BadZipFile as e:
                _log_error(f"❌ 손상된 ZIP 파일: {e}")
                raise
            except Exception as e:
                _log_error(f"❌ 압축 해제 실패: {e}")
                import traceback
                _log_error(traceback.format_exc())
                raise

            # 배치 스크립트 생성
            _log("배치 스크립트 생성 중...")
            bat_path = os.path.join(current_dir, "bundleeditor_update.bat")
            exe_name = os.path.basename(current_exe)
            
            with open(bat_path, 'w', encoding='utf-8-sig') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 > nul\n')
                f.write('echo BundleEditor 업데이트 중...\n')
                
                # EXE 모드인 경우에만 프로세스 종료 대기
                if getattr(sys, 'frozen', False):
                    f.write('echo 기존 프로세스 종료 대기 중...\n')
                    f.write('set WAIT_COUNT=0\n')
                    f.write('\n')
                    
                    # 프로세스가 완전히 종료될 때까지 대기 (최대 30초)
                    f.write(':WAIT_PROCESS\n')
                    f.write('set /A WAIT_COUNT+=1\n')
                    f.write('if %WAIT_COUNT% GTR 30 (\n')
                    f.write('    echo 타임아웃: 프로세스가 종료되지 않았습니다.\n')
                    f.write('    goto UPDATE_FILES\n')
                    f.write(')\n')
                    f.write(f'tasklist /FI "IMAGENAME eq {exe_name}" 2>NUL | find /I /N "{exe_name}">NUL\n')
                    f.write('if "%ERRORLEVEL%"=="0" (\n')
                    f.write('    timeout /t 1 /nobreak > nul\n')
                    f.write('    goto WAIT_PROCESS\n')
                    f.write(')\n')
                    f.write('\n')
                    f.write('echo 프로세스 종료 완료.\n')
                else:
                    f.write('echo 개발 모드: 프로세스 대기 건너뛰기\n')
                
                f.write('\n')
                f.write(':UPDATE_FILES\n')
                f.write('echo 파일 업데이트 중...\n')
                f.write('timeout /t 1 /nobreak > nul\n')
                f.write(f'xcopy "{extract_dir}" "{current_dir}" /E /H /C /Y\n')
                f.write(f'rd /s /q "{extract_dir}"\n')
                f.write(f'del /f /q "{zip_path}"\n')
                f.write('\n')
                
                if restart and getattr(sys, 'frozen', False):
                    f.write('echo 새 버전 시작 중...\n')
                    f.write('timeout /t 1 /nobreak > nul\n')
                    f.write(f'start "" "{current_exe}"\n')
                else:
                    f.write('echo 개발 모드: 자동 시작 건너뛰기\n')
                
                f.write('del "%~f0"\n')

            _log(f"✅ 배치 스크립트 생성: {bat_path}")

            # CMD 실행 (안정형)
            _log("업데이트 스크립트 실행 중...")
            cmd_line = f'start "" cmd.exe /c "{bat_path}"'
            subprocess.Popen(cmd_line, shell=True, cwd=current_dir)
            _log("✅ 업데이트 스크립트 실행 완료")

            # 앱 종료
            if restart and getattr(sys, 'frozen', False):
                _log("앱 종료 중... (3초 후)")
                time.sleep(3)
                sys.exit(0)
            else:
                _log("⚠️ 개발 모드: 자동 재시작 안 함")

            return True

        except zipfile.BadZipFile as e:
            _log_error(f"❌ ZIP 파일 오류: {e}")
            return False
        except Exception as e:
            _log_error(f"❌ 업데이트 설치 실패: {e}")
            import traceback
            _log_error(traceback.format_exc())
            return False


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
                success = UpdateInstaller.install_update(zip_path, restart=True, logger=self.main_app)
                if completion_callback:
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

    response = input("업데이트를 진행하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("업데이트 취소됨")
        sys.exit(0)

    print()
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

    success = UpdateInstaller.install_update(zip_path, restart=False)

    if success:
        print()
        print("=" * 60)
        print("✅ 업데이트 테스트 완료!")
        print("=" * 60)
        print("배치 스크립트가 백그라운드에서 실행 중입니다.")
    else:
        print("❌ 설치 실패")
        sys.exit(1)
