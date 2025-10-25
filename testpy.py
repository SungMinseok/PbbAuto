import subprocess
from monitorcontrol import get_monitors

_last_brightness = None  # 전역 변수로 이전 밝기 저장

def get_current_brightness():
    """현재 화면 밝기 읽기 (내장 디스플레이 또는 외장 모니터)"""
    try:
        # 우선 외장 모니터(DCC/CI) 시도
        for monitor in get_monitors():
            with monitor:
                return monitor.get_luminance()
    except Exception:
        pass

    try:
        # 내장 디스플레이 (WMI)
        command = "(Get-CimInstance -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
        result = subprocess.run(['powershell', '-Command', command],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
    except Exception:
        pass

    print("⚠️ 현재 밝기를 가져올 수 없어 기본값 80%로 사용합니다")
    return 80


def set_screen_brightness(brightness_percent):
    """밝기 설정 (자동 감지 및 복구 지원)"""
    global _last_brightness

    brightness_percent = max(0, min(100, int(brightness_percent)))
    if _last_brightness is None:
        _last_brightness = get_current_brightness()

    try:
        # 외장 모니터(DCC/CI)
        try:
            for monitor in get_monitors():
                with monitor:
                    monitor.set_luminance(brightness_percent)
            print(f"✓ 외장 모니터 밝기를 {brightness_percent}%로 설정했습니다")
            return True
        except Exception:
            pass

        # 내장 디스플레이 (CIM)
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
            restore_brightness()
            return False

    except Exception as e:
        print(f"화면 밝기 설정 중 오류: {e}")
        restore_brightness()
        return False


def restore_brightness():
    """이전 밝기로 복구"""
    global _last_brightness
    if _last_brightness is not None:
        try:
            print(f"↩ 이전 밝기({_last_brightness}%)로 복구합니다")
            set_screen_brightness(_last_brightness)
            return True
        except Exception as e:
            print(f"복구 중 오류: {e}")
    else:
        print("이전 밝기값이 저장되지 않아 복구할 수 없습니다")
    return False


if __name__ == "__main__":
    print(get_current_brightness())
    set_screen_brightness(0)
    print(get_current_brightness())
    import time
    time.sleep(1)
    restore_brightness()
    print(get_current_brightness())