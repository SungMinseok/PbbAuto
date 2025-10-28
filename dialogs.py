"""
개선된 다이얼로그 - 명령어 레지스트리 사용
기존 535줄 → 대폭 축소! 🎉
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import time
import pyautogui as pag
import pygetwindow as gw
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QLineEdit, QSpinBox, QDialogButtonBox, QWidget, 
                             QListWidget, QStackedWidget, QMessageBox, QListWidgetItem, QMenu, QAction,
                             QApplication)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from command_registry import get_all_commands, get_command_names
from pynput import mouse, keyboard


class CommandPopup(QDialog):
    """명령어 실행 진행상황을 보여주는 팝업 (작업표시줄 스타일)
    
    개선사항:
    - 모든 정보를 한 줄로 압축 표시
    - 화면 하단에 작업표시줄처럼 배치
    - 매우 작고 컴팩트한 UI
    - 테스트 방해 최소화
    """
    
    def __init__(self, commands, parent=None):
        super().__init__(None)  # parent를 None으로 설정하여 독립적인 창으로 생성
        self.parent_widget = parent  # 참조만 저장 (중지 시그널 전달용)
        self.setWindowTitle("명령어 실행")
        
        # 항상 최상위에 표시, 독립적인 창으로 설정
        self.setWindowFlags(
            Qt.Window |  # 독립적인 윈도우
            Qt.WindowStaysOnTopHint |  # 항상 최상단
            Qt.FramelessWindowHint |  # 프레임 없음
            Qt.Tool  # 작업표시줄에 표시되지 않음
        )
        
        # 매우 작고 넓은 사이즈 (작업표시줄 스타일)
        self.resize(1200, 32)  # 넓고 낮은 창
        
        # 전체 명령어 목록 저장
        self.commands = commands
        self.total_count = len(commands)
        self.current_idx = 0
        self.stopped = False
        
        # UI 구성 - 모든 것을 한 줄에
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(8)
        
        # 한 줄로 모든 정보 표시
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 9pt; 
            color: #FFFFFF;
            background-color: rgba(40, 40, 40, 220);
            padding: 2px 8px;
            border-radius: 3px;
        """)
        self.layout.addWidget(self.status_label, 1)  # stretch factor 1
        
        # 중지 버튼 (작게)
        self.stop_btn = QPushButton("✕")
        self.stop_btn.clicked.connect(self.stop_execution)
        self.stop_btn.setFixedSize(24, 24)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF0000;
            }
        """)
        self.layout.addWidget(self.stop_btn)
        
        # 전체 배경 설정
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(40, 40, 40, 220);
                border: 1px solid rgba(80, 80, 80, 180);
                border-radius: 4px;
            }
        """)
        
        self.setLayout(self.layout)
        
        # 초기 표시 업데이트
        self._update_display()
        
        # 화면 하단 중앙에 위치
        self._move_to_bottom_center()
    
    def _move_to_bottom_center(self):
        """창을 화면 하단 중앙에 위치 (작업표시줄 위)"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 50  # 화면 하단에서 50px 위 (작업표시줄 위)
        self.move(x, y)
    
    def _update_display(self):
        """한 줄로 모든 정보 표시"""
        # 기본 형식: [3/10] ▶ 현재명령어 | 다음: 다음명령어
        
        if self.current_idx < self.total_count:
            current_cmd = self.commands[self.current_idx]
            
            # 현재 명령어 (최대 40자로 제한)
            if len(current_cmd) > 40:
                current_cmd = current_cmd[:37] + "..."
            
            # 다음 명령어
            next_part = ""
            if self.current_idx + 1 < self.total_count:
                next_cmd = self.commands[self.current_idx + 1]
                if len(next_cmd) > 30:
                    next_cmd = next_cmd[:27] + "..."
                next_part = f" │ 다음: {next_cmd}"
            
            status_text = f"[{self.current_idx + 1}/{self.total_count}] ▶ {current_cmd}{next_part}"
        else:
            status_text = "✅ 모든 명령어 완료!"
        
        self.status_label.setText(status_text)

    def mark_executed(self, idx):
        """명령어 실행 완료 표시 - 다음 명령어로 이동"""
        self.current_idx = idx + 1
        self._update_display()
    
    def update_timer(self, elapsed, total):
        """wait 명령어 타이머 업데이트 (한 줄 형식)
        
        Args:
            elapsed: 경과 시간 (초)
            total: 전체 대기 시간 (초)
        """
        remaining = total - elapsed
        
        if self.current_idx < self.total_count:
            current_cmd = self.commands[self.current_idx]
            
            # 현재 명령어 (최대 30자로 제한 - 타이머 공간 확보)
            if len(current_cmd) > 30:
                current_cmd = current_cmd[:27] + "..."
            
            # 다음 명령어
            next_part = ""
            if self.current_idx + 1 < self.total_count:
                next_cmd = self.commands[self.current_idx + 1]
                if len(next_cmd) > 25:
                    next_cmd = next_cmd[:22] + "..."
                next_part = f" │ 다음: {next_cmd}"
            
            # 타이머 추가
            timer_part = f" │ ⏱ {elapsed:.0f}s / {total:.0f}s"
            
            status_text = f"[{self.current_idx + 1}/{self.total_count}] ▶ {current_cmd}{next_part}{timer_part}"
            self.status_label.setText(status_text)

    def stop_execution(self):
        """실행 중지"""
        self.stopped = True
        # parent_widget의 stop_execution도 호출하여 완전한 중지
        if self.parent_widget and hasattr(self.parent_widget, 'stop_execution'):
            self.parent_widget.stop_execution()
        self.stopped = False
        self.close()
    
    def closeEvent(self, event):
        """창 닫기 이벤트 - x 버튼 클릭 시에도 실행 중지"""
        if not self.stopped:
            self.stop_execution()
        event.accept()


class AddCommandDialog(QDialog):
    """개선된 명령어 다이얼로그 - 레지스트리 기반 + description 표시"""
    
    def __init__(self, parent=None, initial=None):
        super().__init__(parent)
        self.setWindowTitle('Add/Edit Command')
        self.resize(560, 330)
        self.layout = QVBoxLayout()
        
        # 명령어 레지스트리에서 자동으로 가져오기
        self.commands = get_all_commands()
        self.command_names = get_command_names()

        # Action selector
        self.action_box = QComboBox()
        self.action_box.addItems(self.command_names)  # ← 자동으로 채워짐!

        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel('Action:'))
        action_layout.addWidget(self.action_box)
        self.layout.addLayout(action_layout)

        # Description label (추가)
        self.desc_label = QLabel("")
        self.layout.addWidget(self.desc_label)

        # Stacked widget - 각 명령어가 자체 UI 생성
        self.stack = QStackedWidget()
        self.ui_widgets = {}
        
        # 모든 명령어의 UI를 자동으로 생성
        for name, command in self.commands.items():
            ui_widget = command.create_ui_with_window_info()  # ← 윈도우 정보가 포함된 UI 생성!
            self.stack.addWidget(ui_widget)
            self.ui_widgets[name] = ui_widget

        self.layout.addWidget(self.stack)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        self.setLayout(self.layout)

        # connections
        self.action_box.currentIndexChanged.connect(self._on_action_changed)

        # description show (초기 표시)
        self._update_description(self.action_box.currentText())
        
        # 초기 윈도우 정보 설정
        current_action = self.action_box.currentText()
        cmd = self.commands.get(current_action)
        if cmd and hasattr(cmd, 'initialize_window_info'):
            cmd.initialize_window_info()

        # 초기 명령어 파싱
        if initial:
            self._parse_initial_command(initial)

    def _on_action_changed(self, index):
        """액션 변경 시 UI 스택 및 description 변경"""
        self.stack.setCurrentIndex(index)
        action = self.action_box.itemText(index)
        self._update_description(action)
        
        # 윈도우 정보 초기화
        cmd = self.commands.get(action)
        if cmd and hasattr(cmd, 'initialize_window_info'):
            cmd.initialize_window_info()

    def _update_description(self, action_name):
        """description 라벨 업데이트"""
        cmd = self.commands.get(action_name)
        if cmd and hasattr(cmd, 'description'):
            desc = cmd.description
            self.desc_label.setText(f"Description: {desc}")
        else:
            self.desc_label.setText("")
    
    def _parse_initial_command(self, initial_command):
        """기존 명령어 파싱 - 자동화됨!"""
        parts = initial_command.split()
        if not parts:
            return
            
        action = parts[0]
        # 대소문자 구분 없이 명령어 찾기
        found_command = None
        for cmd_name in self.commands.keys():
            if cmd_name.lower() == action.lower():
                found_command = cmd_name
                break
        
        if found_command:
            # 액션 설정
            index = self.command_names.index(found_command)
            self.action_box.setCurrentIndex(index)
            
            # 파라미터 파싱 및 UI 설정
            command = self.commands[found_command]
            params = command.parse_params(parts[1:])  # ← 자동 파싱!
            command.set_ui_values(params)  # ← 자동 UI 설정!

    def get_command(self):
        """현재 명령어 문자열 반환 - 자동화됨!"""
        current_action = self.action_box.currentText()
        command = self.commands.get(current_action)
        if command:
            return command.get_command_string()  # ← 자동 생성!
        return current_action


class RecorderThread(QThread):
    """마우스/키보드 이벤트 녹화 스레드"""
    
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(list)  # 녹화된 이벤트 리스트 전달
    
    def __init__(self):
        super().__init__()
        self.events = []
        self.recording = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.start_time = None
        
    def run(self):
        """녹화 시작"""
        self.events = []
        self.recording = True
        self.start_time = time.time()
        
        # 마우스 리스너
        def on_click(x, y, button, pressed):
            if not self.recording:
                return False
            if pressed:  # 눌렀을 때만 기록
                elapsed = time.time() - self.start_time
                self.events.append({
                    'type': 'click',
                    'x': x,
                    'y': y,
                    'button': str(button),
                    'time': elapsed
                })
        
        # 키보드 리스너
        def on_press(key):
            if not self.recording:
                return False
            
            # F11 키를 눌렀을 때 녹화 종료
            try:
                if key == keyboard.Key.f11:
                    self.stop_recording()
                    return False
            except AttributeError:
                pass
            
            # F11 키는 녹화하지 않음
            try:
                if key == keyboard.Key.f11:
                    return
            except AttributeError:
                pass
            
            # 일반 키 입력 기록
            elapsed = time.time() - self.start_time
            try:
                # 일반 문자 키
                key_name = key.char if hasattr(key, 'char') else str(key)
            except AttributeError:
                # 특수 키 (Enter, Shift 등)
                key_name = str(key).replace('Key.', '')
            
            self.events.append({
                'type': 'press',
                'key': key_name,
                'time': elapsed
            })
        
        # 리스너 시작
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
        self.recording_started.emit()
        
        # 리스너가 종료될 때까지 대기
        self.keyboard_listener.join()
        self.mouse_listener.stop()
        
        # 녹화 완료
        self.recording_stopped.emit(self.events)
    
    def stop_recording(self):
        """녹화 종료"""
        self.recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()


class TriggerEditor(QDialog):
    """트리거 에디터 (기존과 동일하지만 AddCommandDialog가 개선됨)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Trigger Editor')
        self.resize(640, 400)
        self.layout = QVBoxLayout()
        
        # 녹화 관련 초기화
        self.recorder = None
        self.is_recording = False

        hl = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setToolTip("체크박스가 있는 명령어 리스트. 우클릭으로 전체 선택/해제 가능")
        
        # 우클릭 컨텍스트 메뉴 설정
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # 더블클릭 이벤트 연결
        self.list_widget.itemDoubleClicked.connect(self.on_edit)
        
        hl.addWidget(self.list_widget)

        control_v = QVBoxLayout()
        self.add_btn = QPushButton('Add')
        self.edit_btn = QPushButton('Edit')
        self.remove_btn = QPushButton('Remove')
        self.copy_btn = QPushButton('Copy')  # Copy 버튼 추가
        self.record_btn = QPushButton('🔴 녹화 (F11)')  # 녹화 버튼 추가
        self.record_btn.setShortcut('F11')
        self.record_btn.setStyleSheet("font-weight: bold; color: red;")
        self.up_btn = QPushButton('Up')
        self.down_btn = QPushButton('Down')
        control_v.addWidget(self.add_btn)
        control_v.addWidget(self.edit_btn)
        control_v.addWidget(self.remove_btn)
        control_v.addWidget(self.copy_btn)  # Copy 버튼 추가
        control_v.addWidget(self.record_btn)  # 녹화 버튼 추가
        control_v.addWidget(self.up_btn)
        control_v.addWidget(self.down_btn)
        control_v.addStretch()
        hl.addLayout(control_v)

        self.layout.addLayout(hl)

        bottom_h = QHBoxLayout()
        self.ok_btn = QPushButton('Export to Bundle')
        self.cancel_btn = QPushButton('Close')
        bottom_h.addStretch()
        bottom_h.addWidget(self.ok_btn)
        bottom_h.addWidget(self.cancel_btn)
        self.layout.addLayout(bottom_h)

        self.setLayout(self.layout)

        # connections
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit)
        self.remove_btn.clicked.connect(self.on_remove)
        self.copy_btn.clicked.connect(self.on_copy)  # Copy 버튼 연결 추가
        self.record_btn.clicked.connect(self.on_record)  # 녹화 버튼 연결 추가
        self.up_btn.clicked.connect(self.on_up)
        self.down_btn.clicked.connect(self.on_down)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        # Preload from parent's command_list if available
        try:
            parent_widget = self.parent()
            if parent_widget and hasattr(parent_widget, 'command_list'):
                for i in range(parent_widget.command_list.count()):
                    parent_item = parent_widget.command_list.item(i)
                    line = parent_item.text().strip()
                    if line:
                        item = self.add_checkable_item(line)
                        # 부모의 체크 상태도 복사
                        if hasattr(parent_item, 'checkState'):
                            item.setCheckState(parent_item.checkState())
        except Exception:
            pass

    def on_add(self):
        """새 명령어 추가 - 개선된 다이얼로그 사용"""
        dlg = AddCommandDialog(self)  # ← 개선된 다이얼로그!
        if dlg.exec_() == QDialog.Accepted:
            cmd = dlg.get_command()
            self.add_checkable_item(cmd)

    def on_edit(self):
        """선택된 명령어 편집 - 개선된 다이얼로그 사용"""
        item = self.list_widget.currentItem()
        if not item:
            return
        dlg = AddCommandDialog(self, initial=item.text())  # ← 개선된 다이얼로그!
        if dlg.exec_() == QDialog.Accepted:
            item.setText(dlg.get_command())

    def on_remove(self):
        """선택된 명령어 제거"""
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def on_up(self):
        """선택된 명령어를 위로 이동"""
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def on_down(self):
        """선택된 명령어를 아래로 이동"""
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1 and row >= 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def get_commands_as_text(self):
        """명령어 목록을 텍스트로 반환"""
        lines = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        return '\n'.join(lines)

    def get_commands_struct(self):
        """구조화된 명령어 반환: {raw, action, params, checked} 딕셔너리 리스트 (모든 항목 + 체크 상태)"""
        out = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            raw = item.text()
            parts = raw.split()
            if not parts:
                continue
            action = parts[0]
            params = parts[1:]
            is_checked = item.checkState() == Qt.Checked
            out.append({'raw': raw, 'action': action, 'params': params, 'checked': is_checked})
        return out

    def set_commands(self, lines_or_structs):
        """주어진 명령어 라인 또는 구조체로 목록 교체"""
        self.list_widget.clear()
        
        for item in lines_or_structs:
            if isinstance(item, dict):
                # 구조체인 경우 (체크 상태 정보 포함)
                raw_text = item.get('raw', '')
                is_checked = item.get('checked', True)
                if raw_text:
                    list_item = self.add_checkable_item(raw_text)
                    list_item.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
            elif isinstance(item, str) and item:
                # 문자열인 경우 (기존 호환성)
                self.add_checkable_item(item)

    def add_checkable_item(self, text):
        """체크박스가 있는 아이템을 list_widget에 추가"""
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)  # 기본적으로 체크됨
        self.list_widget.addItem(item)
        return item

    def on_copy(self):
        """선택된 명령어 복사"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            return
        
        # 현재 선택된 아이템의 바로 아래에 복사본 삽입
        current_row = self.list_widget.currentRow()
        new_item = QListWidgetItem(current_item.text())
        new_item.setFlags(new_item.flags() | Qt.ItemIsUserCheckable)
        new_item.setCheckState(current_item.checkState())  # 원본과 같은 체크 상태
        
        self.list_widget.insertItem(current_row + 1, new_item)
        self.list_widget.setCurrentRow(current_row + 1)  # 복사본을 선택

    def show_context_menu(self, position):
        """우클릭 컨텍스트 메뉴 표시"""
        menu = QMenu(self)
        
        select_all_action = QAction("전체 체크", self)
        select_all_action.triggered.connect(self.select_all_items)
        menu.addAction(select_all_action)
        
        deselect_all_action = QAction("전체 체크 해제", self)
        deselect_all_action.triggered.connect(self.deselect_all_items)
        menu.addAction(deselect_all_action)
        
        menu.exec_(self.list_widget.mapToGlobal(position))

    def select_all_items(self):
        """모든 아이템 체크"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def deselect_all_items(self):
        """모든 아이템 체크 해제"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def on_record(self):
        """녹화 시작/중지"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """녹화 시작"""
        # 부모 앱에서 현재 선택된 윈도우 정보 가져오기
        parent_app = self.parent()
        if not parent_app or not hasattr(parent_app, 'window_dropdown'):
            QMessageBox.warning(self, '경고', '메인 앱의 윈도우 정보를 가져올 수 없습니다.')
            return
        
        selected_window = parent_app.window_dropdown.currentText()
        if not selected_window:
            QMessageBox.warning(self, '경고', '먼저 윈도우를 선택해주세요.')
            return
        
        self.is_recording = True
        self.record_btn.setText('⏹️ 녹화 중지 (F11)')
        self.record_btn.setStyleSheet("font-weight: bold; color: blue;")
        
        # 녹화 스레드 시작
        self.recorder = RecorderThread()
        self.recorder.recording_started.connect(self.on_recording_started)
        self.recorder.recording_stopped.connect(self.on_recording_stopped)
        self.recorder.start()
        
        # 팝업 없이 바로 녹화 시작
        print("녹화 시작됨 - F11을 눌러 종료하세요.")
    
    def stop_recording(self):
        """녹화 중지"""
        if self.recorder:
            self.recorder.stop_recording()
    
    def on_recording_started(self):
        """녹화 시작 시그널 처리"""
        print("녹화가 시작되었습니다.")
    
    def on_recording_stopped(self, events):
        """녹화 종료 시그널 처리"""
        self.is_recording = False
        self.record_btn.setText('🔴 녹화 (F11)')
        self.record_btn.setStyleSheet("font-weight: bold; color: red;")
        
        if not events:
            print("녹화 완료 - 녹화된 이벤트가 없습니다.")
            return
        
        # 이벤트를 명령어로 변환
        commands = self.convert_events_to_commands(events)
        
        if not commands:
            print(f"녹화 완료 - {len(events)}개의 이벤트가 녹화되었으나 명령어 변환에 실패했습니다.")
            return
        
        # 명령어 리스트에 추가
        for cmd in commands:
            self.add_checkable_item(cmd)
        
        print(f'녹화 완료 - {len(events)}개의 이벤트가 녹화되었고, {len(commands)}개의 명령어가 추가되었습니다.')
    
    def convert_events_to_commands(self, events):
        """녹화된 이벤트를 명령어로 변환"""
        commands = []
        
        print(f"[DEBUG] 이벤트 변환 시작 - 총 {len(events)}개 이벤트")
        
        # 부모 앱에서 현재 선택된 윈도우 정보 가져오기
        parent_app = self.parent()
        if not parent_app or not hasattr(parent_app, 'window_dropdown'):
            print("[DEBUG] 부모 앱을 찾을 수 없음")
            return commands
        
        selected_window = parent_app.window_dropdown.currentText()
        if not selected_window:
            print("[DEBUG] 선택된 윈도우가 없음")
            return commands
        
        print(f"[DEBUG] 선택된 윈도우: {selected_window}")
        
        try:
            # 선택된 윈도우의 좌표 가져오기
            windows = gw.getWindowsWithTitle(selected_window)
            if not windows:
                print("[DEBUG] 윈도우를 찾을 수 없음")
                return commands
            
            window_obj = windows[0]
            win_x = window_obj.left
            win_y = window_obj.top
            
            print(f"[DEBUG] 윈도우 좌표: ({win_x}, {win_y})")
            
            last_time = 0
            
            for i, event in enumerate(events):
                event_time = event.get('time', 0)
                
                # 이전 이벤트와의 시간 차이 계산
                if last_time > 0:
                    wait_time = event_time - last_time
                    if wait_time > 0.1:  # 100ms 이상 차이나면 Wait 명령어 추가
                        commands.append(f"Wait {wait_time:.2f}")
                
                last_time = event_time
                
                if event['type'] == 'click':
                    # 절대 좌표를 윈도우 상대 좌표로 변환
                    rel_x = event['x'] - win_x
                    rel_y = event['y'] - win_y
                    
                    # 버튼 종류에 따라 명령어 생성 (기본 옵션: offset 모드)
                    button = event.get('button', 'Button.left')
                    if 'left' in button.lower():
                        cmd = f"Click {rel_x} {rel_y} offset"
                        commands.append(cmd)
                        print(f"[DEBUG] 이벤트 {i+1}: {cmd}")
                    elif 'right' in button.lower():
                        cmd = f"RClick {rel_x} {rel_y} offset"
                        commands.append(cmd)
                        print(f"[DEBUG] 이벤트 {i+1}: {cmd}")
                
                elif event['type'] == 'press':
                    key = event.get('key', '')
                    print(f"[DEBUG] Press 이벤트: key='{key}', len={len(key) if key else 0}")
                    
                    if key:
                        # 특수 키 처리
                        if key.lower() == 'enter':
                            cmd = "Press enter"
                            commands.append(cmd)
                            print(f"[DEBUG] 이벤트 {i+1}: {cmd}")
                        elif key.lower() == 'tab':
                            cmd = "Press tab"
                            commands.append(cmd)
                            print(f"[DEBUG] 이벤트 {i+1}: {cmd}")
                        elif key.lower() == 'space':
                            cmd = "Press space"
                            commands.append(cmd)
                            print(f"[DEBUG] 이벤트 {i+1}: {cmd}")
                        elif len(key) == 1:  # 일반 문자
                            cmd = f"Press {key}"
                            commands.append(cmd)
                            print(f"[DEBUG] 이벤트 {i+1}: {cmd}")
                        else:
                            # 기타 특수 키 (Shift, Ctrl 등은 무시하지만 로그 출력)
                            print(f"[DEBUG] 이벤트 {i+1}: 무시된 키 '{key}'")
        
        except Exception as e:
            print(f"[ERROR] 이벤트 변환 중 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"[DEBUG] 변환 완료 - 총 {len(commands)}개 명령어 생성")
        return commands