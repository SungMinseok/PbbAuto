"""
개선된 다이얼로그 - 명령어 레지스트리 사용
기존 535줄 → 대폭 축소! 🎉
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import time
import pyautogui as pag
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QLineEdit, QSpinBox, QDialogButtonBox, QWidget, 
                             QListWidget, QStackedWidget, QMessageBox, QListWidgetItem, QMenu, QAction)
from PyQt5.QtCore import QTimer, Qt
from command_registry import get_all_commands, get_command_names


class CommandPopup(QDialog):
    """명령어 실행 진행상황을 보여주는 팝업 (기존과 동일)"""
    
    def __init__(self, commands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("명령어 실행")
        self.resize(400, 300)
        self.layout = QVBoxLayout()
        self.labels = []
        for cmd in commands:
            hbox = QHBoxLayout()
            label = QLabel(cmd)
            status = QLabel("")
            hbox.addWidget(status)
            hbox.addWidget(label)
            self.layout.addLayout(hbox)
            self.labels.append((status, label))
        self.stop_btn = QPushButton("중지")
        self.stop_btn.clicked.connect(self.stop_execution)
        self.layout.addWidget(self.stop_btn)
        self.setLayout(self.layout)
        self.stopped = False

    def mark_executed(self, idx):
        """명령어 실행 완료 표시"""
        if idx < len(self.labels):
            self.labels[idx][0].setText("✅")

    def stop_execution(self):
        """실행 중지"""
        self.stopped = True
        self.close()


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
            ui_widget = command.create_ui()  # ← 각 명령어가 자체 UI 생성!
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

        # 초기 명령어 파싱
        if initial:
            self._parse_initial_command(initial)

    def _on_action_changed(self, index):
        """액션 변경 시 UI 스택 및 description 변경"""
        self.stack.setCurrentIndex(index)
        action = self.action_box.itemText(index)
        self._update_description(action)

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
        if action in self.commands:
            # 액션 설정
            index = self.command_names.index(action)
            self.action_box.setCurrentIndex(index)
            
            # 파라미터 파싱 및 UI 설정
            command = self.commands[action]
            params = command.parse_params(parts[1:])  # ← 자동 파싱!
            command.set_ui_values(params)  # ← 자동 UI 설정!

    def get_command(self):
        """현재 명령어 문자열 반환 - 자동화됨!"""
        current_action = self.action_box.currentText()
        command = self.commands.get(current_action)
        if command:
            return command.get_command_string()  # ← 자동 생성!
        return current_action


class TriggerEditor(QDialog):
    """트리거 에디터 (기존과 동일하지만 AddCommandDialog가 개선됨)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Trigger Editor')
        self.resize(640, 400)
        self.layout = QVBoxLayout()

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
        self.up_btn = QPushButton('Up')
        self.down_btn = QPushButton('Down')
        control_v.addWidget(self.add_btn)
        control_v.addWidget(self.edit_btn)
        control_v.addWidget(self.remove_btn)
        control_v.addWidget(self.copy_btn)  # Copy 버튼 추가
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