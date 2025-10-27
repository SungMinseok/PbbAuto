# 로그 설정을 가장 먼저 import
import logger_setup

import os
import time
import json
import threading
import pyautogui as pag
import pytesseract
from datetime import datetime
from constants import current_dir, screenshot_dir, DEFAULT_TESSERACT_PATHS
from tes import image_to_text_with_fallback


def set_pytesseract_cmd(path):
    """Set pytesseract.tesseract_cmd if the path looks valid."""
    if path and os.path.exists(path) and path.lower().endswith('tesseract.exe'):
        pytesseract.pytesseract.tesseract_cmd = path
        return True
    return False


def take_screenshot():
    """Take a full-screen screenshot."""
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    screenshot_path = os.path.join(screenshot_dir, f"{timestamp}.jpg")
    
    screenshot = pag.screenshot()
    screenshot.save(screenshot_path)
    return screenshot_path


def take_screenshot_with_coords(x, y, w, h):
    """Take a screenshot at specified coordinates."""
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    screenshot_path = os.path.join(screenshot_dir, f"{timestamp}.jpg")
    
    screenshot = pag.screenshot(region=(x, y, w, h))
    screenshot.save(screenshot_path)
    return screenshot_path


def image_to_text(img_path="", lang='auto', expected_text=None, exact_match=False):
    """
    Convert the most recent screenshot to text.
    
    Args:
        img_path: 이미지 파일 경로 (비어있으면 최신 스크린샷 사용)
        lang: 언어 설정
            - 'auto': 자동 감지 (영어+한글 동시 시도, 권장)
            - 'kor': 한글 우선
            - 'eng': 영어만
        expected_text: 기대되는 텍스트 (선택사항, 조기 종료에 사용)
        exact_match: 완전일치 모드 여부 (expected_text와 함께 사용)
            
    Returns:
        추출된 텍스트 (실패 시 None 또는 빈 문자열)
    """
    if img_path == "":
        if not os.path.exists(screenshot_dir):
            print("Screenshot directory does not exist.")
            return None

        screenshots = sorted(
            [f for f in os.listdir(screenshot_dir) if f.endswith('.jpg')],
            key=lambda f: os.path.getmtime(os.path.join(screenshot_dir, f)),
            reverse=True
        )

        if not screenshots:
            print("No screenshots found.")
            return None

        img_path = os.path.join(screenshot_dir, screenshots[0])

    return image_to_text_with_fallback(img_path=img_path, lang=lang, preview=False, expected_text=expected_text, exact_match=exact_match)


def load_config():
    """Load config.json and set tesseract path. Returns True if loaded and set."""
    config_path = os.path.join(current_dir, 'config.json')
    if not os.path.exists(config_path):
        return False
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        tess_path = cfg.get('tesseract_path')
        if tess_path and set_pytesseract_cmd(tess_path):
            print(f"Loaded tesseract path from config: {tess_path}")
            return tess_path
    except Exception as e:
        print(f"Error loading config.json: {e}")
    return False


def save_config(tesseract_path):
    """Save current tesseract path to config.json."""
    config_path = os.path.join(current_dir, 'config.json')
    try:
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                try:
                    cfg = json.load(f)
                except Exception:
                    cfg = {}
        cfg['tesseract_path'] = tesseract_path
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"Saved tesseract path to config: {tesseract_path}")
        return True
    except Exception as e:
        print(f"Error saving config.json: {e}")
        return False


def auto_detect_tesseract():
    """Auto-detect tesseract installation."""
    for p in DEFAULT_TESSERACT_PATHS:
        if os.path.exists(p):
            set_pytesseract_cmd(p)
            print(f"Auto-detected tesseract at: {p}")
            return p
    return False


def calculate_adjusted_coordinates(x, y, window_coords, base_resolution=(2560, 1440)):
    """
    Calculate absolute (screen) coordinates using relative position within the window with ratio adjustment.
    
    Args:
        x, y: relative coordinates within the window (based on base_resolution)
        window_coords: (win_left, win_top, win_width, win_height) - current window coordinates
        base_resolution: (width, height) - reference resolution for coordinate calculation
    
    Returns:
        (absolute_x, absolute_y) - screen coordinates adjusted for window size ratio
    """
    x1, y1, w1, h1 = window_coords
    base_width, base_height = base_resolution
    
    # 현재 윈도우 크기와 기준 해상도의 비율 계산
    width_ratio = w1 / base_width
    height_ratio = h1 / base_height
    
    # 상대 좌표에 비율을 적용하여 조정
    adjusted_x = x1 + int(x * width_ratio)
    adjusted_y = y1 + int(y * height_ratio)
    
    # 디버깅 정보 출력 (필요시에만)
    if globals().get('DEBUG_COORDINATES', False):
        print(f"좌표 변환: ({x}, {y}) -> ({adjusted_x}, {adjusted_y})")
        print(f"윈도우 크기: {w1}x{h1}, 기준 해상도: {base_width}x{base_height}")
        print(f"비율: width={width_ratio:.3f}, height={height_ratio:.3f}")
    
    return adjusted_x, adjusted_y


def calculate_offset_coordinates(x, y, window_coords):
    """
    단순 윈도우 오프셋 좌표 계산 - 스케일링 없이 윈도우 시작점에 좌표를 더함
    
    Args:
        x, y: 윈도우 내 상대 좌표
        window_coords: (win_left, win_top, win_width, win_height) - 윈도우 좌표
    
    Returns:
        (absolute_x, absolute_y) - 화면 절대 좌표
    """
    x1, y1, w1, h1 = window_coords
    
    # 단순히 윈도우 시작점에 상대 좌표를 더함
    adjusted_x = x1 + x
    adjusted_y = y1 + y
    
    # 디버깅 정보 출력 (필요시에만)
    if globals().get('DEBUG_COORDINATES', False):
        print(f"[DEBUG] calculate_offset_coordinates 호출:")
        print(f"  - 입력 좌표: ({x}, {y})")
        print(f"  - 윈도우 좌표: {window_coords}")
        print(f"  - 결과 좌표: ({adjusted_x}, {adjusted_y}) (단순 오프셋)")
    
    return adjusted_x, adjusted_y


def test_coordinate_adjustment():
    """좌표 조정 함수의 작동 예시"""
    # 예시: 1920x1080 기준으로 설계된 좌표 (960, 540)가 
    # 실제 1280x720 윈도우에서 어떻게 조정되는지
    
    base_coords = (960, 540)  # 1920x1080의 중앙
    window_1280x720 = (0, 0, 1280, 720)  # 1280x720 윈도우
    window_1920x1080 = (0, 0, 1920, 1080)  # 1920x1080 윈도우
    
    print("=== 좌표 조정 테스트 ===")
    print(f"기준 좌표: {base_coords}")
    
    # 1280x720 윈도우에서의 조정
    adj_small = calculate_adjusted_coordinates(*base_coords, window_1280x720)
    print(f"1280x720 윈도우 -> {adj_small}")
    
    # 1920x1080 윈도우에서의 조정  
    adj_large = calculate_adjusted_coordinates(*base_coords, window_1920x1080)
    print(f"1920x1080 윈도우 -> {adj_large}")
    
    # 비율 계산
    ratio_small = (1280/1920, 720/1080)
    print(f"1280x720 비율: {ratio_small}")
    print(f"예상 좌표: ({960 * ratio_small[0]}, {540 * ratio_small[1]})")


def align_windows(windows, max_windows=4):
    """Align multiple windows in a grid layout."""
    screen_width, screen_height = pag.size()
    
    width = screen_width // 2
    height = int(width * 9 / 16) + 30
    
    positions = [
        (0, 0),           # 좌상단
        (width, 0),       # 우상단
        (0, height),      # 좌하단
        (width, height)   # 우하단
    ]
    
    for i, window in enumerate(windows[:max_windows]):
        x, y = positions[i]
        window.resizeTo(width, height)
        window.moveTo(x, y)
        try:
            window.activate()
        except:
            pass  # activate 실패 시 무시하고 계속 진행


class KeepAlive:
    """PC 자동 잠금 방지 클래스"""
    
    def __init__(self, interval_minutes=10):
        """
        Args:
            interval_minutes: Keep-alive 동작 간격 (분), 기본값 10분
        """
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.thread = None
        
    def start(self):
        """Keep-alive 시작"""
        if self.is_running:
            print("⚠️ Keep-alive가 이미 실행 중입니다.")
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
        self.thread.start()
        print(f"✅ Keep-alive 시작됨 (간격: {self.interval_minutes}분)")
        
    def stop(self):
        """Keep-alive 중지"""
        if not self.is_running:
            print("⚠️ Keep-alive가 실행되고 있지 않습니다.")
            return
            
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("🛑 Keep-alive 중지됨")
        
    def _keep_alive_loop(self):
        """Keep-alive 메인 루프"""
        import time
        
        while self.is_running:
            try:
                self._perform_keep_alive()
                # 간격만큼 대기 (1초씩 체크해서 중지 신호에 빠르게 반응)
                for _ in range(self.interval_minutes * 60):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Keep-alive 실행 중 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기 후 재시도
                
    def _perform_keep_alive(self):
        """실제 Keep-alive 동작 수행"""
        success = False
        
        # 방법 1: Windows API로 시스템 상태 유지
        try:
            import ctypes
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
            print("🔄 Windows API로 시스템 활성 상태 유지")
            success = True
        except Exception as e:
            print(f"Windows API 방법 실패: {e}")
            
        # 방법 2: 마우스 미세 움직임 (API 실패 시 백업)
        if not success:
            try:
                import pyautogui as pag
                current_pos = pag.position()
                # 1픽셀 이동 후 원위치
                pag.moveRel(1, 1)
                time.sleep(0.1)
                pag.moveTo(current_pos.x, current_pos.y)
                print("🖱️ 마우스 미세 움직임으로 활성 상태 유지")
                success = True
            except Exception as e:
                print(f"마우스 움직임 방법 실패: {e}")
                
        # 방법 3: Scroll Lock 토글 (마지막 백업)
        if not success:
            try:
                import pyautogui as pag
                pag.press('scrolllock')
                time.sleep(0.1)
                pag.press('scrolllock')  # 다시 토글해서 원상태 복구
                print("⌨️ Scroll Lock 토글로 활성 상태 유지")
                success = True
            except Exception as e:
                print(f"키보드 토글 방법 실패: {e}")
                
        if not success:
            print("⚠️ 모든 Keep-alive 방법이 실패했습니다.")


# 전역 Keep-alive 인스턴스
_global_keep_alive = None

def start_keep_alive(interval_minutes=10):
    """전역 Keep-alive 시작"""
    global _global_keep_alive
    if _global_keep_alive is None:
        _global_keep_alive = KeepAlive(interval_minutes)
    _global_keep_alive.start()
    
def stop_keep_alive():
    """전역 Keep-alive 중지"""
    global _global_keep_alive
    if _global_keep_alive:
        _global_keep_alive.stop()
        
def is_keep_alive_running():
    """Keep-alive 실행 상태 확인"""
    global _global_keep_alive
    return _global_keep_alive and _global_keep_alive.is_running


# ==================== 화면 밝기 조절 기능 ====================

_original_brightness = None  # 원래 밝기 저장용

def get_current_brightness():
    """현재 화면 밝기 가져오기 (0-100%) - 외장/내장 모니터 자동 감지"""
    try:
        # 우선 외장 모니터(DDC/CI) 시도
        from monitorcontrol import get_monitors
        for monitor in get_monitors():
            with monitor:
                brightness = monitor.get_luminance()
                print(f"현재 화면 밝기 (외장 모니터): {brightness}%")
                return brightness
    except Exception:
        pass

    try:
        # 내장 디스플레이 (CIM/WMI)
        import subprocess
        command = "(Get-CimInstance -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
        result = subprocess.run(['powershell', '-Command', command],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip().isdigit():
            brightness = int(result.stdout.strip())
            print(f"현재 화면 밝기 (내장 디스플레이): {brightness}%")
            return brightness
    except Exception:
        pass

    print("⚠️ 현재 밝기를 가져올 수 없어 기본값 80%로 사용합니다")
    return 80

def set_screen_brightness(brightness_percent):
    """화면 밝기 설정 (0-100%) - 외장/내장 모니터 자동 감지
    
    Args:
        brightness_percent: 0(완전 어둠) ~ 100(최대 밝기)
    
    Returns:
        bool: 성공 여부
    """
    global _original_brightness
    
    brightness_percent = max(0, min(100, int(brightness_percent)))
    if _original_brightness is None:
        _original_brightness = get_current_brightness()

    try:
        # 외장 모니터(DDC/CI) 시도
        try:
            from monitorcontrol import get_monitors
            for monitor in get_monitors():
                with monitor:
                    monitor.set_luminance(brightness_percent)
            print(f"✓ 외장 모니터 밝기를 {brightness_percent}%로 설정했습니다")
            return True
        except Exception:
            pass

        # 내장 디스플레이 (CIM)
        import subprocess
        command = f"""
$brightness = {brightness_percent}
$monitor = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods
if ($monitor) {{
    $monitor.WmiSetBrightness(1, $brightness)
}} else {{
    Write-Error '모니터 밝기 인터페이스를 찾을 수 없습니다.'
}}
"""
        result = subprocess.run(['powershell', '-Command', command],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ 화면 밝기가 {brightness_percent}%로 설정되었습니다")
            return True
        else:
            print(f"화면 밝기 설정 실패: {result.stderr}")
            return False

    except Exception as e:
        print(f"화면 밝기 설정 중 오류: {e}")
        return False

def dim_screen(target_brightness=5):
    """화면을 어둡게 만들기 (원래 밝기 저장)
    
    Args:
        target_brightness: 목표 밝기 (기본값: 5%, 거의 어둡게)
    
    Returns:
        bool: 성공 여부
    """
    global _original_brightness
    
    try:
        # 현재 밝기 저장
        if _original_brightness is None:
            _original_brightness = get_current_brightness()
        
        # 화면을 어둡게 설정
        success = set_screen_brightness(target_brightness)
        if success:
            print(f"🌙 화면이 어두워졌습니다 (원래: {_original_brightness}% → 현재: {target_brightness}%)")
            print("   스케줄 실행 중에도 모니터가 꺼지지 않습니다")
        
        return success
        
    except Exception as e:
        print(f"화면 어둡게 하기 실패: {e}")
        return False

def restore_screen_brightness():
    """화면 밝기를 원래대로 복구
    
    Returns:
        bool: 성공 여부
    """
    global _original_brightness
    
    try:
        if _original_brightness is None:
            print("⚠️ 저장된 원래 밝기가 없습니다")
            return False
        
        print(f"↩ 이전 밝기({_original_brightness}%)로 복구합니다")
        success = set_screen_brightness(_original_brightness)
        if success:
            print(f"☀️ 화면 밝기가 복구되었습니다")
        
        # 복구 후 초기화
        _original_brightness = None
        return success
        
    except Exception as e:
        print(f"화면 밝기 복구 실패: {e}")
        return False

def is_screen_dimmed():
    """화면이 어두워진 상태인지 확인
    
    Returns:
        bool: 어두워진 상태 여부
    """
    global _original_brightness
    return _original_brightness is not None