# PbbAuto 배포 가이드

## 📋 목차
1. [로컬 빌드](#로컬-빌드)
2. [자동 배포 (GitHub Actions)](#자동-배포-github-actions)
3. [수동 배포](#수동-배포)
4. [버전 관리](#버전-관리)

---

## 🔨 로컬 빌드

### 방법 1: 배치 스크립트 사용 (권장)
```batch
build_local.bat
```

### 방법 2: Python 스크립트 직접 실행
```bash
python build.py
```

### 빌드 결과
- `dist/PbbAuto.exe` - 단일 실행 파일

---

## 🚀 자동 배포 (GitHub Actions)

### 빠른 배포 (권장)
```batch
deploy.bat
```

스크립트가 자동으로:
1. Git 상태 확인
2. 변경사항 커밋
3. GitHub에 푸시
4. 버전 태그 생성
5. 태그 푸시 (자동 빌드 트리거)

### 수동 단계별 실행
```bash
# 1. version.json 업데이트
# - version 증가 (예: 1.0.0 → 1.0.1)
# - build_date 업데이트
# - changelog 추가

# 2. 변경사항 커밋
git add .
git commit -m "v1.0.1 - 변경사항 설명"

# 3. GitHub에 푸시
git push origin main

# 4. 버전 태그 생성 및 푸시
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

### 자동 빌드 프로세스
태그가 푸시되면 GitHub Actions가 자동으로:
1. ✅ Windows 환경 설정
2. ✅ Python 및 의존성 설치
3. ✅ EXE 파일 빌드
4. ✅ GitHub Release 생성
5. ✅ 파일 업로드

### 빌드 상태 확인
- **Actions**: https://github.com/SungMinseok/PbbAuto/actions
- **Releases**: https://github.com/SungMinseok/PbbAuto/releases

---

## 📝 수동 배포

### 1. 로컬 빌드
```batch
build_local.bat
```

### 2. GitHub Release 수동 생성
1. https://github.com/SungMinseok/PbbAuto/releases/new 접속
2. 태그 선택 또는 생성 (예: v1.0.1)
3. Release 제목 입력 (예: Release v1.0.1)
4. 설명 작성
5. 파일 업로드:
   - `dist/PbbAuto.exe`
6. "Publish release" 클릭

---

## 📌 버전 관리

### version.json 구조
```json
{
  "version": "1.0.1",
  "build_date": "2025-10-18",
  "update_url": "https://api.github.com/repos/SungMinseok/PbbAuto/releases/latest",
  "changelog": [
    {
      "version": "1.0.1",
      "date": "2025-10-18",
      "changes": [
        "변경사항 1",
        "변경사항 2"
      ]
    }
  ]
}
```

### 버전 번호 규칙
- **Major (x.0.0)**: 대규모 변경, 호환성 깨짐
- **Minor (1.x.0)**: 새로운 기능 추가
- **Patch (1.0.x)**: 버그 수정, 소규모 개선

### 변경사항 작성 가이드
- 명확하고 간결하게 작성
- 사용자 관점에서 작성
- 기술적 세부사항보다는 변경 효과 설명

예시:
- ✅ "명령어 실행 후 앱 멈춤 현상 해결"
- ✅ "윈도우 선택 자동 새로고침 추가"
- ❌ "Qt 시그널 추가"
- ❌ "코드 리팩토링"

---

## 🔧 트러블슈팅

### 빌드 실패 시
```bash
# 의존성 재설치
pip install -r requirements.txt --force-reinstall

# 캐시 정리 후 재빌드
rmdir /s /q build dist
python build.py
```

### GitHub Actions 실패 시
1. Actions 탭에서 로그 확인
2. 실패 원인 파악
3. 수정 후 재푸시 또는 워크플로우 재실행

### 태그 삭제 및 재생성
```bash
# 로컬 태그 삭제
git tag -d v1.0.1

# 원격 태그 삭제
git push origin --delete v1.0.1

# 재생성 및 푸시
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

---

## 📞 지원

- **이슈**: https://github.com/SungMinseok/PbbAuto/issues
- **문의**: GitHub Issues 또는 Pull Request

---

## 📜 체크리스트

### 배포 전 확인사항
- [ ] version.json 업데이트 (버전, 날짜, 변경사항)
- [ ] 모든 변경사항 커밋 완료
- [ ] 로컬 테스트 완료
- [ ] 로컬 빌드 테스트 (선택사항)

### 배포 후 확인사항
- [ ] GitHub Actions 빌드 성공
- [ ] Release 페이지 확인
- [ ] 다운로드 파일 테스트
- [ ] 자동 업데이트 기능 테스트

---

**마지막 업데이트**: 2025-10-18

