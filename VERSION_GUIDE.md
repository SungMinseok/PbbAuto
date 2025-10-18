# 버전 관리 가이드

## 📌 버전 형식 (CalVer)

```
YYYY.MM.DD.HHMM
```

**예시:**
- `2025.10.18.1530` = 2025년 10월 18일 15시 30분 빌드
- `2025.10.19.0900` = 2025년 10월 19일 09시 00분 빌드

## 🚀 배포 방법

### 방법 1: 자동 배포 (가장 간단) ⭐
```batch
deploy.bat
```

스크립트가 자동으로:
1. ✅ 현재 시간 기반 버전 생성
2. ✅ version.json 업데이트
3. ✅ Git 커밋 및 푸시
4. ✅ 태그 생성 및 푸시
5. ✅ GitHub Actions 트리거

**실행 예:**
```
========================================
PbbAuto 빠른 배포 스크립트
========================================

[1/7] version.json 자동 업데이트...

변경사항 입력 (Enter=자동 배포): 버그 수정 및 성능 개선

새 버전: 2025.10.18.1530
빌드 날짜: 2025-10-18
이전 버전: 2025.10.18.1500

✅ version.json 업데이트 완료!
   버전: 2025.10.18.1530
   날짜: 2025-10-18

생성된 버전: 2025.10.18.1530

[2/7] 로컬 변경사항 확인...
...
```

---

### 방법 2: 수동 버전 업데이트
```bash
# Python 스크립트로 버전 업데이트
python update_version.py "변경사항 메시지"

# Git 커밋 및 태그
git add .
git commit -m "v2025.10.18.1530 배포"
git tag -a v2025.10.18.1530 -m "Release v2025.10.18.1530"
git push origin main
git push origin v2025.10.18.1530
```

---

### 방법 3: 완전 수동
```bash
# 1. version.json 직접 수정
# - version: "2025.10.18.1530"
# - build_date: "2025-10-18"
# - changelog 추가

# 2. Git 작업
git add .
git commit -m "v2025.10.18.1530 배포"
git push origin main

# 3. 태그 생성 및 푸시
git tag -a v2025.10.18.1530 -m "Release v2025.10.18.1530"
git push origin v2025.10.18.1530
```

---

## 🛠️ 로컬 빌드만 (배포 없이)

```batch
build_local.bat
```

현재 version.json 기준으로 로컬에서만 EXE 파일을 빌드합니다.

---

## 📊 버전 관리 FAQ

### Q: 같은 날 여러 번 배포하면?
**A:** 시간(HHMM)이 다르므로 고유합니다.
```
2025.10.18.1000  (오전 10시)
2025.10.18.1430  (오후 2시 30분)
2025.10.18.1600  (오후 4시)
```

### Q: 이전 버전 형식은?
**A:** `1.0.1` → `2025.10.18.1530`으로 변경되었습니다.

### Q: Windows 버전 제한은?
**A:** `build.py`가 자동으로 처리합니다.
- 사용자에게 보이는 버전: `2025.10.18.1530`
- Windows 내부 버전: `25.10.18.1530` (YYYY를 YY로 변환)

### Q: 버전을 수동으로 설정하려면?
**A:** `version.json`을 직접 수정하면 됩니다.
```json
{
  "version": "2025.10.18.1530",
  "build_date": "2025-10-18",
  ...
}
```

---

## 📝 Changelog 작성 팁

**좋은 예:**
```
- 명령어 실행 안정성 개선
- 윈도우 자동 선택 기능 추가
- UI 반응속도 향상
```

**나쁜 예:**
```
- 코드 수정
- 버그 픽스
- 업데이트
```

---

## 🔍 배포 확인

### GitHub Actions
https://github.com/SungMinseok/PbbAuto/actions

### 릴리스 페이지
https://github.com/SungMinseok/PbbAuto/releases

### 최신 버전 확인
```bash
curl -s https://api.github.com/repos/SungMinseok/PbbAuto/releases/latest | grep "tag_name"
```

---

## 🎯 빠른 참조

| 작업 | 명령어 |
|------|--------|
| **자동 배포** | `deploy.bat` |
| **로컬 빌드** | `build_local.bat` |
| **버전 업데이트만** | `python update_version.py "변경사항"` |
| **현재 버전 확인** | `type version.json` |

---

**마지막 업데이트:** 2025-10-18

