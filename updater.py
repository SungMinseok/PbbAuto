"""
자동 업데이트 시스템 (리팩토링 버전)
GitHub Releases를 통한 자동 업데이트 관리

핵심 전략:
1. Python 코드에서 직접 ZIP 다운로드 및 압축 해제
2. 현재 실행 파일 종료 후 파일 교체
3. 앱 재시작 후 임시 파일 정리
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
import zipfile
import time
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
            self._log("업데이트 확인 중...")
            
            # GitHub API로 최신 릴리스 정보 가져오기
            api_url = "https://api.github.com/repos/SungMinseok/PbbAuto/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data['tag_name'].lstrip('v')
            
            self._log(f"현재 버전: {self.current_version}")
            self._log(f"최신 버전: {latest_version}")
            
            # 버전 비교
            if version.parse(latest_version) > version.parse(self.current_version):
                # 다운로드 URL 찾기
                download_url = None
                for asset in release_data.get('assets', []):
                    if asset['name'].endswith('.zip'):
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    return False, None, "다운로드 가능한 파일이 없습니다."
                
                update_info = {
                    'version': latest_version,
                    'download_url': download_url,
                    'release_notes': release_data.get('body', ''),
                    'published_at': release_data.get('published_at', '')
                }
                
                self.latest_info = update_info
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
    """업데이트 파일 다운로드 클래스"""
    
    def __init__(self):
        self.main_app = None  # main app 참조
        self.cancel_flag = False
    
    def set_main_app(self, main_app):
        """main app 참조 설정"""
        self.main_app = main_app
    
    def _log(self, message):
        """로그 메시지 출력"""
        if self.main_app and hasattr(self.main_app, 'log'):
            self.main_app.log(message)
        else:
            print(message)
    
    def _log_error(self, message):
        """에러 로그 메시지 출력"""
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
            download_path = os.path.join(temp_dir, "BundleEditor.zip")
            
            self._log(f"다운로드 시작: {url}")
            self._log(f"저장 위치: {download_path}")
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            self._log(f"총 다운로드 크기: {total_size} bytes")
            
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
    """업데이트 설치 클래스 (새로운 간단한 방식)"""
    
    @staticmethod
    def install_update(zip_path: str, logger=None) -> bool:
        """
        업데이트 설치
        
        Args:
            zip_path: 다운로드된 ZIP 파일 경로
            logger: 로거 객체 (선택)
            
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
            _log(f"ZIP 파일: {zip_path}")
            
            # 1. ZIP 파일 존재 확인
            if not os.path.exists(zip_path):
                _log_error(f"ZIP 파일이 존재하지 않습니다: {zip_path}")
                return False
            
            # 2. 현재 실행 파일 확인
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                _log("개발 모드에서는 업데이트를 설치할 수 없습니다.")
                return False
            
            current_dir = os.path.dirname(current_exe)
            _log(f"현재 실행 파일: {current_exe}")
            _log(f"설치 디렉토리: {current_dir}")
            
            # 3. 임시 압축 해제 디렉토리 생성
            temp_extract_dir = os.path.join(tempfile.gettempdir(), 'update_extract')
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir)
            _log(f"압축 해제 디렉토리: {temp_extract_dir}")
            
            # 4. ZIP 파일 압축 해제
            _log("ZIP 파일 압축 해제 중...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            _log("✅ 압축 해제 완료")
            
            # 5. 압축 해제된 파일 목록 확인
            extracted_files = []
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, temp_extract_dir)
                    extracted_files.append(rel_path)
            
            _log(f"압축 해제된 파일 수: {len(extracted_files)}")
            
            # 6. 현재 앱 종료 준비 (배치 스크립트 생성)
            bat_script = os.path.join(tempfile.gettempdir(), 'update_install.bat')
            
            with open(bat_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 > nul\n')
                f.write('echo 업데이트 설치 중...\n')
                f.write('timeout /t 3 /nobreak > nul\n\n')
                
                # 파일 복사
                for rel_path in extracted_files:
                    src = os.path.join(temp_extract_dir, rel_path)
                    dst = os.path.join(current_dir, rel_path)
                    dst_dir = os.path.dirname(dst)
                    
                    # 디렉토리 생성
                    if dst_dir and dst_dir != current_dir:
                        f.write(f'if not exist "{dst_dir}" mkdir "{dst_dir}"\n')
                    
                    # 파일 복사
                    f.write(f'copy /y "{src}" "{dst}"\n')
                
                f.write('\n')
                f.write('echo 임시 파일 정리 중...\n')
                f.write(f'rmdir /s /q "{temp_extract_dir}"\n')
                f.write(f'del /f /q "{zip_path}"\n')
                f.write('\n')
                f.write('echo 업데이트 완료! 앱을 재시작합니다...\n')
                f.write(f'start "" "{current_exe}"\n')
                f.write('\n')
                f.write('REM 자기 자신 삭제\n')
                f.write('del "%~f0"\n')
            
            _log(f"업데이트 스크립트 생성됨: {bat_script}")
            
            # 7. 배치 스크립트 실행 및 현재 앱 종료
            _log("업데이트 스크립트 실행...")
            subprocess.Popen([bat_script], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            _log("3초 후 앱을 종료하고 업데이트를 설치합니다...")
            time.sleep(3)
            
            # 앱 종료
            sys.exit(0)
            
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
        def download_thread():
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
                success = UpdateInstaller.install_update(zip_path, self.main_app)
                
                if completion_callback:
                    completion_callback(success)
                    
            except Exception as e:
                self._log_error(f"업데이트 다운로드/설치 오류: {e}")
                import traceback
                self._log_error(f"상세 오류: {traceback.format_exc()}")
                if completion_callback:
                    completion_callback(False)
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
