# 로그 설정을 가장 먼저 import (모든 print 출력을 로그파일에도 저장)
import logger_setup

import sys
import time
import os
import json
import threading
import subprocess
from datetime import datetime
import pygetwindow as gw
import pyautogui as pag
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QLineEdit, QScrollArea, QFileDialog, 
                             QMessageBox, QCheckBox, QListWidget, QInputDialog, QMenuBar, 
                             QAction, QDialog, QListWidgetItem, QMenu, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget, QTextEdit,
                             QDateEdit, QTimeEdit, QDialogButtonBox, QSpinBox)
from PyQt5.QtCore import QTimer, Qt, QDate, QTime, pyqtSignal

# 분리된 모듈들 import (print 오버라이드 후)
from constants import current_dir, dir_preset, bundles_dir
from utils import (load_config, save_config, auto_detect_tesseract, take_screenshot, 
                   image_to_text, align_windows, set_pytesseract_cmd, start_keep_alive, 
                   stop_keep_alive, is_keep_alive_running)
from commands import CommandProcessor
from dialogs import CommandPopup, TriggerEditor
from scheduler import ScheduleManager, SchedulerEngine, Schedule, ScheduleType, ScheduleStatus
from updater import AutoUpdater
from update_dialogs import UpdateNotificationDialog, DownloadProgressDialog, AboutDialog


class PbbAutoApp(QWidget):
    """메인 애플리케이션 클래스 (리팩토링된 버전)"""
    
    # 시그널 정의 (워커 스레드에서 메인 스레드로 통신)
    execution_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.stop_flag = False
        self.triggers = []  # structured trigger list
        self.bundles = {}  # named bundles stored as {name: [structs]}
        self.command_processor = CommandProcessor()  # 명령어 처리테스트기
        self.command_processor.set_main_app(self)  # 메인 앱 참조 설정
        self.current_file_path = None  # 현재 불러온 파일의 경로를 기억
        
        # 스케줄링 시스템 초기화
        self.schedule_manager = ScheduleManager()
        self.scheduler_engine = SchedulerEngine(self.schedule_manager)
        self.scheduler_engine.set_command_executor(self.execute_scheduled_command)
        
        # 자동 업데이트 시스템 초기화
        self.auto_updater = AutoUpdater()
        self.auto_updater.set_main_app(self)  # main app 참조 설정
        
        self.initUI()
        self.prefix_input.setText('SM5')
        self.refresh_window_list()
        
        # 시그널 연결
        self.execution_finished.connect(self.on_execution_finished)
        
        # 마우스 위치 실시간 추적 설정
        self.init_mouse_tracker()
        
        # 스케줄러 시작 
        self.scheduler_engine.start()
        
        # 스케줄 상태 초기 업데이트
        self.update_schedule_status()
        
        # Keep-alive 상태 초기 업데이트
        self.update_keep_alive_status()
        
        # 시작 시 자동 업데이트 확인 (비동기)
        QTimer.singleShot(2000, self.check_for_updates_on_startup)  # 2초 후 체크
    
    def initUI(self):
        """UI 초기화"""
        # Layouts
        main_layout = QVBoxLayout()

        # 실행파일 경로 인풋박스 및 버튼
        # self.file_path_input = QLineEdit(self)
        # self.file_path_input.setPlaceholderText("Select .bat file...")
        
        # self.file_select_button = QPushButton("Browse", self)
        # self.file_select_button.clicked.connect(self.select_bat_file)

        # self.file_run_button = QPushButton("Run File", self)
        # self.file_run_button.clicked.connect(self.run_bat_file)

        # Adding to layout
        # file_layout = QHBoxLayout()
        # file_layout.addWidget(self.file_path_input)
        # file_layout.addWidget(self.file_select_button)
        # file_layout.addWidget(self.file_run_button)
        
        # main_layout.addLayout(file_layout)



        # 윈도우 선택 및 좌표 섹션
        self._init_window_section(main_layout)

        # 명령어 리스트 섹션
        self._init_command_section(main_layout)

        # 실행 버튼 섹션
        self._init_execute_section(main_layout)

        # 메뉴바 추가
        self._init_menubar(main_layout)

        # ===== Log UI (최하단, 최대 3줄, 스크롤) =====
        from PyQt5.QtWidgets import QTextEdit
        from PyQt5.QtCore import Qt
        self.log_box = QTextEdit(self)
        self.log_box.setReadOnly(True)
        #self.log_box.setMaximumBlockCount(3)
        self.log_box.setMaximumHeight(60)
        self.log_box.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.log_box.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_box)
        self.log_lines = []

        # Window properties
        self.update_window_title()
        self.setGeometry(300, 300, 500, 400)
        self.setLayout(main_layout)
       

    def _init_window_section(self, main_layout):
        """윈도우 선택 섹션 초기화"""
        self.prefix_input = QLineEdit(self)
        self.prefix_input.setPlaceholderText("Enter window title prefix...")
        self.refresh_button = QPushButton('Refresh', self)
        self.refresh_button.clicked.connect(self.refresh_window_list)
        self.window_dropdown = QComboBox(self)
        self.window_dropdown.setFixedWidth(200)
        self.multi_checkbox = QCheckBox('Multi', self)
        self.multi_align_button = QPushButton('Align', self)
        self.multi_align_button.clicked.connect(self.align_windows)
        self.mouse_track_button = QPushButton('Mouse OFF', self)
        self.mouse_track_button.clicked.connect(self.toggle_mouse_tracking_button)
        self.coord_label = QLabel('Coordinates: (x, y, w, h)', self)

        # Layout
        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(self.prefix_input)
        refresh_layout.addWidget(self.refresh_button)
        refresh_layout.addWidget(self.window_dropdown)
        refresh_layout.addWidget(self.multi_checkbox)
        refresh_layout.addWidget(self.multi_align_button)
        refresh_layout.addWidget(self.mouse_track_button)

        main_layout.addLayout(refresh_layout)
        main_layout.addWidget(self.coord_label)

    def _init_command_section(self, main_layout):
        """명령어 리스트 섹션 초기화"""
        hl_commands = QHBoxLayout()
        self.command_list = QListWidget(self)
        self.command_list.setToolTip("Commands (one per line). Use the Trigger Editor for structured editing.\nRight-click for select/deselect all options.")
        
        # 우클릭 컨텍스트 메뉴 설정
        self.command_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.command_list.customContextMenuRequested.connect(self.show_context_menu)
        
        hl_commands.addWidget(self.command_list)

        # Command-list controls
        cmd_ctrl = QVBoxLayout()
        self.cmd_add_btn = QPushButton('Add')
        self.cmd_edit_btn = QPushButton('Edit')
        self.cmd_remove_btn = QPushButton('Remove')
        self.cmd_copy_btn = QPushButton('Copy')
        self.cmd_up_btn = QPushButton('Up')
        self.cmd_down_btn = QPushButton('Down')
        cmd_ctrl.addWidget(self.cmd_add_btn)
        cmd_ctrl.addWidget(self.cmd_edit_btn)
        cmd_ctrl.addWidget(self.cmd_remove_btn)
        cmd_ctrl.addWidget(self.cmd_copy_btn)
        cmd_ctrl.addWidget(self.cmd_up_btn)
        cmd_ctrl.addWidget(self.cmd_down_btn)
        cmd_ctrl.addStretch()
        hl_commands.addLayout(cmd_ctrl)

        # Wire command-list controls
        self.cmd_add_btn.clicked.connect(self.on_cmd_add)
        self.cmd_edit_btn.clicked.connect(self.on_cmd_edit)
        self.cmd_remove_btn.clicked.connect(self.on_cmd_remove)
        self.cmd_copy_btn.clicked.connect(self.on_cmd_copy)
        self.cmd_up_btn.clicked.connect(self.on_cmd_up)
        self.cmd_down_btn.clicked.connect(self.on_cmd_down)
        self.command_list.itemDoubleClicked.connect(self.on_cmd_item_double_clicked)

        main_layout.addLayout(hl_commands)

    def _init_execute_section(self, main_layout):
        """실행 버튼 섹션 초기화"""
        execute_layout = QHBoxLayout()
        self.execute_count_label = QLabel('실행횟수', self)
        self.execute_count_lineEdit = QLineEdit(self)
        self.execute_count_lineEdit.setFixedWidth(50)
        self.open_report_checkbox = QCheckBox('Open Report', self)
        self.open_report_checkbox.setChecked(True)
        self.open_screenshot_image = QCheckBox('Open Screenshot Image', self)
        self.open_screenshot_image.setChecked(True)
        self.execute_button = QPushButton('Execute (F5)', self)
        self.execute_button.setShortcut('F5')
        self.execute_button.clicked.connect(self.execute_commands)
        
        # Schedule button
        self.schedule_button = QPushButton('Schedule...', self)
        self.schedule_button.clicked.connect(self.open_schedule_dialog)
        
        # Schedule status label
        self.schedule_status_label = QLabel('Schedules: 0 active', self)
        self.schedule_status_label.setStyleSheet("color: #666; font-size: 10px;")
        
        # Keep-alive Controls
        self.keep_alive_button = QPushButton('Keep-Alive: OFF', self)
        self.keep_alive_button.clicked.connect(self.toggle_keep_alive)
        self.keep_alive_button.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        self.keep_alive_status_label = QLabel('PC 잠금 방지: 비활성', self)
        self.keep_alive_status_label.setStyleSheet("color: #666; font-size: 10px;")
        
        execute_layout.addWidget(self.execute_count_label)
        execute_layout.addWidget(self.execute_count_lineEdit)
        execute_layout.addWidget(self.open_report_checkbox)
        execute_layout.addWidget(self.open_screenshot_image)
        execute_layout.addStretch()
        execute_layout.addWidget(self.schedule_button)
        execute_layout.addWidget(self.execute_button)

        # Stop button
        self.stop_button = QPushButton('Stop', self)
        self.stop_button.clicked.connect(self.stop_execution)
        execute_layout.addWidget(self.stop_button)
        
        # Schedule status layout (아래 줄)
        schedule_status_layout = QHBoxLayout()
        schedule_status_layout.addWidget(self.schedule_status_label)
        schedule_status_layout.addStretch()
        schedule_status_layout.addWidget(self.keep_alive_status_label)
        schedule_status_layout.addWidget(self.keep_alive_button)

        main_layout.addLayout(execute_layout)
        main_layout.addLayout(schedule_status_layout)

    def _init_menubar(self, main_layout):
        """메뉴바 초기화"""
        menubar = QMenuBar(self)
        menu = menubar.addMenu('File')
        
        new_file_action = QAction('New File', self)
        new_file_action.setShortcut('Ctrl+N')
        new_file_action.triggered.connect(self.new_file)
        menu.addAction(new_file_action)
        
        menu.addSeparator()
        
        load_bundles_action = QAction('Open Bundles...', self)
        load_bundles_action.setShortcut('Ctrl+O')
        load_bundles_action.triggered.connect(self.load_bundles)
        menu.addAction(load_bundles_action)

        menu.addSeparator()
        
        save_bundles_action = QAction('Save Bundles', self)
        save_bundles_action.setShortcut('Ctrl+S')
        save_bundles_action.triggered.connect(self.save_bundles)
        menu.addAction(save_bundles_action)
        
        save_as_bundles_action = QAction('Save Bundles As...', self)
        save_as_bundles_action.setShortcut('Ctrl+Shift+S')
        save_as_bundles_action.triggered.connect(self.save_bundles_as)
        menu.addAction(save_as_bundles_action)

        
        settings_menu = menubar.addMenu('Settings')

        set_tess_action = QAction('Set Tesseract Path', self)
        set_tess_action.triggered.connect(self.select_tesseract_file)
        settings_menu.addAction(set_tess_action)

        # test_ocr_action = QAction('Test OCR', self)
        # test_ocr_action.triggered.connect(self.test_ocr)
        # settings_menu.addAction(test_ocr_action)
        
        # Help 메뉴 추가
        help_menu = menubar.addMenu('Help')
        
        check_update_action = QAction('업데이트 확인', self)
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)
        
        help_menu.addSeparator()
        
        about_action = QAction('정보', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Place menubar at the top
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(menubar)
        outer_layout.addLayout(main_layout)
        self.setLayout(outer_layout)

    def refresh_window_list(self):
        """윈도우 목록 새로고침"""
        prefix = self.prefix_input.text()
        all_windows = gw.getAllTitles()
        filtered_windows = [w for w in all_windows if prefix in w]
        self.window_dropdown.clear()
        self.window_dropdown.addItems(filtered_windows)
        if filtered_windows:
            self.update_coordinates()

    def update_coordinates(self):
        """선택된 윈도우의 좌표 업데이트"""
        selected_window = self.window_dropdown.currentText()
        if selected_window:
            window_obj = gw.getWindowsWithTitle(selected_window)[0]
            x, y, width, height = window_obj.left, window_obj.top, window_obj.width, window_obj.height
            
            # 디버깅 정보 출력 (필요시에만)
            if globals().get('DEBUG_COORDINATES', False):
                print(f"[DEBUG] 윈도우 정보:")
                print(f"  - left: {window_obj.left}, top: {window_obj.top}")
                print(f"  - width: {window_obj.width}, height: {window_obj.height}")
                print(f"  - right: {window_obj.left + window_obj.width}, bottom: {window_obj.top + window_obj.height}")
            
            self.coord_label.setText(f"Coordinates: ({x}, {y}, {width}, {height})")
            return x, y, width, height

    def execute_commands(self):
        """명령어 실행"""
        self.stop_flag = False
        self.command_processor.stop_flag = False
        
        # 실행 전 윈도우 목록 자동 새로고침
        print("실행 전 윈도우 목록 자동 새로고침...")
        self.refresh_window_list()
        
        # Expand bundles to get flat command list for display (only from checked items)
        display_commands = []
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            # 체크된 아이템만 처리
            if item.checkState() == Qt.Checked:
                item_text = item.text()
                bundle_name = self._parse_bundle_display(item_text)
                if bundle_name and bundle_name in self.bundles:
                    bundle_structs = self.bundles[bundle_name]
                    for struct in bundle_structs:
                        # 번들 내 개별 명령어의 체크 상태 확인
                        is_checked = struct.get('checked', True)  # 기본값 True (기존 호환성)
                        if is_checked:
                            display_commands.append(struct.get('raw', ''))
                else:
                    display_commands.append(item_text.split('#')[0].strip())
        
        display_commands = [c for c in display_commands if c.strip()]
        self.popup = CommandPopup(display_commands, self)
        self.popup.show()
        
        # popup을 command_processor.state에 저장 (wait 명령어에서 타이머 업데이트용)
        self.command_processor.state['popup'] = self.popup
        
        print("명령어 실행 시작")
        self.execution_thread = threading.Thread(target=self._execute_commands_worker)
        self.execution_thread.daemon = True  # 메인 프로그램 종료 시 자동 종료
        self.execution_thread.start()

    def _execute_commands_worker(self):
        """명령어 실행 워커 (별도 스레드)"""
        from datetime import datetime
        
        # 테스트 세션 시작 시간 및 제목 설정
        start_time = datetime.now()
        self.command_processor.state['test_session_start'] = start_time
        
        # 현재 선택된 번들명에서 테스트 제목 추출
        test_title = self._extract_test_title_from_bundles()
        self.command_processor.state['test_session_title'] = test_title
        
        print(f"테스트 세션 시작: {test_title} [{start_time.strftime('%Y-%m-%d %H:%M:%S')}]")
        
        # 실행 전 윈도우 리스트 새로고침
        print("윈도우 리스트 새로고침 중...")
        all_windows = gw.getAllWindows()
        print(f"발견된 윈도우 수: {len(all_windows)}")
        selected_windows = []
        execute_count = self.execute_count_lineEdit.text()
        if execute_count == "" or int(execute_count) == 0:
            execute_count = 1
        else:
            execute_count = int(execute_count)

        for i in range(execute_count):
            if self.stop_flag:
                print("Stopped before window selection.")
                return

            # 윈도우 선택
            selected_windows = []  # 매 루프마다 초기화
            if self.multi_checkbox.isChecked():
                for window in all_windows:
                    if window.title in [self.window_dropdown.itemText(i) for i in range(self.window_dropdown.count())]:
                        selected_windows.append(window)
            else:
                selected_window = self.window_dropdown.currentText()
                print(f"찾으려는 윈도우: '{selected_window}'")
                for window in all_windows:
                    if window.title == selected_window:
                        selected_windows.append(window)
                        print(f"✓ 윈도우 찾음: '{window.title}'")
                        break
            
            # 디버깅: 윈도우 선택 결과 확인
            if not selected_windows:
                print(f"⚠️ 경고: 선택된 윈도우가 없습니다. (드롭다운 선택: '{self.window_dropdown.currentText()}')")
                print("현재 사용 가능한 윈도우 목록:")
                for idx, window in enumerate(all_windows[:10], 1):  # 처음 10개만 표시
                    print(f"  {idx}. '{window.title}'")
                if len(all_windows) > 10:
                    print(f"  ... 외 {len(all_windows) - 10}개 더")
                print("명령어 실행을 건너뜁니다.")
                continue  # 다음 반복으로

            for window in selected_windows:
                if self.stop_flag:
                    print("Stopped before window activation.")
                    return
                try:
                    window.activate()
                except Exception as e:
                    print(f"윈도우 '{window.title}' 활성화 중 오류 발생: {e}")

                # 윈도우 좌표는 이제 각 명령어에서 동적으로 가져옴
                print(f"현재 윈도우: {window.title}")

                # Expand bundles into flat command list (only from checked items)
                commands = []
                for j in range(self.command_list.count()):
                    item = self.command_list.item(j)
                    # 체크된 아이템만 처리
                    if item.checkState() == Qt.Checked:
                        item_text = item.text()
                        bundle_name = self._parse_bundle_display(item_text)
                        if bundle_name and bundle_name in self.bundles:
                            print(f"Executing bundle: {bundle_name}")
                            bundle_structs = self.bundles[bundle_name]
                            for struct in bundle_structs:
                                # 번들 내 개별 명령어의 체크 상태 확인
                                is_checked = struct.get('checked', True)  # 기본값 True (기존 호환성)
                                if is_checked:
                                    cmd = struct.get('raw', '').split('#')[0].strip()
                                    if cmd:
                                        commands.append(cmd)
                                else:
                                    print(f"Skipping unchecked command in bundle: {struct.get('raw', '')}")
                        else:
                            cmd = item_text.split('#')[0].strip()
                            if cmd:
                                commands.append(cmd)
                    else:
                        print(f"Skipping unchecked item: {item.text()}")
                
                time.sleep(0.2)
                for idx, command in enumerate(commands):
                    if self.stop_flag:
                        print("Stopped during command execution.")
                        return
                    if command:
                        print(f"[{idx+1}/{len(commands)}] {command}")
                        # 명령어 처리기에 위임 (윈도우 좌표는 동적으로 가져옴)
                        self.command_processor.process_command(command)
                        if hasattr(self, 'popup') and self.popup:
                            try:
                                self.popup.mark_executed(idx)
                            except Exception:
                                pass

        # 리포트 열기
        try:
            if self.open_report_checkbox.isChecked() and hasattr(self.command_processor, 'cl_path'):
                os.startfile(self.command_processor.cl_path)
        except Exception as e:
            print('리포트 파일 열기 오류 :', e)
        
        # Execute 루틴 완료 후 test_results 및 세션 정보 초기화 (중복 누적 방지)
        if hasattr(self.command_processor, 'state'):
            end_time = datetime.now()
            if 'test_results' in self.command_processor.state:
                test_count = len(self.command_processor.state['test_results'])
                if test_count > 0:
                    start_time = self.command_processor.state.get('test_session_start', end_time)
                    duration = end_time - start_time
                    test_title = self.command_processor.state.get('test_session_title', '알 수 없는 테스트')
                    print(f"테스트 세션 완료: {test_title}")
                    print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"소요 시간: {duration}")
                    print(f"Execute 루틴 완료: {test_count}개의 테스트 결과가 초기화됩니다.")
                    self.command_processor.state['test_results'].clear()
            
            # 세션 정보 초기화
            self.command_processor.state['test_session_start'] = None
            self.command_processor.state['test_session_title'] = None
            
            # popup 참조 제거
            if 'popup' in self.command_processor.state:
                self.command_processor.state['popup'] = None
        
        # 명령어 실행 완료 후 시그널 emit (메인 스레드에서 popup 닫기)
        print("명령어 실행 완료 - 시그널 emit")
        self.execution_finished.emit()

    def stop_execution(self):
        """실행 중지 (개선된 버전)"""
        print("🛑 중지 버튼 클릭됨 - 실행 중지 시작...")
        
        # 중지 플래그 설정
        self.stop_flag = True
        self.command_processor.stop_flag = True
        
        # 팝업 즉시 닫기 및 참조 제거
        if hasattr(self, 'popup') and self.popup:
            try:
                self.popup.stopped = True
                self.popup.close()
                print("✓ Command popup closed")
            except Exception as e:
                print(f"팝업 닫기 중 오류: {e}")
        
        # popup 참조 제거
        if hasattr(self.command_processor, 'state') and 'popup' in self.command_processor.state:
            self.command_processor.state['popup'] = None
        
        # 스레드 상태 확인 및 강제 종료 준비
        if hasattr(self, 'execution_thread') and self.execution_thread:
            if self.execution_thread.is_alive():
                print("⚠️ 실행 스레드가 아직 실행 중입니다. 강제 종료 대기 중...")
                
                # 5초 동안 정상 종료 대기
                import threading
                import time
                
                def wait_for_thread():
                    for i in range(50):  # 0.1초씩 50번 = 5초
                        if not self.execution_thread.is_alive():
                            print("✓ 실행 스레드가 정상 종료됨")
                            return
                        time.sleep(0.1)
                    
                    # 5초 후에도 살아있으면 경고
                    if self.execution_thread.is_alive():
                        print("⚠️ 실행 스레드가 5초 후에도 종료되지 않음")
                        print("   - 윈도우 대기 중이거나 다른 블로킹 작업 수행 중일 수 있음")
                        print("   - 프로그램을 재시작하는 것을 권장합니다")
                
                # 별도 스레드에서 대기 (UI 블로킹 방지)
                wait_thread = threading.Thread(target=wait_for_thread, daemon=True)
                wait_thread.start()
            else:
                print("✓ 실행 스레드가 이미 종료됨")
        
        print("🛑 Execution stopped by user.")
    
    def on_execution_finished(self):
        """명령어 실행 완료 시 호출되는 슬롯 (메인 스레드에서 실행)"""
        print("명령어 실행 완료 - popup 닫기 (메인 스레드)")
        if hasattr(self, 'popup') and self.popup:
            try:
                self.popup.close()
                print("✓ Command popup closed")
            except Exception as e:
                print(f"팝업 닫기 중 오류: {e}")

    def align_windows(self):
        """윈도우 정렬"""
        if not self.multi_checkbox.isChecked():
            return

        all_windows = gw.getAllWindows()
        selected_windows = []
        
        for i in range(min(self.window_dropdown.count(), 4)):
            title = self.window_dropdown.itemText(i)
            matching_windows = [w for w in all_windows if w.title == title]
            if matching_windows:
                selected_windows.append(matching_windows[0])
                all_windows.remove(matching_windows[0])

        align_windows(selected_windows)

    def select_bat_file(self):
        """배치 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select .bat file", "", "Batch Files (*.bat)")
        if file_path:
            self.file_path_input.setText(file_path)

    def run_bat_file(self):
        """배치 파일 실행"""
        file_path = self.file_path_input.text().strip()
        if file_path and os.path.exists(file_path) and file_path.endswith(".bat"):
            try:
                file_dir = os.path.dirname(file_path)
                subprocess.Popen(file_path, cwd=file_dir, shell=True)
            except Exception as e:
                self.show_error_message(f"Error running file: {e}")
        else:
            self.show_error_message("Invalid file path. Please select a valid .bat file.")

    def select_tesseract_file(self):
        """Tesseract 실행파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select tesseract.exe", "", "Executable Files (*.exe)")
        if file_path:
            if set_pytesseract_cmd(file_path):
                save_config(file_path)
                QMessageBox.information(self, "Tesseract", f"Tesseract set to: {file_path}")
            else:
                QMessageBox.warning(self, "Tesseract", "Selected file is not a valid tesseract.exe")

    def test_ocr(self):
        """OCR 테스트"""
        img_path = take_screenshot()
        try:
            extracted = image_to_text(img_path=img_path, lang='eng')
            if not extracted:
                extracted = "(No text found)"
            QMessageBox.information(self, "OCR Result", extracted)
        except Exception as e:
            QMessageBox.critical(self, "OCR Error", f"Error running OCR: {e}")

    def open_trigger_editor(self):
        """트리거 에디터 열기"""
        dlg = TriggerEditor(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            structs = dlg.get_commands_struct()
            if not structs:
                QMessageBox.warning(self, "Trigger Editor", "No commands to bundle.")
                return

            # 기본 번들 이름 자동 생성 (bundle_숫자)
            existing_names = set(self.bundles.keys())
            base = "bundle_"
            n = 1
            while f"{base}{n}" in existing_names:
                n += 1
            default_name = f"{base}{n}"
            name, ok = QInputDialog.getText(self, "Bundle name", "Enter bundle name:", text=default_name)
            if not ok or not name.strip():
                while True:
                    QMessageBox.warning(self, "Trigger Editor", "Bundle name required.")
                    name, ok = QInputDialog.getText(self, "Bundle name", "Enter bundle name:", text=default_name)
                    if ok and name.strip():
                        break
                return
            name = name.strip()

            if name in self.bundles:
                resp = QMessageBox.question(self, "Overwrite Bundle?", f"Bundle '{name}' exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
                if resp != QMessageBox.Yes:
                    return

            self.bundles[name] = structs
            display = f"[BUNDLE] {name} ({len(structs)})"
            self.add_checkable_item(display)
            self.triggers = structs

    def show_error_message(self, message):
        """에러 메시지 표시"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    # ========== 명령어 리스트 관련 메서드들 ==========
    def _parse_bundle_display(self, display_text):
        """번들 표시에서 번들 이름 추출"""
        prefix = "[BUNDLE] "
        if not display_text.startswith(prefix):
            return None
        rest = display_text[len(prefix):]
        idx = rest.rfind(" (")
        if idx == -1:
            return rest.strip()
        return rest[:idx].strip()

    def _open_trigger_editor_with_initial(self, initial_lines=None):
        """초기 라인으로 트리거 에디터 열기"""
        dlg = TriggerEditor(parent=self)
        try:
            if initial_lines is not None:
                dlg.set_commands(initial_lines)
        except Exception:
            pass
        if dlg.exec_() == QDialog.Accepted:
            return dlg.get_commands_struct()
        return None

    def on_cmd_add(self):
        """명령어 추가"""
        structs = self._open_trigger_editor_with_initial([])
        if not structs:
            return

        # 기본 번들 이름 자동 생성 (bundle_n)
        existing_names = set(self.bundles.keys())
        base = "bundle_"
        n = 1
        while f"{base}{n}" in existing_names:
            n += 1
        default_name = f"{base}{n}"
        name, ok = QInputDialog.getText(
            self, 
            "Bundle name", 
            "Enter bundle name:", 
            text=default_name
        )
        if not ok or not name.strip():
            while True:
                QMessageBox.warning(self, "Trigger Editor", "Bundle name required.")
                name, ok = QInputDialog.getText(self, "Bundle name", "Enter bundle name:", text=default_name)
                if ok and name.strip():
                    break
            return
        name = name.strip()
        if name in self.bundles:
            resp = QMessageBox.question(self, "Overwrite Bundle?", f"Bundle '{name}' exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        self.bundles[name] = structs
        display = f"[BUNDLE] {name} ({len(structs)})"
        self.add_checkable_item(display)
        self.triggers = structs

    def on_cmd_edit(self):
        """명령어 편집"""
        selected_items = self.command_list.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        display_text = item.text()
        bundle_name = self._parse_bundle_display(display_text)
        if bundle_name:
            existing_structs = self.bundles.get(bundle_name, [])
            # 구조체 전체를 전달 (체크 상태 포함)
            structs = self._open_trigger_editor_with_initial(existing_structs)
            if not structs:
                return
            new_name, ok = QInputDialog.getText(self, "Bundle name", "Update bundle name:", text=bundle_name)
            if not ok or not new_name.strip():
                return
            new_name = new_name.strip()
            if new_name != bundle_name and new_name in self.bundles:
                resp = QMessageBox.question(self, "Overwrite Bundle?", f"Bundle '{new_name}' exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
                if resp != QMessageBox.Yes:
                    return
            if new_name != bundle_name and bundle_name in self.bundles:
                try:
                    del self.bundles[bundle_name]
                except Exception:
                    pass
            self.bundles[new_name] = structs
            item.setText(f"[BUNDLE] {new_name} ({len(structs)})")
            self.triggers = structs
        else:
            initial_lines = [display_text]
            structs = self._open_trigger_editor_with_initial(initial_lines)
            if not structs:
                return
            name, ok = QInputDialog.getText(self, "Bundle name", "Enter bundle name:")
            if not ok or not name.strip():
                return
            name = name.strip()
            if name in self.bundles:
                resp = QMessageBox.question(self, "Overwrite Bundle?", f"Bundle '{name}' exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
                if resp != QMessageBox.Yes:
                    return
            self.bundles[name] = structs
            item.setText(f"[BUNDLE] {name} ({len(structs)})")
            self.triggers = structs

    def on_cmd_remove(self):
        """명령어 제거"""
        selected_rows = sorted([self.command_list.row(i) for i in self.command_list.selectedItems()], reverse=True)
        for row in selected_rows:
            item = self.command_list.item(row)
            if item:
                bundle_name = self._parse_bundle_display(item.text())
                if bundle_name and bundle_name in self.bundles:
                    del self.bundles[bundle_name]
                    print(f"Bundle '{bundle_name}' removed from storage")
            self.command_list.takeItem(row)

    def on_cmd_copy(self):
        """명령어 복사 - 번들의 경우 구조체도 함께 복사"""
        selected_rows = sorted([self.command_list.row(i) for i in self.command_list.selectedItems()])
        if not selected_rows:
            return
        
        shift = 0
        for idx, row in enumerate(selected_rows):
            insert_at = row + 1 + shift
            original_item = self.command_list.item(row + shift - shift)
            original_text = original_item.text()
            
            # 번들인지 확인
            bundle_name = self._parse_bundle_display(original_text)
            if bundle_name and bundle_name in self.bundles:
                # 번들 복사: 새로운 이름으로 번들 구조체도 함께 복사
                import copy
                original_bundle_data = copy.deepcopy(self.bundles[bundle_name])
                
                # 새로운 번들 이름 생성
                existing_names = set(self.bundles.keys())
                base_name = bundle_name
                default_copy_name = f"{base_name}_copy"
                counter = 1
                while default_copy_name in existing_names:
                    counter += 1
                    default_copy_name = f"{base_name}_copy{counter}"
                
                # 사용자에게 새 번들 이름 입력받기
                copy_name, ok = QInputDialog.getText(
                    self, 
                    "Copy Bundle", 
                    f"Enter name for copied bundle:", 
                    text=default_copy_name
                )
                
                if not ok or not copy_name.strip():
                    # 취소하거나 빈 이름이면 복사하지 않음
                    shift -= 1  # shift 조정
                    continue
                
                copy_name = copy_name.strip()
                
                # 이름 중복 확인
                if copy_name in existing_names:
                    resp = QMessageBox.question(
                        self, 
                        "Overwrite Bundle?", 
                        f"Bundle '{copy_name}' already exists. Overwrite?", 
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if resp != QMessageBox.Yes:
                        # 덮어쓰지 않으면 복사하지 않음
                        shift -= 1  # shift 조정
                        continue
                
                # 새 번들을 딕셔너리에 추가
                self.bundles[copy_name] = original_bundle_data
                
                # 새 리스트 아이템 생성
                new_text = f"[BUNDLE] {copy_name} ({len(original_bundle_data)})"
                new_item = QListWidgetItem(new_text)
                print(f"번들 복사 완료: {bundle_name} -> {copy_name} (명령어 {len(original_bundle_data)}개)")
            else:
                # 일반 명령어 복사
                new_item = QListWidgetItem(original_text)
            
            new_item.setFlags(new_item.flags() | Qt.ItemIsUserCheckable)
            new_item.setCheckState(original_item.checkState())  # 원본과 같은 체크 상태
            self.command_list.insertItem(insert_at, new_item)
            shift += 1
            
        # Select the newly duplicated items
        self.command_list.clearSelection()
        for idx, row in enumerate(selected_rows):
            new_row = row + 1 + idx
            self.command_list.item(new_row).setSelected(True)

    def on_cmd_up(self):
        """명령어 위로 이동"""
        count = self.command_list.count()
        if count <= 1:
            return
        selected_rows = sorted([self.command_list.row(i) for i in self.command_list.selectedItems()])
        if not selected_rows:
            return
        for row in selected_rows:
            if row == 0 or (row - 1) in selected_rows:
                continue
            item = self.command_list.takeItem(row)
            self.command_list.insertItem(row - 1, item)
        self.command_list.clearSelection()
        for row in [max(r - 1, 0) if r not in (0,) else 0 for r in selected_rows]:
            self.command_list.item(row).setSelected(True)

    def on_cmd_down(self):
        """명령어 아래로 이동"""
        count = self.command_list.count()
        if count <= 1:
            return
        selected_rows = sorted([self.command_list.row(i) for i in self.command_list.selectedItems()], reverse=True)
        if not selected_rows:
            return
        for row in selected_rows:
            if row >= count - 1 or (row + 1) in selected_rows:
                continue
            item = self.command_list.takeItem(row)
            self.command_list.insertItem(row + 1, item)
        self.command_list.clearSelection()
        for row in [min(r + 1, count - 1) if r != count - 1 else count - 1 for r in selected_rows]:
            self.command_list.item(row).setSelected(True)

    def on_cmd_item_double_clicked(self, item):
        """아이템 더블클릭"""
        self.on_cmd_edit()

    # ========== 프리셋 관련 메서드들 ==========
    # def savePreset(self):
    #     """프리셋 저장"""
    #     new_preset = self.add_preset_line.text().strip()
    #     if not new_preset:
    #         QMessageBox.warning(self, "Warning", "Preset name cannot be empty.")
    #         return
    #     if not new_preset.endswith('.txt'):
    #         new_preset += '.txt'
    #     self.save_textarea_content(new_preset)
    #     self.refreshPresets()
    #     print(f'saved preset successfully: {new_preset}')

    # def deletePreset(self):
    #     """프리셋 삭제"""
    #     current_preset = self.preset.currentText()
    #     if not current_preset:
    #         return

    #     confirm_dialog = QMessageBox()
    #     confirm_dialog.setIcon(QMessageBox.Warning)
    #     confirm_dialog.setText(f"Are you sure you want to delete the preset '{current_preset}'?")
    #     confirm_dialog.setWindowTitle("Confirm Deletion")
    #     confirm_dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

    #     result = confirm_dialog.exec_()

    #     if result == QMessageBox.Ok:
    #         file_path = os.path.join(dir_preset, f"{current_preset}")
    #         try:
    #             os.remove(file_path)
    #             self.refreshPresets()
    #             QMessageBox.information(self, "Success", f"Preset '{current_preset}' has been deleted.")
    #         except OSError as e:
    #             QMessageBox.critical(self, "Error", f"Failed to delete preset: {str(e)}")

    # def refreshPresets(self):
    #     """프리셋 새로고침"""
    #     self.preset.clear()
    #     self.preset_prefix.clear()
    #     preset_files = [f for f in os.listdir(dir_preset) if f.endswith('.txt')]
        
    #     prefixes = set()
    #     prefix_to_files = {}

    #     for filename in preset_files:
    #         parts = filename.split('_')
    #         if len(parts) > 1:
    #             prefix = parts[0]
    #         else:
    #             prefix = parts[0].replace('.txt', '')

    #         prefixes.add(prefix)

    #         if prefix not in prefix_to_files:
    #             prefix_to_files[prefix] = []
    #         prefix_to_files[prefix].append(filename)

    #     def on_preset_prefix_changed():
    #         current_prefix = self.preset_prefix.currentText()
    #         self.preset.clear()
    #         if current_prefix in prefix_to_files:
    #             self.preset.addItems(prefix_to_files[current_prefix])

    #     self.preset_prefix.addItems(sorted(prefixes))
    #     on_preset_prefix_changed()
    #     self.preset_prefix.currentIndexChanged.connect(on_preset_prefix_changed)

    #     if self.preset_prefix.count() > 0:
    #         self.preset_prefix.setCurrentIndex(0)

    # def applyPreset(self):
    #     """프리셋 적용"""
    #     selected_preset = self.preset.currentText()
    #     self.add_preset_line.setText(selected_preset)

    #     if selected_preset:
    #         self.load_textarea_content(selected_preset)

    # def save_textarea_content(self, filename='commands.txt'):
    #     """텍스트영역 내용 저장"""
    #     file_path = os.path.join(dir_preset, filename)
    #     lines = [self.command_list.item(i).text() for i in range(self.command_list.count())]
    #     content = '\n'.join(lines)
    #     with open(file_path, 'w', encoding='utf-8') as file:
    #         file.write(content)
    #     print(f"Content saved to {file_path}")

    # def load_textarea_content(self, filename='commands.txt'):
    #     """텍스트영역 내용 로드"""
    #     file_path = os.path.join(dir_preset, filename)
    #     try:
    #         with open(file_path, 'r', encoding='utf-8') as file:
    #             content = file.read()
    #         self.command_list.clear()
    #         for line in content.splitlines():
    #             line = line.strip()
    #             if line:
    #                 self.add_checkable_item(line)
    #         print(f"Content loaded from {file_path}")
    #     except FileNotFoundError:
    #         print(f"File not found: {file_path}")

    # ========== 번들 관련 메서드들 ==========
    def save_bundles(self):
        """번들 저장 - 현재 파일이 있으면 바로 저장, 없으면 다른이름으로 저장"""
        if self.current_file_path:
            # 현재 파일이 있으면 바로 저장
            file_path = self.current_file_path
        else:
            # 현재 파일이 없으면 다른이름으로 저장과 같은 동작
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Bundles",
                os.path.join(bundles_dir, "bundles.json"),
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # 새로 저장한 파일을 현재 파일로 설정
            self.current_file_path = file_path
        
        try:
            save_data = {
                "bundles": self.bundles,
                "command_list": []
            }
            
            for i in range(self.command_list.count()):
                item = self.command_list.item(i)
                item_text = item.text()
                bundle_name = self._parse_bundle_display(item_text)
                is_checked = item.checkState() == Qt.Checked
                
                if bundle_name:
                    save_data["command_list"].append({
                        "type": "bundle",
                        "name": bundle_name,
                        "checked": is_checked
                    })
                else:
                    save_data["command_list"].append({
                        "type": "command",
                        "text": item_text,
                        "checked": is_checked
                    })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.log(f"Saved {len(self.bundles)} bundles to {file_path}")
            self.update_window_title()
        
        except Exception as e:
            self.log_error(f"Error saving bundles: {e}")

    def save_bundles_as(self):
        """다른이름으로 번들 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Bundles As...",
            os.path.join(bundles_dir, "bundles.json"),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # 새로 저장한 파일을 현재 파일로 설정
        self.current_file_path = file_path
        
        try:
            save_data = {
                "bundles": self.bundles,
                "command_list": []
            }
            
            for i in range(self.command_list.count()):
                item = self.command_list.item(i)
                item_text = item.text()
                bundle_name = self._parse_bundle_display(item_text)
                is_checked = item.checkState() == Qt.Checked
                
                if bundle_name:
                    save_data["command_list"].append({
                        "type": "bundle",
                        "name": bundle_name,
                        "checked": is_checked
                    })
                else:
                    save_data["command_list"].append({
                        "type": "command",
                        "text": item_text,
                        "checked": is_checked
                    })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.log(f"Saved {len(self.bundles)} bundles to {file_path}")
            self.update_window_title()
        
        except Exception as e:
            self.log_error(f"Error saving bundles as: {e}")

    def load_bundles(self):
        """번들 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Bundles",
            bundles_dir,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                load_data = json.load(f)
            
            if not isinstance(load_data, dict) or "bundles" not in load_data:
                self.log_error(f"Invalid bundle file format.")
                return
            
            if self.bundles or self.command_list.count() > 0:
                reply = QMessageBox.question(
                    self,
                    "Load Bundles",
                    "Do you want to merge with existing bundles?\n\n"
                    "Yes: Merge (keep existing)\n"
                    "No: Replace (clear existing)\n"
                    "Cancel: Abort",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.No:
                    self.bundles.clear()
                    self.command_list.clear()
            
            loaded_bundles = load_data.get("bundles", {})
            for bundle_name, structs in loaded_bundles.items():
                if bundle_name in self.bundles:
                    resp = QMessageBox.question(
                        self,
                        "Overwrite Bundle?",
                        f"Bundle '{bundle_name}' already exists. Overwrite?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if resp != QMessageBox.Yes:
                        continue
                
                self.bundles[bundle_name] = structs
            
            command_list_data = load_data.get("command_list", [])
            if command_list_data:
                for item in command_list_data:
                    if item.get("type") == "bundle":
                        bundle_name = item.get("name")
                        if bundle_name in self.bundles:
                            count = len(self.bundles[bundle_name])
                            list_item = self.add_checkable_item(f"[BUNDLE] {bundle_name} ({count})")
                            # 저장된 체크 상태가 있으면 적용
                            if "checked" in item:
                                list_item.setCheckState(Qt.Checked if item["checked"] else Qt.Unchecked)
                    elif item.get("type") == "command":
                        text = item.get("text", "")
                        if text:
                            list_item = self.add_checkable_item(text)
                            # 저장된 체크 상태가 있으면 적용
                            if "checked" in item:
                                list_item.setCheckState(Qt.Checked if item["checked"] else Qt.Unchecked)
            
            
            self.log(f"Loaded {len(loaded_bundles)} bundles from {file_path}")
            
            # 성공적으로 불러온 파일을 현재 파일로 설정
            self.current_file_path = file_path
            self.update_window_title()

        
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON format:\n{e}")
        except Exception as e:
            self.log_error(f"Failed to load bundles:\n{e}")
            print(f"Error loading bundles: {e}")

    def new_file(self):
        """새 파일 생성"""
        if self.bundles or self.command_list.count() > 0:
            reply = QMessageBox.question(
                self,
                "New File",
                "현재 작업 내용이 있습니다. 저장하지 않은 변경사항은 사라집니다.\n\n새 파일을 만드시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # 모든 내용 초기화
        self.bundles.clear()
        self.command_list.clear()
        self.current_file_path = None
        self.update_window_title()
        self.log("새 파일이 생성되었습니다.")

    def update_window_title(self):
        """윈도우 제목 업데이트"""
        base_title = 'Bundle Editor'
        if self.current_file_path:
            filename = os.path.basename(self.current_file_path)
            self.setWindowTitle(f'{base_title} - {filename}')
        else:
            self.setWindowTitle(f'{base_title} - [새 파일]')

    def log(self, message):
        """로그 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        msg_with_time = f"{timestamp} {message}"
        self.log_lines.append(msg_with_time)
        self.log_box.append(msg_with_time)
        print(msg_with_time)
        if len(self.log_lines) > 3:
            self.log_lines.pop(0)

    def log_error(self, message):
        """에러 로그 추가 (빨간색)"""
        from datetime import datetime
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        msg_with_time = f"{timestamp} {message}"
        self.log_lines.append(msg_with_time)
        self.log_box.append(f'<span style="color:red;">{msg_with_time}</span>')
        print(msg_with_time)
        if len(self.log_lines) > 3:
            self.log_lines.pop(0)

    def init_mouse_tracker(self):
        """마우스 위치 실시간 추적 초기화"""
        self.mouse_tracking_enabled = False  # 초기 상태는 OFF
        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self.update_mouse_position)
        self.mouse_timer.start(100)  # 100ms마다 업데이트 (10FPS)

    def update_mouse_position(self):
        """마우스 위치 업데이트"""
        if not self.mouse_tracking_enabled:
            return
            
        try:
            # 현재 마우스 위치 가져오기
            x, y = pag.position()
            
            # 선택된 윈도우 정보 가져오기
            selected_window = self.window_dropdown.currentText()
            
            if selected_window:
                try:
                    # 윈도우 좌표 정보 가져오기
                    windows = gw.getWindowsWithTitle(selected_window)
                    if windows:
                        window = windows[0]
                        win_x, win_y, win_w, win_h = window.left, window.top, window.width, window.height
                        
                        # 윈도우 내 상대 좌표 계산
                        rel_x = x - win_x
                        rel_y = y - win_y
                        
                        # 마우스가 윈도우 내부에 있는지 확인
                        if 0 <= rel_x <= win_w and 0 <= rel_y <= win_h:
                            # 윈도우 내부에 있을 때
                            self.coord_label.setText(
                                f"Mouse: ({x}, {y}) | Window: ({win_x}, {win_y}, {win_w}, {win_h}) | Relative: ({rel_x}, {rel_y})"
                            )
                        else:
                            # 윈도우 외부에 있을 때
                            self.coord_label.setText(
                                f"Mouse: ({x}, {y}) | Window: ({win_x}, {win_y}, {win_w}, {win_h}) | Outside window"
                            )
                    else:
                        # 윈도우를 찾지 못했을 때
                        self.coord_label.setText(f"Mouse: ({x}, {y}) | Window not found")
                except Exception:
                    # 윈도우 정보 가져오기 실패
                    self.coord_label.setText(f"Mouse: ({x}, {y}) | Window info unavailable")
            else:
                # 윈도우가 선택되지 않았을 때
                self.coord_label.setText(f"Mouse: ({x}, {y}) | No window selected")
                
        except Exception as e:
            # 마우스 위치 가져오기 실패
            self.coord_label.setText(f"Mouse tracking error: {e}")

    def toggle_mouse_tracking(self):
        """마우스 추적 켜기/끄기"""
        self.mouse_tracking_enabled = not self.mouse_tracking_enabled
        if self.mouse_tracking_enabled:
            self.coord_label.setText("Mouse tracking enabled")
        else:
            self.coord_label.setText("Mouse tracking disabled")
    
    def toggle_mouse_tracking_button(self):
        """버튼을 통한 마우스 추적 켜기/끄기"""
        self.mouse_tracking_enabled = not self.mouse_tracking_enabled
        
        if self.mouse_tracking_enabled:
            self.mouse_track_button.setText('Mouse ON')
            self.coord_label.setText("Mouse tracking enabled - Move your mouse!")
        else:
            self.mouse_track_button.setText('Mouse OFF')
            self.coord_label.setText("Mouse tracking disabled")

    # ========== 체크박스 기능 관련 메서드들 ==========
    def add_checkable_item(self, text):
        """체크박스가 있는 아이템을 command_list에 추가"""
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)  # 기본적으로 체크됨
        self.command_list.addItem(item)
        return item

    def show_context_menu(self, position):
        """우클릭 컨텍스트 메뉴 표시"""
        menu = QMenu(self)
        
        select_all_action = QAction("전체 선택", self)
        select_all_action.triggered.connect(self.select_all_items)
        menu.addAction(select_all_action)
        
        deselect_all_action = QAction("전체 해제", self)
        deselect_all_action.triggered.connect(self.deselect_all_items)
        menu.addAction(deselect_all_action)
        
        menu.exec_(self.command_list.mapToGlobal(position))

    def select_all_items(self):
        """모든 아이템 체크"""
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            item.setCheckState(Qt.Checked)

    def deselect_all_items(self):
        """모든 아이템 체크 해제"""
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            item.setCheckState(Qt.Unchecked)

    def _extract_test_title_from_bundles(self):
        """현재 체크된 번들명에서 테스트 제목 추출 (파일명의 날짜 앞쪽 부분)"""
        try:
            for i in range(self.command_list.count()):
                item = self.command_list.item(i)
                # 체크된 아이템만 처리
                if item.checkState() == Qt.Checked:
                    item_text = item.text()
                    bundle_name = self._parse_bundle_display(item_text)
                    if bundle_name:
                        # 파일명에서 날짜 패턴 이전의 부분 추출
                        import re
                        # 날짜 패턴들: YYYYMMDD, YYYY-MM-DD, YY-MM-DD, YYMMDD 등
                        date_patterns = [
                            r'_?\d{8}',  # _20241014 또는 20241014
                            r'_?\d{4}-\d{2}-\d{2}',  # _2024-10-14 또는 2024-10-14
                            r'_?\d{2}-\d{2}-\d{2}',  # _24-10-14 또는 24-10-14
                            r'_?\d{6}',  # _241014 또는 241014
                            r'_?\d{4}\d{2}\d{2}',  # _20241014
                            r'\.json$'  # .json 확장자
                        ]
                        
                        title = bundle_name
                        for pattern in date_patterns:
                            title = re.split(pattern, title)[0]
                        
                        # 언더스코어나 하이픈으로 끝나면 제거
                        title = title.rstrip('_-')
                        
                        if title:
                            return title
            
            return "기본테스트"  # 기본값
            
        except Exception as e:
            print(f"테스트 제목 추출 중 오류: {e}")
            return "테스트"
    
    # ========== 스케줄링 관련 메서드들 ==========
    def open_schedule_dialog(self):
        """스케줄 설정 다이얼로그 열기"""
        # 현재 선택된 명령어들을 가져오기
        commands = []
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            if item.checkState() == Qt.Checked:
                item_text = item.text()
                bundle_name = self._parse_bundle_display(item_text)
                if bundle_name and bundle_name in self.bundles:
                    # 번들인 경우 개별 명령어들로 확장
                    bundle_structs = self.bundles[bundle_name]
                    for struct in bundle_structs:
                        is_checked = struct.get('checked', True)
                        if is_checked:
                            commands.append(struct.get('raw', ''))
                else:
                    commands.append(item_text.split('#')[0].strip())
        
        if not commands:
            QMessageBox.warning(self, "Schedule", "스케줄할 명령어를 선택해주세요.")
            return
        
        # 스케줄 다이얼로그 열기
        dialog = ScheduleDialog(commands, self.schedule_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_schedule_status()
    
    def execute_scheduled_command(self, command: str):
        """스케줄된 명령어 실행 (스케줄러 엔진에서 호출)"""
        try:
            print(f"[스케줄] 명령어 실행: {command}")
            
            # 기존 명령어 처리기를 사용하여 실행
            self.command_processor.process_command(command.strip())
            
        except Exception as e:
            print(f"[스케줄] 명령어 실행 실패: {e}")
            raise
    
    def update_schedule_status(self):
        """스케줄 상태 라벨 업데이트"""
        try:
            enabled_schedules = self.schedule_manager.get_enabled_schedules()
            count = len(enabled_schedules)
            
            if count == 0:
                self.schedule_status_label.setText("Schedules: No active schedules")
            else:
                # 다음 실행 예정 시간 찾기
                next_runs = [s.next_run for s in enabled_schedules if s.next_run]
                if next_runs:
                    next_run = min(next_runs)
                    next_str = next_run.strftime("%H:%M")
                    self.schedule_status_label.setText(f"Schedules: {count} active | Next: {next_str}")
                else:
                    self.schedule_status_label.setText(f"Schedules: {count} active")
                    
        except Exception as e:
            print(f"스케줄 상태 업데이트 오류: {e}")
            self.schedule_status_label.setText("Schedules: Error")
    
    def toggle_keep_alive(self):
        """Keep-alive 토글"""
        try:
            if is_keep_alive_running():
                stop_keep_alive()
                print("Keep-alive 수동 중지됨")
            else:
                start_keep_alive(interval_minutes=12)
                print("Keep-alive 수동 시작됨")
            
            self.update_keep_alive_status()
        except Exception as e:
            print(f"Keep-alive 토글 오류: {e}")
            QMessageBox.warning(self, "Error", f"Keep-alive 토글 실패: {e}")
    
    def update_keep_alive_status(self):
        """Keep-alive 상태 UI 업데이트"""
        try:
            if is_keep_alive_running():
                self.keep_alive_button.setText("Keep-Alive: ON")
                self.keep_alive_button.setStyleSheet("font-size: 10px; padding: 2px 8px; background-color: #4CAF50; color: white;")
                self.keep_alive_status_label.setText("PC 잠금 방지: 활성 (12분 간격)")
                self.keep_alive_status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
            else:
                self.keep_alive_button.setText("Keep-Alive: OFF")
                self.keep_alive_button.setStyleSheet("font-size: 10px; padding: 2px 8px;")
                self.keep_alive_status_label.setText("PC 잠금 방지: 비활성")
                self.keep_alive_status_label.setStyleSheet("color: #666; font-size: 10px;")
        except Exception as e:
            print(f"Keep-alive 상태 업데이트 오류: {e}")
            self.keep_alive_status_label.setText("PC 잠금 방지: 오류")
    
    # ==================== 업데이트 관련 메서드 ====================
    
    def check_for_updates_on_startup(self):
        """시작 시 자동 업데이트 확인 (비동기, 조용히)"""
        def callback(has_update, info, error_msg):
            if error_msg:
                print(f"업데이트 확인 실패: {error_msg}")
            elif has_update:
                print(f"새 버전 발견: {info['version']}")
                # 자동으로 알림 표시하지 않고 로그만 남김
                # 사용자가 원하면 메뉴에서 수동으로 확인 가능
        
        self.auto_updater.check_updates_async(callback)
    
    def check_for_updates(self):
        """업데이트 확인 (메뉴에서 수동 호출)"""
        print("업데이트 확인 중...")
        
        def callback(has_update, info, error_msg):
            # 비동기 스레드에서 호출되므로 메인 스레드로 전환
            def show_result():
                if error_msg:
                    # 에러 발생
                    QMessageBox.warning(
                        self,
                        "업데이트 확인 실패",
                        f"업데이트를 확인할 수 없습니다.\n\n{error_msg}"
                    )
                elif has_update:
                    # 새 버전 발견
                    dialog = UpdateNotificationDialog(info, self)
                    result = dialog.exec_()
                    
                    if result == QDialog.Accepted:
                        # 지금 업데이트 선택
                        self.start_update_download(info)
                    elif result == 2:  # Skip
                        print(f"버전 {info['version']} 건너뛰기")
                else:
                    # 최신 버전 사용 중
                    QMessageBox.information(
                        self,
                        "업데이트 확인",
                        "현재 최신 버전을 사용하고 있습니다."
                    )
            
            # 메인 스레드에서 실행
            QTimer.singleShot(0, show_result)
        
        self.auto_updater.check_updates_async(callback)
    
    def start_update_download(self, update_info):
        """업데이트 다운로드 시작"""
        # 다운로드 진행률 다이얼로그 표시
        progress_dialog = DownloadProgressDialog(self)
        progress_dialog.show()
        
        def progress_callback(received, total):
            """진행률 콜백"""
            progress_dialog.update_progress(received, total)
        
        def completion_callback(success):
            """완료 콜백"""
            if success:
                progress_dialog.download_complete()
                QMessageBox.information(
                    self,
                    "업데이트 설치",
                    "업데이트가 다운로드되었습니다.\n앱을 재시작하여 업데이트를 적용합니다."
                )
                # install_update 메서드가 자동으로 재시작함
            else:
                progress_dialog.close()
                if not progress_dialog.cancelled:
                    QMessageBox.warning(
                        self,
                        "업데이트 실패",
                        "업데이트 다운로드에 실패했습니다.\n나중에 다시 시도해주세요."
                    )
        
        # 다운로드 및 설치 시작
        self.auto_updater.download_and_install(progress_callback, completion_callback)
    
    def show_about_dialog(self):
        """정보 다이얼로그 표시"""
        dialog = AboutDialog(self)
        dialog.exec_()
    
    # ==================== 종료 관련 ====================
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 스케줄러 정리"""
        try:
            print("애플리케이션 종료 중...")
            
            # 스케줄러 엔진 정지
            if hasattr(self, 'scheduler_engine'):
                self.scheduler_engine.stop()
            
            # 스케줄 데이터 저장
            if hasattr(self, 'schedule_manager'):
                self.schedule_manager.save_schedules()
            
            event.accept()
        except Exception as e:
            print(f"종료 중 오류: {e}")
            event.accept()


class ScheduleDialog(QDialog):
    """개선된 스케줄 관리 다이얼로그"""
    
    def __init__(self, commands, schedule_manager, parent=None):
        super().__init__(parent)
        self.commands = commands
        self.schedule_manager = schedule_manager
        self.parent_widget = parent  # 부모 위젯 참조 저장
        self.editing_schedule = None  # 편집 중인 스케줄
        self.setWindowTitle("Schedule Manager")
        self.setModal(True)
        self.resize(700, 600)
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        
        # 탭 1: 새 스케줄 추가
        self.add_tab = QWidget()
        self.init_add_tab()
        self.tab_widget.addTab(self.add_tab, "새 스케줄 추가")
        
        # 탭 2: 기존 스케줄 관리
        self.manage_tab = QWidget()
        self.init_manage_tab()
        self.tab_widget.addTab(self.manage_tab, "스케줄 관리")
        
        layout.addWidget(self.tab_widget)
        
        # 닫기 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def init_add_tab(self):
        """새 스케줄 추가 탭 초기화"""
        layout = QVBoxLayout()
        
        # 명령어 표시 (스크롤 가능)
        commands_label = QLabel("Commands to schedule:")
        layout.addWidget(commands_label)
        
        self.commands_display = QTextEdit()
        commands_text = "\n".join([f"{i+1}. {cmd}" for i, cmd in enumerate(self.commands)])
        self.commands_display.setPlainText(commands_text)
        self.commands_display.setReadOnly(True)
        self.commands_display.setMaximumHeight(120)
        self.commands_display.setStyleSheet("background: #f5f5f5; border: 1px solid #ddd;")
        layout.addWidget(self.commands_display)
        
        # 스케줄 이름
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Schedule Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter schedule name...")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 스케줄 타입
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Repeat Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Once", "Daily", "Weekly", "Monthly", "Interval"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # 날짜 선택 (Once용)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:"))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())  # 오늘 날짜로 설정
        self.date_input.setCalendarPopup(True)
        date_layout.addWidget(self.date_input)
        layout.addLayout(date_layout)
        self.date_layout = date_layout
        
        # 시간 선택
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time:"))
        self.time_input = QTimeEdit()
        # 현재 시간으로 설정 (분은 0으로 맞춤)
        current_time = QTime.currentTime()
        current_time = QTime(current_time.hour(), 0)  # 분을 0으로 설정
        self.time_input.setTime(current_time)
        time_layout.addWidget(self.time_input)
        layout.addLayout(time_layout)
        
        # 요일 선택 (Weekly용)
        days_layout = QVBoxLayout()
        days_layout.addWidget(QLabel("Days of Week:"))
        self.day_checkboxes = []
        days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_row = QHBoxLayout()
        for i, day_name in enumerate(days_names):
            checkbox = QCheckBox(day_name)
            if i < 5:  # 월-금 기본 선택
                checkbox.setChecked(True)
            self.day_checkboxes.append(checkbox)
            days_row.addWidget(checkbox)
        days_layout.addLayout(days_row)
        layout.addLayout(days_layout)
        self.days_layout = days_layout
        
        # 간격 설정 (Interval용)
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval (minutes):"))
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 1440)  # 1분~24시간
        self.interval_input.setValue(60)  # 1시간 기본값
        interval_layout.addWidget(self.interval_input)
        layout.addLayout(interval_layout)
        self.interval_layout = interval_layout
        
        # 추가 버튼
        add_button = QPushButton("Add Schedule")
        add_button.clicked.connect(self.add_schedule)
        layout.addWidget(add_button)
        
        layout.addStretch()
        self.add_tab.setLayout(layout)
        
        # 초기 상태 설정
        self.on_type_changed("Once")
    
    def init_manage_tab(self):
        """기존 스케줄 관리 탭 초기화"""
        layout = QVBoxLayout()
        
        # 스케줄 목록 테이블
        self.schedules_table = QTableWidget()
        self.schedules_table.setColumnCount(6)
        self.schedules_table.setHorizontalHeaderLabels(["Name", "Type", "Time", "Next Run", "Status", "Commands"])
        
        # 테이블 헤더 설정
        header = self.schedules_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Time
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Next Run
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.Stretch)          # Commands
        
        self.schedules_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.schedules_table)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.refresh_schedules)
        button_layout.addWidget(self.refresh_button)
        
        self.edit_button = QPushButton("편집")
        self.edit_button.clicked.connect(self.edit_schedule)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)
        
        self.toggle_button = QPushButton("활성화/비활성화")
        self.toggle_button.clicked.connect(self.toggle_schedule)
        self.toggle_button.setEnabled(False)
        button_layout.addWidget(self.toggle_button)
        
        self.delete_button = QPushButton("삭제")
        self.delete_button.clicked.connect(self.delete_schedule)
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.manage_tab.setLayout(layout)
        
        # 테이블 선택 변경 시 버튼 활성화/비활성화
        self.schedules_table.selectionModel().selectionChanged.connect(self.on_schedule_selected)
        
        # 초기 데이터 로드
        self.refresh_schedules()
    
    def on_type_changed(self, type_text):
        """스케줄 타입 변경 시 UI 업데이트"""
        # 모든 레이아웃 숨기기
        for i in range(self.date_layout.count()):
            widget = self.date_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(False)
        
        for i in range(self.days_layout.count()):
            item = self.days_layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(False)
            elif item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if widget:
                        widget.setVisible(False)
        
        for i in range(self.interval_layout.count()):
            widget = self.interval_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(False)
        
        # 타입별로 필요한 UI만 표시
        if type_text == "Once":
            for i in range(self.date_layout.count()):
                widget = self.date_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
        elif type_text == "Weekly":
            for i in range(self.days_layout.count()):
                item = self.days_layout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(True)
                elif item.layout():
                    for j in range(item.layout().count()):
                        widget = item.layout().itemAt(j).widget()
                        if widget:
                            widget.setVisible(True)
        elif type_text == "Interval":
            for i in range(self.interval_layout.count()):
                widget = self.interval_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
    
    def add_schedule(self):
        """새 스케줄 추가"""
        try:
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Error", "Please enter schedule name.")
                return
            
            schedule_type_text = self.type_combo.currentText()
            schedule_type = {
                "Once": ScheduleType.ONCE,
                "Daily": ScheduleType.DAILY,
                "Weekly": ScheduleType.WEEKLY,
                "Monthly": ScheduleType.MONTHLY,
                "Interval": ScheduleType.INTERVAL
            }[schedule_type_text]
            
            schedule_time = self.time_input.time().toString("HH:mm")
            
            # 타입별 추가 옵션
            kwargs = {}
            
            if schedule_type == ScheduleType.ONCE:
                kwargs['date'] = self.date_input.date().toString("yyyy-MM-dd")
            elif schedule_type == ScheduleType.WEEKLY:
                selected_days = []
                for i, checkbox in enumerate(self.day_checkboxes):
                    if checkbox.isChecked():
                        selected_days.append(i)
                if not selected_days:
                    QMessageBox.warning(self, "Error", "Please select at least one day.")
                    return
                kwargs['days_of_week'] = selected_days
            elif schedule_type == ScheduleType.INTERVAL:
                kwargs['interval_minutes'] = self.interval_input.value()
            
            # 편집 모드인지 확인
            if self.editing_schedule:
                # 기존 스케줄 업데이트
                self.editing_schedule.name = name
                self.editing_schedule.schedule_type = schedule_type
                self.editing_schedule.schedule_time = schedule_time
                self.editing_schedule.date = kwargs.get('date')
                self.editing_schedule.days_of_week = kwargs.get('days_of_week', [])
                self.editing_schedule.interval_minutes = kwargs.get('interval_minutes', 60)
                self.editing_schedule.calculate_next_run()
                
                if self.schedule_manager.update_schedule(self.editing_schedule):
                    QMessageBox.information(self, "Success", f"Schedule '{name}' updated successfully!")
                    self.editing_schedule = None
                    self.clear_form()
                    self.refresh_schedules()
                    self.update_parent_status()
                else:
                    QMessageBox.warning(self, "Error", "Failed to update schedule.")
            else:
                # 새 스케줄 생성
                schedule = Schedule(name, self.commands, schedule_type, schedule_time, **kwargs)
                
                if self.schedule_manager.add_schedule(schedule):
                    QMessageBox.information(self, "Success", f"Schedule '{name}' created successfully!")
                    self.clear_form()
                    self.refresh_schedules()
                    self.update_parent_status()
                else:
                    QMessageBox.warning(self, "Error", "Failed to create schedule.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating/updating schedule: {e}")
    
    def clear_form(self):
        """폼 초기화"""
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.date_input.setDate(QDate.currentDate())
        current_time = QTime.currentTime()
        current_time = QTime(current_time.hour(), 0)
        self.time_input.setTime(current_time)
        for checkbox in self.day_checkboxes:
            checkbox.setChecked(checkbox == self.day_checkboxes[0] or checkbox == self.day_checkboxes[1] or checkbox == self.day_checkboxes[2] or checkbox == self.day_checkboxes[3] or checkbox == self.day_checkboxes[4])
        self.interval_input.setValue(60)
        self.editing_schedule = None
        
    def refresh_schedules(self):
        """스케줄 목록 새로고침"""
        schedules = self.schedule_manager.get_all_schedules()
        self.schedules_table.setRowCount(len(schedules))
        
        for i, schedule in enumerate(schedules):
            # Name
            self.schedules_table.setItem(i, 0, QTableWidgetItem(schedule.name))
            
            # Type
            type_text = schedule.schedule_type.value.title()
            self.schedules_table.setItem(i, 1, QTableWidgetItem(type_text))
            
            # Time
            self.schedules_table.setItem(i, 2, QTableWidgetItem(schedule.schedule_time))
            
            # Next Run
            if schedule.next_run:
                next_run_text = schedule.next_run.strftime("%Y-%m-%d %H:%M")
            else:
                next_run_text = "N/A"
            self.schedules_table.setItem(i, 3, QTableWidgetItem(next_run_text))
            
            # Status
            status_text = schedule.status.value.title()
            self.schedules_table.setItem(i, 4, QTableWidgetItem(status_text))
            
            # Commands (처음 2개만 표시)
            commands_preview = ", ".join(schedule.commands[:2])
            if len(schedule.commands) > 2:
                commands_preview += f" ... (+{len(schedule.commands)-2} more)"
            self.schedules_table.setItem(i, 5, QTableWidgetItem(commands_preview))
            
            # 스케줄 ID를 데이터로 저장
            self.schedules_table.item(i, 0).setData(Qt.UserRole, schedule.id)
    
    def on_schedule_selected(self):
        """스케줄 선택 시 버튼 활성화"""
        selected = len(self.schedules_table.selectionModel().selectedRows()) > 0
        self.edit_button.setEnabled(selected)
        self.toggle_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)
    
    def get_selected_schedule(self):
        """선택된 스케줄 반환"""
        selected_rows = self.schedules_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        schedule_id = self.schedules_table.item(row, 0).data(Qt.UserRole)
        return self.schedule_manager.get_schedule(schedule_id)
    
    def edit_schedule(self):
        """스케줄 편집"""
        schedule = self.get_selected_schedule()
        if not schedule:
            return
        
        # 편집 모드로 전환
        self.editing_schedule = schedule
        
        # 폼에 기존 데이터 설정
        self.name_input.setText(schedule.name)
        
        # 타입 설정
        type_mapping = {
            ScheduleType.ONCE: "Once",
            ScheduleType.DAILY: "Daily", 
            ScheduleType.WEEKLY: "Weekly",
            ScheduleType.MONTHLY: "Monthly",
            ScheduleType.INTERVAL: "Interval"
        }
        self.type_combo.setCurrentText(type_mapping[schedule.schedule_type])
        
        # 시간 설정
        time_parts = schedule.schedule_time.split(":")
        self.time_input.setTime(QTime(int(time_parts[0]), int(time_parts[1])))
        
        # 타입별 옵션 설정
        if schedule.schedule_type == ScheduleType.ONCE and schedule.date:
            date_parts = schedule.date.split("-")
            self.date_input.setDate(QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])))
        elif schedule.schedule_type == ScheduleType.WEEKLY:
            for i, checkbox in enumerate(self.day_checkboxes):
                checkbox.setChecked(i in schedule.days_of_week)
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            self.interval_input.setValue(schedule.interval_minutes)
        
        # 첫 번째 탭으로 전환
        self.tab_widget.setCurrentIndex(0)
        
        QMessageBox.information(self, "Edit Mode", f"Editing schedule '{schedule.name}'. Make changes and click 'Add Schedule' to save.")
    
    def toggle_schedule(self):
        """스케줄 활성화/비활성화"""
        schedule = self.get_selected_schedule()
        if not schedule:
            return
        
        if schedule.status == ScheduleStatus.ENABLED:
            schedule.status = ScheduleStatus.DISABLED
        else:
            schedule.status = ScheduleStatus.ENABLED
        
        if self.schedule_manager.update_schedule(schedule):
            self.refresh_schedules()
            self.update_parent_status()
        else:
            QMessageBox.warning(self, "Error", "Failed to update schedule status.")
    
    def delete_schedule(self):
        """스케줄 삭제"""
        schedule = self.get_selected_schedule()
        if not schedule:
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete schedule '{schedule.name}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.schedule_manager.remove_schedule(schedule.id):
                self.refresh_schedules()
                self.update_parent_status()
                QMessageBox.information(self, "Success", f"Schedule '{schedule.name}' deleted successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete schedule.")
    
    def update_parent_status(self):
        """부모 위젯의 스케줄 상태 업데이트"""
        if self.parent_widget and hasattr(self.parent_widget, 'update_schedule_status'):
            self.parent_widget.update_schedule_status()


# Main function
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PbbAutoApp()
    ex.show()
    sys.exit(app.exec_())
