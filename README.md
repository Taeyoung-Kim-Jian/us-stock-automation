# 🇺🇸 US Stock Automation

미국 주식 가격 업데이트 및 패턴 분석 자동화 시스템

## 📋 기능

1. **매일 아침 7시 (한국시간) 자동 실행**
2. **미국 주식 가격 정보 업데이트** (Supabase DB)
3. **당일 패턴 자동 계산 및 저장**

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
│       └── daily_update.yml    # GitHub Actions 워크플로우
├── scripts/
│   ├── update_prices.py        # 가격 업데이트
│   └── calculate_pattern.py    # 패턴 계산
├── requirements.txt            # Python 패키지
├── .env.example               # 환경변수 예시
└── README.md
```

## 🚀 설정 방법

### 1. GitHub Secrets 설정

Repository Settings → Secrets and variables → Actions에서 추가:

- `SUPABASE_URL`: Supabase 프로젝트 URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service Role Key
- `DATABASE_URL`: PostgreSQL 연결 문자열

### 2. 로컬 실행 (테스트)

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
```

## ⏰ 실행 스케줄

- **매일 아침 7시 (KST)** - 한국시간 기준
- **UTC 기준 22시** (전날 밤 10시)

## 📊 처리 프로세스

1. Supabase에서 미국 주식 목록 조회
2. yfinance API로 최신 가격 데이터 가져오기
3. `us_prices` 테이블에 당일 데이터 업데이트
4. b포인트 기준으로 당일 패턴 계산
5. `us_prices.pattern` 컬럼에 패턴 저장

## 📝 라이선스

MIT License

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
