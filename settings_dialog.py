"""
Settings 다이얼로그
- Tesseract 경로 설정
- Debug 모드 on/off
- 기타 앱 설정들
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import os
import json
import webbrowser
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QCheckBox, QFileDialog, QMessageBox, QGroupBox,
                             QDialogButtonBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPalette
import pytesseract
from utils import set_pytesseract_cmd


class SettingsDialog(QDialog):
    """Settings 다이얼로그"""
    
    # 설정 변경 시그널
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        # 설정 데이터
        self.config_file = "config.json"
        self.settings = self.load_settings()
        
        self.init_ui()
        self.load_current_settings()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # Tesseract 설정 그룹
        tesseract_group = self.create_tesseract_group()
        layout.addWidget(tesseract_group)
        
        # Debug 설정 그룹
        debug_group = self.create_debug_group()
        layout.addWidget(debug_group)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def create_tesseract_group(self):
        """Tesseract 설정 그룹 생성"""
        group = QGroupBox("🔍 Tesseract OCR Settings")
        layout = QVBoxLayout()
        
        # 설명
        desc_label = QLabel("Tesseract 실행 파일 경로를 설정하세요.")
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # 경로 입력 섹션
        path_layout = QHBoxLayout()
        
        # 상태 아이콘
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(20, 20)
        self.status_icon.setAlignment(Qt.AlignCenter)
        path_layout.addWidget(self.status_icon)
        
        # 경로 입력 필드
        self.tesseract_path_input = QLineEdit()
        self.tesseract_path_input.setPlaceholderText("C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        self.tesseract_path_input.textChanged.connect(self.validate_tesseract_path)
        path_layout.addWidget(self.tesseract_path_input)
        
        # 파일 선택 버튼
        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self.browse_tesseract_path)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # 다운로드 버튼들
        download_layout = QHBoxLayout()
        
        download_official_btn = QPushButton("📥 Tesseract 공식 다운로드")
        download_official_btn.clicked.connect(self.download_tesseract_official)
        download_layout.addWidget(download_official_btn)
        
        download_github_btn = QPushButton("🔗 GitHub 릴리스")
        download_github_btn.clicked.connect(self.download_tesseract_github)
        download_layout.addWidget(download_github_btn)
        
        layout.addLayout(download_layout)
        
        # 현재 상태 표시
        self.tesseract_status_label = QLabel()
        self.tesseract_status_label.setStyleSheet("font-size: 11px; padding: 5px;")
        layout.addWidget(self.tesseract_status_label)
        
        group.setLayout(layout)
        return group
    
    def create_debug_group(self):
        """Debug 설정 그룹 생성"""
        group = QGroupBox("🐛 Debug Settings")
        layout = QVBoxLayout()
        
        # Debug 모드 체크박스
        self.debug_mode_checkbox = QCheckBox("Debug 모드 활성화")
        self.debug_mode_checkbox.setToolTip("[DEBUG] 태그가 포함된 로그 메시지를 표시합니다.")
        self.debug_mode_checkbox.toggled.connect(self.on_debug_mode_changed)
        layout.addWidget(self.debug_mode_checkbox)
        
        # 설명
        desc_label = QLabel("Debug 모드를 활성화하면 상세한 로그 정보가 표시됩니다.")
        desc_label.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px;")
        layout.addWidget(desc_label)
        
        group.setLayout(layout)
        return group
    
    def load_settings(self):
        """설정 파일에서 설정 로드"""
        default_settings = {
            "tesseract_path": "",
            "debug_mode": False
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기존 설정과 병합
                    settings = default_settings.copy()
                    if isinstance(config, dict):
                        settings.update(config)
                    return settings
        except Exception as e:
            print(f"설정 로드 중 오류: {e}")
        
        return default_settings
    
    def save_settings(self):
        """설정을 파일에 저장"""
        try:
            # 기존 config.json이 있다면 로드하여 병합
            existing_config = {}
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                        if not isinstance(existing_config, dict):
                            existing_config = {}
                except:
                    existing_config = {}
            
            # 현재 설정으로 업데이트
            existing_config.update(self.settings)
            
            # 파일에 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=2, ensure_ascii=False)
            
            print(f"설정이 저장되었습니다: {self.settings}")
            return True
        except Exception as e:
            print(f"설정 저장 중 오류: {e}")
            QMessageBox.warning(self, "오류", f"설정을 저장할 수 없습니다.\n\n{e}")
            return False
    
    def load_current_settings(self):
        """현재 설정을 UI에 반영"""
        # Tesseract 경로
        tesseract_path = self.settings.get("tesseract_path", "")
        self.tesseract_path_input.setText(tesseract_path)
        
        # Debug 모드
        debug_mode = self.settings.get("debug_mode", False)
        self.debug_mode_checkbox.setChecked(debug_mode)
        
        # 경로 유효성 검사
        self.validate_tesseract_path()
    
    def validate_tesseract_path(self):
        """Tesseract 경로 유효성 검사 및 시각적 피드백"""
        path = self.tesseract_path_input.text().strip()
        
        if not path:
            self.update_tesseract_status("경로가 설정되지 않았습니다.", "warning")
            return False
        
        if not os.path.exists(path):
            self.update_tesseract_status("파일이 존재하지 않습니다.", "error")
            return False
        
        if not path.lower().endswith('tesseract.exe'):
            self.update_tesseract_status("tesseract.exe 파일이 아닙니다.", "error")
            return False
        
        # Tesseract 실행 테스트
        try:
            import subprocess
            result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_info = result.stdout.split('\n')[0] if result.stdout else "알 수 없는 버전"
                self.update_tesseract_status(f"✅ 유효한 경로입니다. ({version_info})", "success")
                return True
            else:
                self.update_tesseract_status("실행할 수 없는 파일입니다.", "error")
                return False
        except Exception as e:
            self.update_tesseract_status(f"테스트 실패: {str(e)[:50]}...", "error")
            return False
    
    def update_tesseract_status(self, message, status_type):
        """Tesseract 상태 업데이트"""
        colors = {
            "success": ("#4CAF50", "✅"),
            "warning": ("#FF9800", "⚠️"),
            "error": ("#F44336", "❌")
        }
        
        color, icon = colors.get(status_type, ("#666", "ℹ️"))
        
        # 아이콘 업데이트
        self.status_icon.setText(icon)
        
        # 상태 메시지 업데이트
        self.tesseract_status_label.setText(message)
        self.tesseract_status_label.setStyleSheet(f"color: {color}; font-size: 11px; padding: 5px;")
    
    def browse_tesseract_path(self):
        """Tesseract 파일 찾아보기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Tesseract 실행 파일 선택", 
            "C:\\Program Files\\Tesseract-OCR\\", 
            "Executable Files (*.exe);;All Files (*)"
        )
        
        if file_path:
            self.tesseract_path_input.setText(file_path)
    
    def download_tesseract_official(self):
        """Tesseract 공식 사이트에서 다운로드"""
        url = "https://tesseract-ocr.github.io/tessdoc/Downloads.html"
        try:
            webbrowser.open(url)
            QMessageBox.information(
                self,
                "다운로드",
                "Tesseract 공식 다운로드 페이지를 열었습니다.\n\n"
                "Windows Installer를 다운로드하여 설치한 후,\n"
                "설치 경로를 다시 설정해주세요."
            )
        except Exception as e:
            QMessageBox.warning(self, "오류", f"웹페이지를 열 수 없습니다.\n\n{e}")
    
    def download_tesseract_github(self):
        """Tesseract GitHub 릴리스 페이지 열기"""
        url = "https://github.com/UB-Mannheim/tesseract/wiki"
        try:
            webbrowser.open(url)
            QMessageBox.information(
                self,
                "다운로드",
                "Tesseract Windows 빌드 페이지를 열었습니다.\n\n"
                "최신 Windows Installer를 다운로드하여 설치하세요."
            )
        except Exception as e:
            QMessageBox.warning(self, "오류", f"웹페이지를 열 수 없습니다.\n\n{e}")
    
    def on_debug_mode_changed(self, checked):
        """Debug 모드 변경 시 호출"""
        self.settings["debug_mode"] = checked
        # 즉시 저장
        self.save_settings()
        
        # 메인 앱에 변경 사항 알림
        self.settings_changed.emit()
        
        print(f"Debug 모드가 {'활성화' if checked else '비활성화'}되었습니다.")
    
    def accept_settings(self):
        """설정 적용"""
        # Tesseract 경로 검증
        tesseract_path = self.tesseract_path_input.text().strip()
        
        if tesseract_path and not self.validate_tesseract_path():
            reply = QMessageBox.question(
                self,
                "경로 오류",
                "Tesseract 경로가 유효하지 않습니다.\n그래도 저장하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # 설정 업데이트
        self.settings["tesseract_path"] = tesseract_path
        self.settings["debug_mode"] = self.debug_mode_checkbox.isChecked()
        
        # 설정 저장
        if self.save_settings():
            # Tesseract 경로 적용
            if tesseract_path:
                if set_pytesseract_cmd(tesseract_path):
                    print(f"Tesseract 경로가 설정되었습니다: {tesseract_path}")
                else:
                    print(f"Tesseract 경로 설정 실패: {tesseract_path}")
            
            # 메인 앱에 변경 사항 알림
            self.settings_changed.emit()
            
            QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
            self.accept()
        else:
            QMessageBox.warning(self, "저장 실패", "설정을 저장할 수 없습니다.")


if __name__ == '__main__':
    # 테스트 코드
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.show()
    sys.exit(app.exec_())
