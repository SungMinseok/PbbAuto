## 한 줄 소개
- **PbbAuto**: QA 실무자가 AI 개발도구를 활용해 단기간에 직접 구축한 PC 게임 테스트 자동화 도구. GUI 기반 시나리오 실행, 스케줄링, 시각화 리포팅, 자동 업데이트를 지원해 테스트 속도·일관성·재현성을 크게 향상.

## 문서 목적
- **목적**: 다른 앱 소개 문서와 통합 가능한 표준 형태의 설명서 제공. 도입 배경, 아키텍처, 기능, 측정된 효과(수치·그래프), 한계, 개선 계획, 종합 결론을 포함.
- **대상**: QA 리더, 개발/운영 책임자, 도구 표준화를 검토하는 조직.

## 도입 배경과 목표
- **배경**: 수작업 테스트 반복, 시나리오 복잡도 증가, 릴리스 주기 단축, 야간·장시간 회귀 테스트 어려움.
- **핵심 목표**
  - **리드타임 단축**: 반복/회귀·E2E 테스트 자동화로 인력 소모 최소화.
  - **일관성/재현성 확보**: 스텝 정의의 표준화와 실행 환경 고정.
  - **가시성 강화**: 결과·커버리지·결함 트렌드의 시각화 리포팅.
  - **확장성**: 비개발자도 스텝(커맨드)와 번들을 추가·수정 가능.

## 시스템 개요
- **구성요소**
  - **GUI 실행기**: 테스트 번들 선택/실행, 상태 모니터링 (`main.py`, `settings_dialog.py`, `dialogs.py`).
  - **커맨드/번들 엔진**: 명령 레지스트리와 JSON 번들 기반 시나리오 실행 (`commands.py`, `command_registry.py`, `bundles/*.json`).
  - **스케줄러**: 예약 실행 및 반복 수행 (`scheduler.py`, `schedules.json`).
  - **리포팅/로그**: 실행 로그, 결과 저장, 리포트 생성 (`logger_setup.py`, `logs/`, `test_results/`).
  - **업데이트/배포**: 로컬/원격 업데이트 지원, 버전 관리 (`updater.py`, `update_version.py`, `version.json`, `deploy*.py|.bat`, `*.spec`).
  - **OCR/화면 인식**: 스크린샷+OCR(Tesseract) 기반 텍스트/상태 인식 (`etc/test_tesseract*.py`, `screenshot/`).
- **동작 원리**
  1) 사용자가 실행할 번들을 선택 → 2) 엔진이 스텝을 순차/조건 실행 → 3) 화면/OCR/클라이언트 상태를 감지해 분기 → 4) 결과와 로그를 수집·저장 → 5) 스케줄/재시도/업데이트를 자동 처리.
- **대상 영역**
  - 게임 런처/클라이언트 진입, 계정 연결/생성, 매치 진입/종료, 인벤토리·상점 상호작용, 외부 도구(OP.GG 등) 연동 체크 등.

## 주요 기능
- **번들 기반 테스트 시나리오**: 사람이 읽기 쉬운 JSON으로 작성·버전관리. 사내 도메인 명령을 재조합해 고수준 시나리오 구성.
- **GUI 중심 사용성**: 비개발자도 실행, 중단, 재시작, 파라미터 변경 가능.
- **스케줄링/무인실행**: 야간·주말 배치, 실패 자동 재시도.
- **시각화 리포트**: 실행 시간, 성공률, 결함 밀도, 커버리지 트렌드 시각화.
- **자동 업데이트**: 버전 확인·차등 배포, 사내 배포 파이프라인 연계.
- **확장성**: `commands.py`로 새 명령 등록, `bundles/*.json`만으로 시나리오 확장.

## 기술 스택 및 AI 활용
- **언어/프레임워크**: Python 3.11, PyQt5, PyInstaller.
- **인식/자동화**: 스크린샷 캡처 + Tesseract OCR, UI 상태 감지.
- **AI 개발도구 활용**
  - GPT 계열로 커맨드 스텝/번들 초안 생성·리팩터링, 로그 요약, 실패 원인 분류 자동화.
  - 자연어→번들(JSON) 변환 가이드 생성으로 시나리오 작성 시간 단축.
  - 릴리즈 노트·체인지로그 초안 자동 생성.

## 운영 워크플로우
1) 요구 시나리오를 자연어로 정리 → 2) AI 보조로 번들 초안 생성 → 3) 로컬 검증/리뷰 → 4) 스케줄 등록(필요 시) → 5) 야간 회귀 자동 실행 → 6) 아침에 리포트·알림 확인 → 7) 결함 티켓화/추적 → 8) 주간 트렌드 리뷰.

## 측정된 효과(예시 수치 및 시각화 스펙)
- 아래 템플릿을 실제 수치로 치환해 사용하세요.

- **핵심 지표**
  - **회귀 테스트 시간**: 도입 전 <BEFORE_HOURS>h → 도입 후 <AFTER_HOURS>h (△<REDUCTION_%>%)
  - **수동 투입 인력**: 주당 <BEFORE_FTE>FTE → <AFTER_FTE>FTE
  - **성공률**: <BEFORE_PASS_%>% → <AFTER_PASS_%>%
  - **결함 발견 리드타임**: <BEFORE_DAYS>d → <AFTER_DAYS>d
  - **시나리오 커버리지**: <BEFORE_SCENARIOS> → <AFTER_SCENARIOS>

- **데이터 스키마 예시(CSV)**
```csv
date,build_id,total_cases,passed,failed,avg_duration_min,unique_defects,coverage_scenarios
2025-09-01,20250901.1,480,433,47,92,13,120
```

- **변경 전/후 막대 그래프(Vega-Lite 사양)**
```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {
    "values": [
      {"metric":"Regression Hours","phase":"Before","value": <BEFORE_HOURS>},
      {"metric":"Regression Hours","phase":"After","value": <AFTER_HOURS>},
      {"metric":"Weekly FTE","phase":"Before","value": <BEFORE_FTE>},
      {"metric":"Weekly FTE","phase":"After","value": <AFTER_FTE>}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field":"metric","type":"nominal"},
    "y": {"field":"value","type":"quantitative"},
    "color": {"field":"phase","type":"nominal"}
  }
}
```

- **트렌드 라인(성공률/커버리지)**
```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {"url": "results_timeseries.csv"},
  "transform": [
    {"calculate": "datum.passed / datum.total_cases * 100", "as": "pass_rate"}
  ],
  "layer": [
    {
      "mark": "line",
      "encoding": {
        "x": {"field": "date", "type": "temporal"},
        "y": {"field": "pass_rate", "type": "quantitative", "title": "Pass Rate (%)"},
        "color": {"value":"#2E86DE"}
      }
    },
    {
      "mark": "line",
      "encoding": {
        "x": {"field": "date", "type": "temporal"},
        "y": {"field": "coverage_scenarios", "type": "quantitative", "title": "Coverage"},
        "color": {"value":"#16A085"}
      }
    }
  ],
  "resolve": {"scale": {"y": "independent"}}
}
```

- **ROI 개요**
  - 초기 구축 공수: <INIT_PM> PM
  - 월간 절감 시간: <SAVED_HOURS_PER_MONTH> h
  - 단순 회수기간: <PAYBACK_MONTHS> 개월

## 한계와 리스크
- **OCR/화면 의존성**: UI/폰트/해상도 변경 시 민감. 안정화(앵커 요소, 템플릿 갱신) 필요.
- **클라이언트 업데이트**: 게임 패치 주기와 동기화 필요. 번들/커맨드 유지보수 부담.
- **환경 요인**: 포커스·네트워크·권한에 따른 비결정성. 재시도·타임아웃 전략 필수.
- **관측 범위**: 화면·텍스트 중심이라 내부 상태(비동기 오류) 가시성 제한.

## 개선 계획
- **객체 레이어 도입**: 화면 요소 추상화와 안정 식별자 관리로 유지보수 비용 절감.
- **하이브리드 인식**: 이미지+OCR+윈도우 접근성 API/메모리 프로빙 보완.
- **실패 원인 분류 자동화**: LLM 기반 로그 요약·라벨링, 큐레이션 피드백 루프.
- **테스트 데이터 팩토리**: 계정/인벤토리/매치 상태를 코드로 생성·재현.
- **CI/CD 연동**: 빌드 후 자동 회귀, 결과를 게이트로 활용.
- **리포팅 고도화**: 팀/모듈별 대시보드, SLA/에러버짓 관점 도입.
- **번들 작성 UX**: 자연어→번들 변환 마법사, 템플릿/검증기 제공.

## 도입 효과(요약 문구 템플릿)
- “PbbAuto 도입으로 회귀 시간 △<REDUCTION_%>% 단축, 주당 <SAVED_HOURS_PER_WEEK>시간 절감, 성공률 <AFTER_PASS_%>% 달성, 릴리즈 안정성 체감 향상.”

## 채택 및 확산 전략
- **파일럿 → 롤아웃**: 핵심 10개 시나리오로 2주 파일럿 → 성공지표 달성 시 팀 확장.
- **역량 내재화**: 커맨드/번들 작성 교육, 예제 라이브러리 공유.
- **SLA/운영**: 야간 실패 자동 알림, 티켓 연동, 주간 품질 리포트 정례화.

## 결론
- PbbAuto는 QA 현업이 주도해 단기간에 구축한 실용적 자동화 플랫폼으로, 반복 업무의 자동화·표준화·가시화를 동시에 달성. 측정 데이터와 대시보드를 통해 지속적 개선이 가능한 구조를 제공하며, 하이브리드 인식 및 객체 레이어 도입으로 한계를 점진적으로 해소할 로드맵을 보유.

## 부록 A: 데이터 사전(메트릭 정의)
- **total_cases**: 실행된 테스트 케이스 수
- **passed/failed**: 성공/실패 수
- **avg_duration_min**: 평균 수행 시간(분)
- **unique_defects**: 신규/유니크 결함 수
- **coverage_scenarios**: 활성 시나리오/스텝 커버리지
- 계산 지표: pass_rate(%), MTTR(분), 실패율(%), 결함 밀도(결함/100케이스)

## 부록 B: 번들(JSON) 최소 예시
```json
{
  "name": "runPBB_smoke",
  "steps": [
    {"cmd": "launch_client", "args": {"profile": "default"}},
    {"cmd": "connect_account", "args": {"reuse": true}},
    {"cmd": "enter_match", "args": {"mode": "solo"}},
    {"cmd": "validate_state", "args": {"ocr": "MATCH_READY"}},
    {"cmd": "exit_match"},
    {"cmd": "collect_logs"}
  ],
  "retry": {"max": 2, "backoff_sec": 30},
  "timeouts": {"step_sec": 120}
}
```

원하시면 실제 로그 샘플과 결과 CSV를 주시면, 위 시각화 스펙에 맞춰 그래프를 바로 생성해 드리겠습니다.