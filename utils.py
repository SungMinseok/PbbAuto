import os
import time
import json
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


def image_to_text(img_path="", lang='eng'):
    """Convert the most recent screenshot to text."""
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

    return image_to_text_with_fallback(img_path=img_path, lang=lang, preview=False)


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
