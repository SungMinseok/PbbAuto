import os
import sys

# 디렉토리 설정 - PyInstaller exe 환경 고려
def get_app_dir():
    """애플리케이션 실행 디렉토리 반환 (exe/개발환경 모두 고려)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 exe 환경
        return os.path.dirname(sys.executable)
    else:
        # 일반 Python 스크립트 환경
        return os.path.dirname(os.path.abspath(__file__))

current_dir = get_app_dir()

screenshot_dir = os.path.join(current_dir, 'screenshot')
if not os.path.exists(screenshot_dir):
    os.makedirs(screenshot_dir)

# cl_dir = os.path.join(current_dir, 'checklist')
# if not os.path.exists(cl_dir):
#     os.makedirs(cl_dir)
    
# dir_preset = 'preset'
# if not os.path.exists(dir_preset):
#     os.makedirs(dir_preset)

bundles_dir = os.path.join(current_dir, 'bundles')
if not os.path.exists(bundles_dir):
    os.makedirs(bundles_dir)

test_results_dir = os.path.join(current_dir, 'test_results')
if not os.path.exists(test_results_dir):
    os.makedirs(test_results_dir)

# 전역 변수
recent_txt = "0"

# 지원되는 액션 목록 - 기존 방식으로 유지 (circular import 방지)
SUPPORTED_ACTIONS = [
    'press', 'write', 'wait', 'screenshot', 'click', 
    'drag',  # ← 새 명령어! 이제 수동으로 추가해야 함
    'cheat', 'i2s', 'i2skr', 'validate', 'export', 'waituntil',
    'testtext', 'showresults', 'exportexcel', 'runapp'  # ← 새로운 테스트 관련 명령어들
]
# Note: 새 명령어를 추가할 때 여기도 업데이트해야 합니다

# OCR 언어 설정
OCR_LANGUAGES = {
    'i2s': 'eng',
    'i2skr': 'kor'
}

# Tesseract 기본 경로들
DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
