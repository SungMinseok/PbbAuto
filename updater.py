"""
자동 업데이트 시스템 (리팩토링 버전)
GitHub Releases를 통한 자동 업데이트 관리

9단계 프로세스:
[1] 서버에서 최신 버전 조회
[2] 로컬 버전 비교
[3] (필요 시) 사용자 승인
[4] 새 버전 다운로드 (현재 exe파일 있는 경로로, zip 압축해제 포함)
[5] 실행 중인 앱 종료
[6] 파일 교체 / 설치
[7] 무결성 검증
[8] 새 앱 실행
[9] 임시 파일 정리
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import json
import os
import sys
import requests
import subprocess
import shutil
import zipfile
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from packaging import version
import threading


class UpdateChecker:
    """[1~2] 버전 체크 및 업데이트 확인"""
    
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
        [1~2] 서버에서 최신 버전 조회 및 로컬 버전 비교
        
        Returns:
            (has_update, update_info, error_message)
        """
        try:
            self._log("[1] 서버에서 최신 버전 조회 중...")
            
            # GitHub API로 최신 릴리스 정보 가져오기
            api_url = "https://api.github.com/repos/SungMinseok/PbbAuto/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data['tag_name'].lstrip('v')
            
            self._log(f"[2] 로컬 버전 비교")
            self._log(f"    현재 버전: {self.current_version}")
            self._log(f"    최신 버전: {latest_version}")
            
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


class UpdateInstaller:
    """[4~9] 업데이트 다운로드 및 설치"""
    
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
    
    def download_and_install(self, download_url: str, progress_callback=None) -> bool:
        """
        [4~9] 전체 업데이트 프로세스 실행
        
        Args:
            download_url: 다운로드 URL
            progress_callback: 진행률 콜백 (received, total)
            
        Returns:
            성공 여부
        """
        try:
            # [4] 새 버전 다운로드 (현재 exe 경로로)
            self._log("[4] 새 버전 다운로드 중...")
            
            # 현재 실행 파일 경로 확인
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
                current_dir = os.path.dirname(current_exe)
            else:
                self._log_error("개발 모드에서는 업데이트를 설치할 수 없습니다.")
                return False
            
            self._log(f"    현재 실행 파일: {current_exe}")
            self._log(f"    설치 디렉토리: {current_dir}")
            
            # 다운로드 경로: 현재 exe 경로에 임시 폴더 생성
            temp_download_dir = os.path.join(current_dir, "_update_temp")
            os.makedirs(temp_download_dir, exist_ok=True)
            
            zip_path = os.path.join(temp_download_dir, "update.zip")
            self._log(f"    다운로드 위치: {zip_path}")
            
            # ZIP 파일 다운로드
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancel_flag:
                        self._log("다운로드 취소됨")
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            self._log(f"✅ 다운로드 완료 ({downloaded} bytes)")
            
            # ZIP 압축 해제
            extract_dir = os.path.join(temp_download_dir, "extracted")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            self._log("    ZIP 파일 압축 해제 중...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 압축 해제된 파일 목록
            extracted_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, extract_dir)
                    extracted_files.append((src_path, rel_path))
            
            self._log(f"✅ 압축 해제 완료 ({len(extracted_files)} 파일)")
            
            # [5] 실행 중인 앱 종료 준비
            self._log("[5] 앱 종료 및 업데이트 설치 준비...")
            
            # [6] 파일 교체 배치 스크립트 생성
            self._log("[6] 파일 교체 스크립트 생성 중...")
            
            bat_script = os.path.join(temp_download_dir, "install.bat")
            
            with open(bat_script, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 > nul\n')
                f.write('echo ========================================\n')
                f.write('echo BundleEditor 업데이트 설치\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                f.write('echo [5] 실행 중인 앱 종료 대기 중...\n')
                f.write('timeout /t 3 /nobreak > nul\n')
                f.write('echo.\n')
                
                # [6] 파일 교체
                f.write('echo [6] 파일 교체 중...\n')
                for src_path, rel_path in extracted_files:
                    dst_path = os.path.join(current_dir, rel_path)
                    dst_dir = os.path.dirname(dst_path)
                    
                    # 디렉토리 생성
                    if dst_dir and dst_dir != current_dir:
                        f.write(f'if not exist "{dst_dir}" mkdir "{dst_dir}"\n')
                    
                    # 기존 파일 백업 (exe 파일의 경우)
                    if dst_path.lower().endswith('.exe'):
                        f.write(f'if exist "{dst_path}" move /y "{dst_path}" "{dst_path}.bak"\n')
                    
                    # 새 파일 복사
                    f.write(f'copy /y "{src_path}" "{dst_path}"\n')
                    
                    # [7] 무결성 검증 (exe 파일의 경우)
                    if dst_path.lower().endswith('.exe'):
                        f.write(f'if not exist "{dst_path}" (\n')
                        f.write(f'    echo [7] 파일 복사 실패: {rel_path}\n')
                        f.write(f'    echo     백업에서 복구 중...\n')
                        f.write(f'    if exist "{dst_path}.bak" move /y "{dst_path}.bak" "{dst_path}"\n')
                        f.write(f'    echo     업데이트 실패!\n')
                        f.write(f'    pause\n')
                        f.write(f'    exit /b 1\n')
                        f.write(f')\n')
                        f.write(f'echo     ✓ {rel_path} 복사 완료\n')
                
                f.write('echo.\n')
                f.write('echo [7] 무결성 검증 완료\n')
                f.write('echo.\n')
                
                # [8] 새 앱 실행
                f.write('echo [8] 새 버전 실행 중...\n')
                f.write(f'start "" "{current_exe}"\n')
                f.write('timeout /t 2 /nobreak > nul\n')
                f.write('echo.\n')
                
                # [9] 임시 파일 정리
                f.write('echo [9] 임시 파일 정리 중...\n')
                f.write(f'cd /d "{current_dir}"\n')
                
                # .bak 파일 삭제
                for src_path, rel_path in extracted_files:
                    if rel_path.lower().endswith('.exe'):
                        dst_path = os.path.join(current_dir, rel_path)
                        f.write(f'if exist "{dst_path}.bak" del /f /q "{dst_path}.bak"\n')
                
                # 임시 폴더 삭제
                f.write(f'rmdir /s /q "{temp_download_dir}"\n')
                f.write('echo.\n')
                f.write('echo ========================================\n')
                f.write('echo 업데이트 완료!\n')
                f.write('echo ========================================\n')
                f.write('timeout /t 2 /nobreak > nul\n')
                f.write('\n')
                f.write('REM 자기 자신 삭제\n')
                f.write('(goto) 2>nul & del "%~f0"\n')
            
            self._log(f"✅ 설치 스크립트 생성 완료: {bat_script}")
            
            # 배치 스크립트 실행
            self._log("업데이트 스크립트 실행 중...")
            subprocess.Popen(
                [bat_script],
                cwd=current_dir,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
            )
            
            # 현재 앱 종료
            self._log("3초 후 앱을 종료합니다...")
            time.sleep(3)
            sys.exit(0)
            
        except Exception as e:
            self._log_error(f"업데이트 설치 실패: {e}")
            import traceback
            self._log_error(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def cancel(self):
        """다운로드 취소"""
        self.cancel_flag = True


class AutoUpdater:
    """통합 자동 업데이트 관리자"""
    
    def __init__(self, version_file: str = "version.json"):
        self.checker = UpdateChecker(version_file)
        self.installer = UpdateInstaller()
        self.update_available = False
        self.latest_info = None
        self.main_app = None
    
    def set_main_app(self, main_app):
        """main app 참조 설정"""
        self.main_app = main_app
        self.checker.set_main_app(main_app)
        self.installer.set_main_app(main_app)
    
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
        [1~3] 비동기로 업데이트 확인
        
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
        [4~9] 업데이트 다운로드 및 설치
        
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
                
                # [4~9] 전체 프로세스 실행
                success = self.installer.download_and_install(download_url, progress_callback)
                
                # 참고: sys.exit(0)가 호출되므로 여기에 도달하지 않음
                if completion_callback:
                    completion_callback(success)
                    
            except Exception as e:
                self._log_error(f"업데이트 설치 오류: {e}")
                import traceback
                self._log_error(f"상세 오류: {traceback.format_exc()}")
                if completion_callback:
                    completion_callback(False)
        
        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()
