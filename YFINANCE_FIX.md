# 🔧 yfinance API 차단 문제 해결

## 📋 문제점
GitHub Actions 환경에서 Yahoo Finance API 요청 시 다음 에러 발생:
```
Failed to get ticker 'AAPL' reason: Expecting value: line 1 column 1 (char 0)
$AAPL: possibly delisted; No price data found (period=7d)
HTTPSConnectionPool: Max retries exceeded (429 error responses)
```

## 🎯 원인
1. **User-Agent 헤더 없음**: Yahoo Finance가 봇 트래픽을 차단
2. **Rate Limiting (429 에러)**: 너무 빠른 요청 속도로 IP 차단
3. **재시도 전략 부족**: 일시적 오류 처리 미흡

## ✅ 해결 방법

### 1. User-Agent 설정
브라우저처럼 보이도록 User-Agent 헤더 추가:
```python
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
```

### 2. 재시도 전략 구현
HTTP 500번대 에러 발생 시 자동 재시도 (429는 별도 처리):
```python
retry_strategy = Retry(
    total=3,
    backoff_factor=5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)
```

### 3. 429 Rate Limit 특별 처리
429 에러 발생 시 긴 대기 시간 적용:
```python
if "429" in error_msg:
    wait_time = 30 + (attempt * 30)  # 30, 60, 90초 대기
```

### 4. 요청 간격 조정
- 각 종목마다 **2초** 대기
- 10개마다 **10초** 추가 대기
- 일반 에러 시 **10초** 대기
- 데이터 없을 시 **5초** 대기

### 5. 타임아웃 설정
API 응답 대기 시간 30초로 제한:
```python
hist = ticker.history(period="7d", timeout=30)
```

## 📝 변경된 파일
- `scripts/update_prices.py`: User-Agent, 재시도 로직, 요청 간격 개선

## 🚀 테스트 방법

### 로컬 테스트
```bash
cd us_stock_automation
pip install -r requirements.txt
python test_yfinance.py
```

### GitHub Actions 테스트
1. 코드를 GitHub에 push
2. Actions 탭에서 "Daily US Stock Update" 워크플로우
3. "Run workflow" 버튼 클릭 (수동 실행)
4. 로그 확인

## 🔍 예상 결과
- ✅ 대부분의 종목 데이터 정상 수집
- ⚠️ 일부 상장폐지 종목은 데이터 없음 (정상)
- ❌ API 차단 메시지가 대폭 감소

## ⏱️ 실행 시간
- 기존: ~5분 (실패 시)
- 개선 후: **~30-60분** (안정적 수집)
  - 종목당 평균 12초 (2초 요청 + 10초 배치 대기)
  - 100개 종목 기준: ~20분
  - 속도보다 안정성 우선
  - Rate limit 회피가 최우선

## 📌 참고사항
- Yahoo Finance API는 무료이지만 rate limit 존재
- 너무 빠른 요청은 IP 차단 가능성
- 주말/공휴일엔 최신 데이터가 없을 수 있음
