"""
전역 로깅 설정 모듈
모든 파일에서 이 모듈을 import하면 print 출력이 자동으로 로그파일에도 저장됩니다.
"""
import os
import builtins
from datetime import datetime
import inspect

# 로그 파일 설정
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")

# 원래 print 함수 백업 (한 번만)
if not hasattr(builtins, '_original_print'):
    builtins._original_print = builtins.print

def enhanced_print(*args, **kwargs):
    """모든 print 출력을 콘솔과 로그파일에 동시 저장, 실행 위치 포함"""
    # 콘솔에 출력
    builtins._original_print(*args, **kwargs)
    
    # 파일에 저장
    try:
        # 호출 위치 가져오기
        # frame = inspect.currentframe()
        # caller_frame = frame.f_back.f_back  # enhanced_print() → print() 호출한 쪽 → 실제 호출한 쪽
        # filename = caller_frame.f_code.co_filename
        # lineno = caller_frame.f_lineno
        # #funcname = caller_frame.f_code.co_name
        # #location = f"{filename}:{lineno} ({funcname})"
        # location = f"{filename}:{lineno}"

        frame = inspect.currentframe().f_back.f_back
        filename = os.path.basename(frame.f_code.co_filename)  # 파일명만
        lineno = frame.f_lineno  # 줄 번호
        location = f"{filename}:{lineno}"

        # 메시지 구성
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = ' '.join(str(arg) for arg in args)

        if message.strip():  # 빈 메시지가 아닐 때만 저장
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [{location}] {message}\n")
    except Exception as e:
        builtins._original_print(f"로그 파일 쓰기 오류: {e}")

# print 함수를 전역적으로 교체
builtins.print = enhanced_print

def get_log_file_path():
    """현재 로그 파일 경로 반환"""
    return log_file
