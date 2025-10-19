# 🔑 GitHub Secret 업데이트 필요

## ❌ 문제
현재 DATABASE_URL이 IPv6 주소를 사용하여 GitHub Actions에서 연결 실패

## ✅ 해결 방법

### DATABASE_URL을 Pooler 주소로 변경:

**기존 (IPv6 - 작동 안 함):**
```
postgresql://postgres:July05280326!@db.sssmldmhcfuodutvvcqf.supabase.co:5432/postgres
```

**변경 (Pooler - 작동함):**
```
postgresql://postgres.sssmldmhcfuodutvvcqf:July05280326!@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
```

## 🔧 GitHub Secret 업데이트 단계:

1. https://github.com/Taeyoung-Kim-Jian/us-stock-automation/settings/secrets/actions 접속

2. `DATABASE_URL` 시크릿 찾기

3. **Update** 버튼 클릭

4. 새로운 값 입력:
   ```
   postgresql://postgres.sssmldmhcfuodutvvcqf:July05280326!@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
   ```

5. **Update secret** 클릭

## 🧪 테스트

Secret 업데이트 후:
- Actions 탭 → **Run workflow** 버튼으로 수동 실행
- 정상 작동 확인

---

**주요 변경점:**
- 호스트: `db.xxx` → `aws-0-ap-northeast-2.pooler.supabase.com`
- 포트: `5432` → `6543`
- 사용자: `postgres` → `postgres.sssmldmhcfuodutvvcqf`
