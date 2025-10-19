# 🔑 한국투자증권 API 설정 가이드

## 📋 개요
네이버 스크래핑 대신 **한국투자증권 공식 API**를 사용하여 미국 주식 데이터를 수집합니다.

## ✅ 장점
- **안정성**: 공식 API로 차단 걱정 없음
- **정확도**: 실시간 정확한 데이터
- **속도**: API 호출이 스크래핑보다 빠름 (~1-2분)
- **Rate Limit**: 계정당 초당 20건, 충분한 호출 가능

## 🚀 설정 방법

### 1. 한국투자증권 앱 키 발급

1. **한국투자증권 홈페이지 접속**
   - https://www.koreainvestment.com

2. **Open API 신청**
   - 로그인 → Open API → 오픈API 신청
   - 실전투자 또는 모의투자 선택

3. **앱 키 발급**
   - `APP_KEY` (앱 키)
   - `APP_SECRET` (앱 시크릿)
   - 발급 즉시 사용 가능

### 2. GitHub Secrets 설정

1. **GitHub 리포지토리 이동**
   ```
   https://github.com/{username}/us-stock-automation
   ```

2. **Settings → Secrets and variables → Actions**

3. **New repository secret 클릭하여 추가**

   **Secret 1: KIS_APP_KEY**
   ```
   Name: KIS_APP_KEY
   Value: (발급받은 APP_KEY)
   ```

   **Secret 2: KIS_APP_SECRET**
   ```
   Name: KIS_APP_SECRET
   Value: (발급받은 APP_SECRET)
   ```

   **Secret 3: KIS_IS_REAL** (선택사항)
   ```
   Name: KIS_IS_REAL
   Value: false  (모의투자) 또는 true (실전투자)
   ```

4. **기존 Secrets 확인**
   - `SUPABASE_URL` (이미 설정됨)
   - `SUPABASE_SERVICE_ROLE_KEY` (이미 설정됨)

### 3. 로컬 테스트 (.env 파일)

`us_stock_automation/.env` 파일에 추가:

```env
# Supabase (기존)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# 한국투자증권 API (새로 추가)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_IS_REAL=false
```

### 4. GitHub Actions 워크플로우 확인

`.github/workflows/daily_update.yml`에서 환경변수 자동 전달:

```yaml
- name: 💰 Update US Stock Prices
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
    KIS_APP_KEY: ${{ secrets.KIS_APP_KEY }}
    KIS_APP_SECRET: ${{ secrets.KIS_APP_SECRET }}
    KIS_IS_REAL: ${{ secrets.KIS_IS_REAL }}
  run: |
    python scripts/update_prices.py
```

## 📊 API 사양

### 거래소 코드
- `NAS`: 나스닥 (AAPL, TSLA, NVDA 등)
- `NYS`: 뉴욕증권거래소 (JPM, WMT, V 등)
- `AMS`: 아멕스 (사용 안함)

### API 제한
- **초당 호출**: 최대 20건
- **일일 호출**: 무제한 (실전투자 기준)
- **동시 접속**: 최대 40건

### 토큰 유효기간
- **접근 토큰**: 24시간
- 스크립트에서 자동 발급

## 🔍 주요 기능

### 1. 자동 거래소 구분
```python
# NYSE 종목 자동 인식
nyse_stocks = {'JPM', 'BAC', 'WMT', 'V', 'MA', ...}

# NASDAQ 먼저 시도, 실패 시 NYSE 시도
exchange = determine_exchange(symbol)
```

### 2. 현재가 조회
- 종가, 시가, 고가, 저가, 거래량
- 실시간 데이터 (15분 지연)

### 3. 에러 핸들링
- 토큰 자동 발급
- API 호출 제한 대응 (0.1초 간격)
- 실패 시 재시도

## 📈 예상 성능

| 항목 | 네이버 스크래핑 | 한투 API |
|------|----------------|----------|
| 실행 시간 (500개) | 3-5분 | **1-2분** ⚡ |
| 성공률 | 60-80% | **99%+** 🎯 |
| Rate Limit | 있음 | **거의 없음** ✅ |
| 안정성 | 중간 | **매우 높음** 💪 |
| 데이터 정확도 | 중간 | **실시간** 📊 |

## 🎯 다음 단계

1. ✅ APP_KEY, APP_SECRET 발급
2. ✅ GitHub Secrets 설정
3. ✅ GitHub Actions 실행
4. ✅ 결과 확인

## 📌 참고사항

### 모의투자 vs 실전투자
- **모의투자**: 무료, 연습용, 데이터 동일
- **실전투자**: 계좌 필요, 실시간 데이터

### API 문서
- https://apiportal.koreainvestment.com/
- 해외주식 현재가: `HHDFS00000300`
- 해외주식 기간별시세: `HHDFS76240000`

### 문제 해결
- **토큰 발급 실패**: APP_KEY, APP_SECRET 확인
- **데이터 없음**: 거래소 코드 확인 (NAS ↔ NYS)
- **Rate Limit**: 호출 간격 늘리기 (time.sleep 증가)
