"""
업데이트 관련 다이얼로그
- 업데이트 알림
- 다운로드 진행률
- About 다이얼로그
"""

# 로그 설정을 가장 먼저 import
import logger_setup

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QProgressBar, QTextEdit, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QMetaObject, Q_ARG
from PyQt5.QtGui import QFont
import json
import os


class UpdateNotificationDialog(QDialog):
    """업데이트 알림 다이얼로그"""
    
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        # update_info 안전성 검사
        if not update_info or not isinstance(update_info, dict):
            self.update_info = {
                'version': '알 수 없음',
                'name': '업데이트',
                'body': '업데이트 정보를 불러올 수 없습니다.',
                'published_at': '',
                'assets': []
            }
        else:
            self.update_info = update_info
        
        self.setWindowTitle("업데이트 사용 가능")
        self.resize(500, 400)
        try:
            self.init_ui()
        except Exception as e:
            print(f"UpdateNotificationDialog UI 초기화 오류: {e}")
            # 기본 UI로 대체
            self._init_fallback_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 제목
        title_label = QLabel("🎉 새로운 버전이 출시되었습니다!")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 버전 정보
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("새 버전:"))
        version_label = QLabel(self.update_info.get('version', '알 수 없음'))
        version_label.setStyleSheet("color: #0066CC; font-weight: bold;")
        version_layout.addWidget(version_label)
        version_layout.addStretch()
        layout.addLayout(version_layout)
        
        # 발행일
        if 'published_at' in self.update_info:
            date_str = self.update_info['published_at'][:10]  # YYYY-MM-DD
            layout.addWidget(QLabel(f"발행일: {date_str}"))
        
        # 변경사항
        layout.addWidget(QLabel("\n📝 변경사항:"))
        
        changelog = QTextEdit()
        changelog.setReadOnly(True)
        changelog.setPlainText(self.update_info.get('body', '변경사항이 없습니다.'))
        changelog.setMaximumHeight(200)
        layout.addWidget(changelog)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        self.update_now_btn = QPushButton("지금 업데이트")
        self.update_now_btn.setStyleSheet("QPushButton { background-color: #0066CC; color: white; padding: 8px 16px; }")
        self.update_now_btn.clicked.connect(self.accept)
        
        self.later_btn = QPushButton("나중에")
        self.later_btn.clicked.connect(self.reject)
        
        self.skip_btn = QPushButton("이 버전 건너뛰기")
        self.skip_btn.clicked.connect(self.skip_version)
        
        button_layout.addWidget(self.later_btn)
        button_layout.addWidget(self.skip_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.update_now_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def skip_version(self):
        """이 버전 건너뛰기"""
        # TODO: 건너뛴 버전을 설정 파일에 저장
        self.done(2)  # 2 = Skip
    
    def _init_fallback_ui(self):
        """기본 UI (오류 발생 시 대체용)"""
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("업데이트 정보"))
        layout.addWidget(QLabel(f"버전: {self.update_info.get('version', '알 수 없음')}"))
        
        # 기본 버튼
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn = QPushButton("확인")
        ok_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)


class DownloadProgressDialog(QDialog):
    """다운로드 진행률 다이얼로그 (스레드 안전)"""
    
    # 시그널 정의 (스레드 간 통신용)
    progress_updated = pyqtSignal(int, int)  # received, total
    download_completed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업데이트 다운로드 중")
        self.resize(400, 150)
        
        # 모달 설정 및 최상단 표시
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        self.init_ui()
        self.cancelled = False
        
        # 시그널 연결 (메인 스레드에서 처리)
        self.progress_updated.connect(self._update_progress_safe)
        self.download_completed.connect(self._download_complete_safe)
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 상태 메시지
        self.status_label = QLabel("업데이트 파일 다운로드 중...")
        layout.addWidget(self.status_label)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 크기 정보
        self.size_label = QLabel("0 MB / 0 MB")
        self.size_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.size_label)
        
        # 취소 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_progress(self, received, total):
        """
        진행률 업데이트 (스레드 안전 - 시그널 발생)
        
        Args:
            received: 받은 바이트
            total: 전체 바이트
        """
        # 시그널을 통해 메인 스레드에서 처리하도록 함
        self.progress_updated.emit(received, total)
    
    def _update_progress_safe(self, received, total):
        """
        실제 진행률 업데이트 (메인 스레드에서 실행)
        
        Args:
            received: 받은 바이트
            total: 전체 바이트
        """
        if total > 0:
            percentage = int((received / total) * 100)
            self.progress_bar.setValue(percentage)
            
            received_mb = received / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.size_label.setText(f"{received_mb:.1f} MB / {total_mb:.1f} MB")
    
    def cancel_download(self):
        """다운로드 취소"""
        reply = QMessageBox.question(
            self, 
            "다운로드 취소", 
            "다운로드를 취소하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.cancelled = True
            self.reject()
    
    def download_complete(self):
        """다운로드 완료 (스레드 안전 - 시그널 발생)"""
        # 시그널을 통해 메인 스레드에서 처리하도록 함
        self.download_completed.emit()
    
    def _download_complete_safe(self):
        """실제 다운로드 완료 처리 (메인 스레드에서 실행)"""
        self.status_label.setText("다운로드 완료! 설치 중...")
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(False)


class AboutDialog(QDialog):
    """About 다이얼로그 - 버전 정보 및 업데이트 체크"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bundle Editor 정보")
        self.resize(450, 350)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 앱 이름 및 아이콘
        title_label = QLabel("🎮 Bundle Editor")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("자동화 테스트 도구")
        subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # 버전 정보 로드
        version_info = self._load_version_info()
        
        # 현재 버전
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("버전:"))
        version_label = QLabel(version_info.get('version', '알 수 없음'))
        version_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(version_label)
        version_layout.addStretch()
        layout.addLayout(version_layout)
        
        # 빌드 날짜
        build_layout = QHBoxLayout()
        build_layout.addWidget(QLabel("빌드 날짜:"))
        build_label = QLabel(version_info.get('build_date', '알 수 없음'))
        build_layout.addWidget(build_label)
        build_layout.addStretch()
        layout.addLayout(build_layout)
        
        layout.addSpacing(10)
        
        # 변경 이력
        layout.addWidget(QLabel("📝 최근 변경사항:"))
        
        changelog_text = QTextEdit()
        changelog_text.setReadOnly(True)
        changelog_text.setMaximumHeight(150)
        
        # version.json에서 모든 변경사항 표시, 최근 것부터 표시, 빌드명 개행 변경사항 형식
        changelog = version_info.get('changelog', [])
        if changelog:
            # 최신 항목이 먼저 나오도록 역순 정렬
            changelog_texts = []
            for item in sorted(changelog, key=lambda x: x.get('date', ''), reverse=True):
                build_name = item.get('version', 'Unknown')
                changes = item.get('changes', [])
                # 각 변경사항 앞에 '• ' 붙이기
                formatted_changes = "\n".join(f"• {change}" for change in changes)
                changelog_texts.append(f"{build_name}\n{formatted_changes}")
            # 항목 간에는 빈 줄로 구분
            changelog_text.setPlainText("\n\n".join(changelog_texts))
        else:
            changelog_text.setPlainText("변경사항이 없습니다.")

        layout.addWidget(changelog_text)
        
        # 업데이트 확인 버튼
        update_btn = QPushButton("업데이트 확인")
        update_btn.clicked.connect(self.check_updates)
        layout.addWidget(update_btn)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _load_version_info(self):
        """version.json 파일에서 버전 정보 로드"""
        try:
            version_file = "version.json"
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"버전 정보 로드 실패: {e}")
        
        return {
            'version': '알 수 없음',
            'build_date': '알 수 없음',
            'changelog': []
        }
    
    def check_updates(self):
        """업데이트 확인 - 부모 위젯의 메서드 호출"""
        try:
            if self.parent() and hasattr(self.parent(), 'check_for_updates'):
                # About 다이얼로그 닫기
                self.accept()
                
                # 부모 에서 업데이트 확인 실행 (부모에서 팝업 처리)
                self.parent().check_for_updates()
                
            else:
                QMessageBox.information(
                    self,
                    "업데이트 확인",
                    "업데이트를 확인하려면 메뉴에서 '업데이트 확인'을 선택하세요."
                )
        except Exception as e:
            print(f"About 다이얼로그에서 업데이트 확인 중 오류: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"업데이트 확인 중 오류가 발생했습니다.\n\n{e}"
            )


class UpdateSettingsDialog(QDialog):
    """업데이트 설정 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업데이트 설정")
        self.resize(400, 200)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # TODO: 설정 옵션 추가
        # - 자동 업데이트 확인 ON/OFF
        # - 업데이트 채널 선택 (Stable/Beta)
        # - 시작 시 자동 확인
        
        layout.addWidget(QLabel("업데이트 설정 (준비 중)"))
        
        # 버튼
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)


if __name__ == '__main__':
    # 테스트 코드
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 테스트: 업데이트 알림
    test_info = {
        'version': '1.1.0',
        'published_at': '2025-10-17T12:00:00Z',
        'body': '• CommandPopup 개선\n• wait 타이머 추가\n• 버그 수정'
    }
    
    # dialog = UpdateNotificationDialog(test_info)
    # dialog = DownloadProgressDialog()
    dialog = AboutDialog()
    
    dialog.exec_()
    
    sys.exit(0)

