# 🚀 활성 종목 관리 시스템 설정 가이드

이 가이드는 투자점수 기반 활성 종목 관리 시스템을 us-stock-automation에 통합하는 방법을 설명합니다.

## 📋 변경 사항 요약

### 추가된 파일
- `scripts/manage_us_stocks_rest.py` - 투자점수 계산 및 활성 종목 관리 스크립트

### 수정된 파일
- `.github/workflows/daily_update.yml` - 활성 종목 관리 스텝 추가
- `requirements.txt` - supabase 패키지 추가
- `README.md` - 새로운 기능 설명 추가

## ✅ 설정 단계

### Step 1: Supabase SQL 실행

Supabase SQL Editor에서 다음 SQL 파일들을 **순서대로** 실행하세요:

> SQL 파일들은 메인 프로젝트 저장소 (`vercel_project`)의 `sql/` 폴더에 있습니다.

1. **01_add_us_stock_management_columns.sql**
   ```sql
   -- us_stocks 테이블에 관리 컬럼 추가
   ALTER TABLE us_stocks ADD COLUMN 활성여부 BOOLEAN DEFAULT true;
   ALTER TABLE us_stocks ADD COLUMN 투자점수 NUMERIC DEFAULT 50;
   -- ... 등
   ```

2. **02_create_us_stock_views_final.sql**
   ```sql
   -- 활성 종목 뷰, 스윙 적정가 뷰 등 7개 뷰 생성
   CREATE VIEW us_active_stocks_view AS ...
   CREATE VIEW us_swing_proper_view AS ...
   -- ... 등
   ```

3. **03_create_monthly_snapshot_table.sql**
   ```sql
   -- 월별 스냅샷 테이블 생성
   CREATE TABLE us_monthly_snapshots (...);
   CREATE VIEW us_current_month_snapshot AS ...
   ```

### Step 2: GitHub Secrets 추가

GitHub 저장소 Settings > Secrets and variables > Actions에서 추가:

**새로 추가할 Secret:**
- `SUPABASE_ANON_KEY` - Supabase Anon Key

**기존 Secrets (확인):**
- `SUPABASE_URL` ✓
- `SUPABASE_SERVICE_ROLE_KEY` ✓
- `KIS_APP_KEY` ✓
- `KIS_APP_SECRET` ✓
- `KIS_IS_REAL` ✓

#### SUPABASE_ANON_KEY 찾는 방법:
1. Supabase 프로젝트 대시보드 접속
2. Settings > API
3. **Project API keys** 섹션에서 `anon` `public` 키 복사
4. GitHub Secrets에 `SUPABASE_ANON_KEY`로 추가

### Step 3: 변경사항 커밋 & 푸시

```bash
cd /path/to/us-stock-automation

# 변경사항 확인
git status

# 파일 추가
git add .

# 커밋
git commit -m "Add investment score management system

- Add manage_us_stocks_rest.py for automated stock management
- Calculate investment scores (0-100) based on 4 factors
- Auto activate/deactivate stocks based on scores
- Save monthly snapshots for us_proper page
- Update workflow to run management after pattern calculation
- Add supabase dependency to requirements.txt"

# 푸시
git push origin main
```

### Step 4: 수동 테스트 실행

1. GitHub 저장소 > **Actions** 탭 이동
2. **"Daily US Stock Update"** 워크플로우 선택
3. **"Run workflow"** 버튼 클릭 > "Run workflow" 확인
4. 실행 결과 확인 (약 15분 소요)

#### 예상 출력:
```
💰 Update US Stock Prices
✓ 516개 종목 가격 업데이트 완료

📊 Calculate Today's Pattern
✓ 패턴 계산 완료

🎯 Manage Active Stocks
📊 1단계: 투자점수 계산 중...
   진행: 50/516
   진행: 100/516
   ...
   ✓ 투자점수 계산 완료: 516개 종목

🔄 2단계: 종목 활성/비활성 처리 중...
   ✓ 활성화: 100개 종목
   ✓ 비활성화: 416개 종목

📸 3단계: 월별 스냅샷 저장 중...
   ✓ 신규 저장: 25개 종목
   ✓ 업데이트: 3개 종목

✨ 모든 작업이 완료되었습니다!
```

## 🔍 동작 확인

### 1. Supabase에서 데이터 확인

```sql
-- 활성 종목 수 확인
SELECT
    COUNT(*) FILTER (WHERE 활성여부 = true) as 활성종목,
    COUNT(*) FILTER (WHERE 활성여부 = false) as 비활성종목,
    ROUND(AVG(투자점수) FILTER (WHERE 활성여부 = true), 1) as 평균점수
FROM us_stocks;

-- Top 10 활성 종목 확인
SELECT 종목코드, 종목명, 투자점수, 활성화일
FROM us_stocks
WHERE 활성여부 = true
ORDER BY 투자점수 DESC
LIMIT 10;

-- 월별 스냅샷 확인
SELECT COUNT(*), 스냅샷년월
FROM us_monthly_snapshots
GROUP BY 스냅샷년월
ORDER BY 스냅샷년월 DESC;
```

### 2. 프론트엔드에서 확인

메인 프로젝트의 다음 페이지들을 확인:

- **us_total.html**: 활성 100개 종목만 표시 + 통계 위젯
- **us_proper.html**: 월별 스냅샷 데이터 표시 (비활성화되어도 유지)
- **us_main.html**: 활성 종목만 필터링

## ⚙️ 설정 값 조정

`scripts/manage_us_stocks_rest.py` 파일 상단에서 조정 가능:

```python
MIN_INVESTMENT_SCORE = 60   # 최소 투자점수 (기본 60점)
MIN_VOLUME = 100000         # 최소 평균거래량 (기본 10만주)
MAX_ACTIVE_STOCKS = 100     # 최대 활성 종목 수 (기본 100개)
```

변경 후 커밋 & 푸시하면 다음 실행부터 적용됩니다.

## 🕐 실행 스케줄

- **자동 실행**: 매일 아침 7시 (한국시간), 월~금
- **수동 실행**: 언제든지 GitHub Actions에서 가능

## 🛠️ 문제 해결

### Q1: "활성 종목이 0개입니다"
**원인**: 투자점수가 모두 60점 미만
**해결**:
1. `MIN_INVESTMENT_SCORE` 값을 낮춤 (예: 50점)
2. 또는 SQL 파일 실행 여부 확인

### Q2: "테이블/뷰를 찾을 수 없음"
**원인**: SQL 파일 미실행
**해결**: Step 1의 SQL 파일들을 순서대로 다시 실행

### Q3: "SUPABASE_ANON_KEY 오류"
**원인**: GitHub Secrets 미설정
**해결**: Step 2에서 `SUPABASE_ANON_KEY` Secret 추가

### Q4: "투자점수가 모두 50점"
**원인**: 가격 데이터 또는 B가격 데이터 부족
**해결**:
1. us_prices 테이블에 최소 2일 이상의 데이터 필요
2. us_bt_points 테이블에 B가격 데이터 필요

## 📊 모니터링 대시보드 (Supabase)

### 뷰 활용
```sql
-- 전체 통계
SELECT * FROM us_stock_management_stats;

-- 활성 종목 목록
SELECT * FROM us_active_stocks_view LIMIT 10;

-- 이번 달 스냅샷
SELECT * FROM us_current_month_snapshot;
```

## 🎯 다음 단계

1. ✅ SQL 파일 실행
2. ✅ GitHub Secrets 설정
3. ✅ 변경사항 커밋 & 푸시
4. ✅ 수동 테스트 실행
5. ✅ 결과 확인
6. 🔄 매일 자동 실행됨!

---

문제가 발생하면 GitHub Actions 로그를 확인하거나, Supabase 테이블/뷰를 직접 조회하여 디버깅하세요.
