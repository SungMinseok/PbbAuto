"""
개선된 명령어 프로세서 - 명령어 레지스트리 사용
기존 296줄 → 25줄로 대폭 축소! 🎉
"""

# 로그 설정을 가장 먼저 import
import logger_setup

import os
from command_registry import get_command


class CommandProcessor:
    """개선된 명령어 처리기 - 레지스트리 기반"""
    
    def __init__(self):
        self.stop_flag = False
        self.main_app = None  # 메인 앱 참조 추가
        # 프로세서 상태 (명령어 간 데이터 공유용)
        self.state = {
            'screenshot_path': None,
            'extracted_text': '',
            'expected_text': '',
            'last_result': 'N/A',
            'checklist_file': 'checklist.xlsx',
            'iteration_count': 1,  # 현재 반복 횟수 (1-based)
            'test_results': [],  # 테스트 결과 저장용 리스트
            'test_session_start': None,  # 테스트 세션 시작 시간
            'test_session_title': None   # 테스트 세션 제목 (파일명 기반)
        }
    
    def set_main_app(self, main_app):
        """메인 앱 참조 설정"""
        self.main_app = main_app
    
    def get_current_window_coords(self):
        """현재 선택된 윈도우의 좌표를 동적으로 가져오기"""
        if not self.main_app:
            return None
            
        try:
            import pygetwindow as gw
            
            selected_window = self.main_app.window_dropdown.currentText()
            if not selected_window:
                return None
                
            windows = gw.getWindowsWithTitle(selected_window)
            if windows:
                window = windows[0]
                coords = (window.left, window.top, window.width, window.height)
                print(f"현재 윈도우 좌표: {selected_window} → {coords}")
                return coords
        except Exception as e:
            print(f"윈도우 좌표 가져오기 실패: {e}")
        
        return None
    
    def process_command(self, command_string, window_coords=None):
        """명령어 처리 - 동적 윈도우 좌표 지원"""
        # 중지 플래그 체크
        if self.stop_flag:
            print("⚠️ 실행 중지됨 - 명령어 처리 중단")
            return
            
        parts = command_string.split()
        if not parts:
            return
            
        action = parts[0].strip()
        print(f'Executing action: {action}')
        
        # 레지스트리에서 명령어 찾기
        command = get_command(action)
        if command:
            # 중지 플래그 한 번 더 체크
            if self.stop_flag:
                print("⚠️ 실행 중지됨 - 명령어 실행 중단")
                return
                
            # 파라미터 파싱
            params = command.parse_params(parts[1:])
            
            # CommandProcessor 인스턴스를 명령어에 전달 (실시간 stop_flag 체크를 위해)
            params['processor'] = self
            
            # 동적 윈도우 좌표 가져오기 (기존 window_coords보다 우선)
            current_coords = self.get_current_window_coords()
            if current_coords:
                # 현재 선택된 윈도우 좌표 사용 (state 딕셔너리를 전달)
                command.execute(params, current_coords, self.state)
                print(f"✓ 동적 윈도우 좌표 사용: {current_coords}")
            else:
                # 기존 좌표 또는 None 사용 (state 딕셔너리를 전달)
                command.execute(params, window_coords, self.state)
                if window_coords:
                    print(f"✓ 기존 윈도우 좌표 사용: {window_coords}")
                else:
                    print("⚠️ 윈도우 좌표 없음")
        else:
            print(f"Unknown command: {action}")
    
    # 기존의 수십 개 _handle_xxx 메서드들이 모두 사라졌습니다! 🎉
    # 새로운 명령어를 추가할 때 더 이상 이 파일을 수정할 필요가 없습니다!