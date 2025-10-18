# 🚀 빌드 & 배포 빠른 시작

## 로컬 빌드 (테스트용)
```bash
build_local.bat
```
➡️ `dist/PbbAuto.exe` 생성

---

## 자동 배포 (GitHub Release)
```bash
deploy.bat
```

또는 수동:
```bash
# 1. version.json 수정 (버전 증가 + 변경사항 추가)

# 2. 배포
git add .
git commit -m "v1.0.1 - 변경사항"
git push origin main

# 3. 태그 생성 및 푸시 (자동 빌드 트리거)
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

---

## 배포 확인
- **빌드 진행**: https://github.com/SungMinseok/PbbAuto/actions
- **릴리스**: https://github.com/SungMinseok/PbbAuto/releases

---

## 체크리스트
- [ ] `version.json` 업데이트 (버전 + 변경사항)
- [ ] 로컬 테스트 완료
- [ ] 커밋 & 푸시
- [ ] 태그 생성 & 푸시
- [ ] GitHub Actions 빌드 확인

---

자세한 내용은 [DEPLOY.md](DEPLOY.md) 참조

