# 🚀 새로운 명령어 추가하는 방법 (drag 예시)

## 🎯 개요
새로운 플러그인 아키텍처로 명령어를 추가하는 것이 매우 간단해졌습니다!
`drag` 명령어를 예시로 설명합니다.

## 📋 단계별 가이드

### 1단계: command_registry.py에 클래스 추가

```python
class DragCommand(CommandBase):
    """마우스 드래그 명령어 - 새로운 명령어 예시! 🎉"""
    
    @property
    def name(self) -> str:
        return "drag"
    
    @property
    def description(self) -> str:
        return "Mouse drag from point A to point B"
    
    def create_ui(self) -> QWidget:
        # UI 위젯 생성 코드
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 좌표 입력 필드들
        self.x1_input = QLineEdit()
        self.y1_input = QLineEdit()
        # ... 더 많은 UI 요소들
        
        return widget
    
    def parse_params(self, params: list) -> dict:
        # "drag 100 200 300 400" → {'x1': '100', 'y1': '200', ...}
        if len(params) >= 4:
            return {
                'x1': params[0], 'y1': params[1], 
                'x2': params[2], 'y2': params[3]
            }
        return {}
    
    def set_ui_values(self, params: dict):
        # UI에 값 설정
        self.x1_input.setText(params.get('x1', ''))
        # ...
    
    def get_command_string(self) -> str:
        # UI에서 명령어 문자열 생성
        return f"drag {x1} {y1} {x2} {y2}"
    
    def execute(self, params: dict, window_coords=None, processor_state=None):
        # 실제 드래그 실행 로직
        pyd.moveTo(x1, y1)
        pyd.mouseDown()
        pyd.moveTo(x2, y2)
        pyd.mouseUp()
```

### 2단계: 레지스트리에 등록

```python
# command_registry.py 하단
COMMAND_REGISTRY = {
    'press': PressCommand(),
    'write': WriteCommand(),
    # ... 기존 명령어들
    'drag': DragCommand(),  # ← 이것만 추가하면 끝! 🎉
}
```

### 3단계: constants.py 업데이트 (현재는 필요함)

```python
# constants.py
SUPPORTED_ACTIONS = [
    'press', 'write', 'wait', 'screenshot', 'click', 
    'drag',  # ← 새 명령어 추가
    'cheat', 'i2s', 'i2skr', 'validate', 'export', 'waituntil'
]
```

## ✅ 완료!

이제 새로운 `drag` 명령어가:
- ✅ 자동으로 드롭다운에 나타남
- ✅ 전용 UI가 자동 생성됨  
- ✅ 파라미터 파싱/설정이 자동화됨
- ✅ 실행 로직이 통합됨

## 🔥 이전 vs 현재 비교

### 이전 방식 (복잡)
1. `commands.py`에 `_handle_drag()` 메서드 추가
2. `process_command()`에 elif 분기 추가
3. `dialogs.py`에 UI 코드 추가
4. `AddCommandDialog`에 케이스 추가
5. 여러 파일을 수정해야 함

### 현재 방식 (간단!)
1. `command_registry.py`에 클래스 1개 추가
2. 레지스트리에 1줄 추가
3. `constants.py`에 1줄 추가
4. **끝!** 🎉

## 🌟 주요 장점

- **단일 파일**: 새 명령어는 한 곳에만 작성
- **자동 통합**: UI, 파싱, 실행이 자동 연결
- **타입 안전**: 추상 클래스로 인터페이스 강제
- **유지보수**: 각 명령어가 독립적
- **확장성**: 무한정 명령어 추가 가능

## 🚀 결론

296줄 → 25줄로 축소된 `commands.py`와 함께,  
새로운 명령어 추가가 **10배 더 쉬워졌습니다!** 🎉
