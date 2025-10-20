# 🇺🇸 US Stock Automation

미국 주식 가격 업데이트, 패턴 분석 및 활성 종목 관리 자동화 시스템

## 📋 기능

1. **매일 아침 7시 (한국시간) 자동 실행**
2. **미국 주식 가격 정보 업데이트** (Supabase DB)
3. **당일 패턴 자동 계산 및 저장**
4. **투자점수 계산 및 활성 종목 관리** (상위 100개 자동 선정)
5. **월별 스냅샷 저장** (적정가 근접 종목 기록)

## 🔧 기술 스택

- Python 3.11
- GitHub Actions (스케줄링)
- Supabase (PostgreSQL)
- yfinance (주가 데이터)

## 📂 프로젝트 구조

```
us_stock_automation/
├── .github/
│   └── workflows/
│       └── daily_update.yml           # GitHub Actions 워크플로우
├── scripts/
│   ├── update_prices.py               # 가격 업데이트
│   ├── calculate_pattern.py           # 패턴 계산
│   └── manage_us_stocks_rest.py       # 활성 종목 관리 (NEW!)
├── requirements.txt                   # Python 패키지
├── .env.example                       # 환경변수 예시
└── README.md
```

## 🚀 설정 방법

### 1. GitHub Secrets 설정

Repository Settings → Secrets and variables → Actions에서 추가:

- `SUPABASE_URL`: Supabase 프로젝트 URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service Role Key
- `SUPABASE_ANON_KEY`: Anon Key (활성 종목 관리용)
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `KIS_APP_KEY`: 한국투자증권 APP KEY
- `KIS_APP_SECRET`: 한국투자증권 APP SECRET
- `KIS_IS_REAL`: 실전/모의 구분 (true/false)

### 2. Supabase SQL 실행

다음 SQL 파일들을 순서대로 Supabase SQL Editor에서 실행:

1. `01_add_us_stock_management_columns.sql` - 관리 컬럼 추가
2. `02_create_us_stock_views_final.sql` - 뷰 생성
3. `03_create_monthly_snapshot_table.sql` - 월별 스냅샷 테이블 생성

> SQL 파일은 메인 프로젝트 저장소의 `sql/` 폴더에 있습니다.

### 3. 로컬 실행 (테스트)

```bash
# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 가격 업데이트 실행
python scripts/update_prices.py

# 패턴 계산 실행
python scripts/calculate_pattern.py

# 활성 종목 관리 실행
python scripts/manage_us_stocks_rest.py
```

## ⏰ 실행 스케줄

- **매일 아침 7시 (KST)** - 한국시간 기준
- **UTC 기준 22시** (전날 밤 10시)
- **실행 요일**: 월~금 (주중만 실행)

## 📊 처리 프로세스

### 1단계: 가격 업데이트
1. Supabase에서 미국 주식 목록 조회
2. 한국투자증권 API로 최신 가격 데이터 가져오기
3. `us_prices` 테이블에 당일 데이터 업데이트

### 2단계: 패턴 계산
4. B포인트 기준으로 당일 패턴 계산
5. `us_prices.pattern` 컬럼에 패턴 저장

### 3단계: 활성 종목 관리 (NEW!)
6. **투자점수 계산** (0-100점)
   - 수익률: 35점
   - 거래량: 20점
   - 패턴: 25점 (돌파=25, 돌파눌림=20, 박스권=15, 이탈=5, 기타=10)
   - B가격 위치: 20점

7. **활성/비활성 처리**
   - 투자점수 60점 이상 종목 중 상위 100개 활성화
   - 나머지 종목 비활성화

8. **월별 스냅샷 저장**
   - 적정가 근접 종목 (괴리율 ±5% 이내)을 월별로 저장
   - 한번 표시된 종목은 비활성화되어도 해당 월에는 계속 노출

## 🎯 투자점수 시스템

### 점수 구성 (총 100점)

| 항목 | 배점 | 설명 |
|------|------|------|
| 수익률 | 35점 | 전체 기간 누적 수익률 |
| 거래량 | 20점 | 최근 20일 평균 거래량 (log scale) |
| 패턴 | 25점 | 차트 패턴 유형 (돌파 > 돌파눌림 > 박스권 > 기타 > 이탈) |
| B가격 위치 | 20점 | 적정 매수가 근접도 (±5% 이내 = 만점) |

### 활성화 기준

- **최소 투자점수**: 60점 이상
- **최소 거래량**: 100,000주 이상
- **최대 활성 종목 수**: 100개

## 📁 데이터베이스 구조

### 테이블

- `us_stocks`: 종목 정보 + 관리 컬럼 (활성여부, 투자점수, 활성화일 등)
- `us_prices`: 일별 가격 데이터
- `us_bt_points`: B/T 포인트 (적정 매수/매도가)
- `us_monthly_snapshots`: 월별 스냅샷 (NEW!)

### 주요 뷰

- `us_active_stocks_view`: 활성 종목만 표시 (투자점수 순)
- `us_swing_proper_view`: 활성 종목 중 적정가 근접 종목
- `us_current_month_snapshot`: 현재 월 스냅샷 (us_proper 페이지용)
- `us_stock_management_stats`: 전체 통계

## 🔍 모니터링

### GitHub Actions 로그 확인
1. GitHub 저장소 > Actions 탭
2. "Daily US Stock Update" 워크플로우 선택
3. 최신 실행 결과 확인

### 성공 예시
```
🔄 미국 주식 가격 업데이트 시작...
✓ 516개 종목 가격 업데이트 완료

📈 당일 패턴 계산 시작...
✓ 패턴 계산 완료

🔄 투자점수 계산 및 활성 종목 관리 시작...
📊 1단계: 투자점수 계산 중...
   ✓ 투자점수 계산 완료: 516개 종목

🔄 2단계: 종목 활성/비활성 처리 중...
   ✓ 활성화: 100개 종목
   ✓ 비활성화: 416개 종목

📸 3단계: 월별 스냅샷 저장 중...
   ✓ 신규 저장: 25개 종목
   ✓ 업데이트: 3개 종목

✨ 모든 작업이 완료되었습니다!
```

## 🛠️ 트러블슈팅

### GitHub Actions 실패 시
1. Secrets 설정 확인 (`SUPABASE_ANON_KEY` 추가 확인)
2. SQL 파일 실행 여부 확인
3. Supabase RLS 정책 확인
4. 실행 로그에서 에러 메시지 확인

### 투자점수가 0점인 경우
1. `us_prices` 테이블에 가격 데이터 확인
2. `us_bt_points` 테이블에 B가격 데이터 확인
3. `us_stocks.pattern` 컬럼 값 확인

## 📝 라이선스

MIT License

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
