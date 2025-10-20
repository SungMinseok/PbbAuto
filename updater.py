"""
자동 업데이트 시스템
GitHub Releases를 통한 버전 체크 및 업데이트

정석 방식:
1. 버전 체크 (GitHub API)
2. 다운로드 (Temp 폴더)
3. 압축 해제
4. 배치 스크립트로 파일 교체
5. 앱 재시작

단독 실행 테스트:
python updater.py
"""

# 로그 설정을 가장 먼저 import
try:
    import logger_setup
except ImportError:
    pass  # 단독 실행 시 logger_setup이 없을 수도 있음

import json
import os
import sys
import requests
import tempfile
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
        """
        업데이트 확인
        
        Returns:
            (has_update, update_info, error_message)
        """
        try:
            self._log("서버에서 최신 버전 확인 중...")
            
            # GitHub API로 최신 릴리스 정보 가져오기
            api_url = "https://api.github.com/repos/SungMinseok/PbbAuto/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data['tag_name'].lstrip('v')
            
            self._log(f"현재 버전: {self.current_version}")
            self._log(f"최신 버전: {latest_version}")
            
            # 버전 비교
            if version_parser.parse(latest_version) > version_parser.parse(self.current_version):
                # 다운로드 URL 찾기
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
        """
        파일 다운로드
        
        Args:
            url: 다운로드 URL
            progress_callback: 진행률 콜백 함수 (received, total)
            
        Returns:
            다운로드된 파일 경로 (실패 시 None)
        """
        try:
            temp_dir = tempfile.gettempdir()
            download_path = os.path.join(temp_dir, "BundleEditor_update.zip")
            
            self._log(f"다운로드 시작: {url}")
            self._log(f"저장 위치: {download_path}")
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            self._log(f"총 크기: {total_size} bytes")
            
            downloaded = 0
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancel_flag:
                        self._log("다운로드 취소됨")
                        return None
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            self._log(f"✅ 다운로드 완료: {download_path}")
            return download_path
            
        except Exception as e:
            self._log_error(f"다운로드 실패: {e}")
            return None
    
    def cancel(self):
        """다운로드 취소"""
        self.cancel_flag = True


class UpdateInstaller:
    """설치 클래스"""
    
    @staticmethod
    def install_update(zip_path: str, restart: bool = True, logger=None) -> bool:
        """
        업데이트 설치 (정석 방식)
        
        Args:
            zip_path: 다운로드된 ZIP 파일 경로
            restart: 재시작 여부
            logger: 로거 객체
            
        Returns:
            성공 여부
        """
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
            
            # 1. ZIP 파일 존재 확인
            if not os.path.exists(zip_path):
                _log_error(f"ZIP 파일이 존재하지 않습니다: {zip_path}")
                return False
            
            # 2. 현재 실행 파일 확인
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                _log("개발 모드: 테스트 실행")
                current_exe = os.path.abspath("BundleEditor.exe")
                if not os.path.exists(current_exe):
                    _log_error("테스트용 BundleEditor.exe가 없습니다.")
                    return False
            
            current_dir = os.path.dirname(current_exe)
            _log(f"현재 실행 파일: {current_exe}")
            _log(f"설치 디렉토리: {current_dir}")
            
            # 3. 임시 압축 해제 디렉토리 생성
            temp_extract_dir = os.path.join(tempfile.gettempdir(), 'bundleeditor_update_extract')
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir)
            _log(f"압축 해제 디렉토리: {temp_extract_dir}")
            
            # 4. ZIP 파일 압축 해제
            _log("ZIP 파일 압축 해제 중...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            _log("✅ 압축 해제 완료")
            
            # 5. 압축 해제된 파일 목록
            extracted_files = []
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, temp_extract_dir)
                    extracted_files.append((src_path, rel_path))
            
            _log(f"압축 해제된 파일 수: {len(extracted_files)}")
            
            # 6. 배치 스크립트 생성
            bat_script = os.path.join(tempfile.gettempdir(), 'bundleeditor_update.bat')
            
            with open(bat_script, 'w', encoding='utf-8-sig') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 > nul\n')
                f.write('echo ========================================\n')
                f.write('echo BundleEditor 업데이트 설치\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                f.write('echo 앱 종료 대기 중...\n')
                f.write('timeout /t 3 /nobreak > nul\n')
                f.write('echo.\n')
                
                # 파일 복사
                f.write('echo 파일 교체 중...\n')
                for src_path, rel_path in extracted_files:
                    dst_path = os.path.join(current_dir, rel_path)
                    dst_dir = os.path.dirname(dst_path)
                    
                    # 디렉토리 생성
                    if dst_dir and dst_dir != current_dir:
                        f.write(f'if not exist "{dst_dir}" mkdir "{dst_dir}"\n')
                    
                    # 기존 파일 백업 (exe 파일의 경우)
                    if dst_path.lower().endswith('.exe'):
                        f.write(f'if exist "{dst_path}" (\n')
                        f.write(f'    if exist "{dst_path}.bak" del /f /q "{dst_path}.bak"\n')
                        f.write(f'    move /y "{dst_path}" "{dst_path}.bak"\n')
                        f.write(f')\n')
                    
                    # 새 파일 복사
                    f.write(f'copy /y "{src_path}" "{dst_path}"\n')
                    
                    # 복사 확인 (exe 파일의 경우)
                    if dst_path.lower().endswith('.exe'):
                        f.write(f'if not exist "{dst_path}" (\n')
                        f.write(f'    echo 파일 복사 실패: {rel_path}\n')
                        f.write(f'    if exist "{dst_path}.bak" move /y "{dst_path}.bak" "{dst_path}"\n')
                        f.write(f'    echo 백업에서 복구 완료\n')
                        f.write(f'    pause\n')
                        f.write(f'    exit /b 1\n')
                        f.write(f')\n')
                        f.write(f'echo ✓ {rel_path} 복사 완료\n')
                
                f.write('echo.\n')
                f.write('echo 임시 파일 정리 중...\n')
                f.write(f'rmdir /s /q "{temp_extract_dir}"\n')
                f.write(f'del /f /q "{zip_path}"\n')
                
                # .bak 파일 삭제
                for src_path, rel_path in extracted_files:
                    if rel_path.lower().endswith('.exe'):
                        dst_path = os.path.join(current_dir, rel_path)
                        f.write(f'if exist "{dst_path}.bak" del /f /q "{dst_path}.bak"\n')
                
                f.write('echo.\n')
                f.write('echo ========================================\n')
                f.write('echo 업데이트 완료!\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                
                # 재시작
                if restart:
                    f.write('echo 앱 재시작 중...\n')
                    f.write(f'start "" "{current_exe}"\n')
                    f.write('timeout /t 2 /nobreak > nul\n')
                
                # 자기 자신 삭제
                f.write('del "%~f0"\n')
            
            _log(f"✅ 업데이트 스크립트 생성됨: {bat_script}")
            
            # 7. 배치 스크립트 실행
            _log("업데이트 스크립트 실행...")

            try:
                cmd_line = f'start "" cmd.exe /c "{bat_script}"'
                _log(f"CMD 명령어: {cmd_line}")

                subprocess.Popen(
                    cmd_line,
                    shell=True,
                    cwd=os.path.dirname(bat_script)
                )

                _log("✅ 업데이트 스크립트가 성공적으로 실행되었습니다.")
            except Exception as e:
                _log_error(f"업데이트 스크립트 실행 실패: {e}")
                import traceback
                _log_error(traceback.format_exc())
                return False


            
            # 8. 현재 앱 종료
            if restart and getattr(sys, 'frozen', False):
                _log("3초 후 앱을 종료합니다...")
                time.sleep(3)
                sys.exit(0)
            else:
                _log("✅ 테스트 모드: 앱을 종료하지 않습니다.")
                _log("배치 스크립트가 백그라운드에서 실행 중입니다.")
                return True
            
        except Exception as e:
            _log_error(f"업데이트 설치 실패: {e}")
            import traceback
            _log_error(f"상세 오류: {traceback.format_exc()}")
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
        """main app 참조 설정"""
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
        """
        비동기로 업데이트 확인
        
        Args:
            callback: 완료 콜백 함수 (has_update, info, error_msg)
        """
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
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def download_and_install(self, progress_callback=None, completion_callback=None):
        """
        업데이트 다운로드 및 설치
        
        Args:
            progress_callback: 진행률 콜백 (received, total)
            completion_callback: 완료 콜백 (success: bool)
        """
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
                
                # 다운로드
                self._log("업데이트 다운로드 시작...")
                zip_path = self.downloader.download(download_url, progress_callback)
                
                if not zip_path:
                    self._log_error("다운로드 실패")
                    if completion_callback:
                        completion_callback(False)
                    return
                
                self._log("다운로드 완료, 설치 시작...")
                
                # 설치
                success = UpdateInstaller.install_update(zip_path, restart=True, logger=self.main_app)
                
                if completion_callback:
                    completion_callback(success)
                    
            except Exception as e:
                self._log_error(f"업데이트 다운로드/설치 오류: {e}")
                import traceback
                self._log_error(f"상세 오류: {traceback.format_exc()}")
                if completion_callback:
                    completion_callback(False)
        
        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()


# ==================== 단독 실행 테스트 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("BundleEditor 업데이트 테스트")
    print("=" * 60)
    print()
    
    # 업데이트 체커 생성
    updater = AutoUpdater()
    
    # 버전 체크
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
    
    # 사용자 확인
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
    print()  # 줄바꿈
    
    if not zip_path:
        print("❌ 다운로드 실패")
        sys.exit(1)
    
    print("✅ 다운로드 완료")
    print()
    print("[3] 설치 시작...")
    
    # 설치 (테스트 모드: restart=False)
    success = UpdateInstaller.install_update(zip_path, restart=False)
    
    if success:
        print()
        print("=" * 60)
        print("✅ 업데이트 테스트 완료!")
        print("=" * 60)
        print()
        print("배치 스크립트가 백그라운드에서 실행 중입니다.")
        print("실제 파일 교체는 BundleEditor.exe 종료 후 진행됩니다.")
    else:
        print("❌ 설치 실패")
        sys.exit(1)
