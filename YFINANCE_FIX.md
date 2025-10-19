# 🔧 yfinance API 차단 문제 해결

## 📋 문제점
GitHub Actions 환경에서 Yahoo Finance API 요청 시 다음 에러 발생:
```
Failed to get ticker 'AAPL' reason: Expecting value: line 1 column 1 (char 0)
$AAPL: possibly delisted; No price data found (period=7d)
```

## 🎯 원인
1. **User-Agent 헤더 없음**: Yahoo Finance가 봇 트래픽을 차단
2. **Rate Limiting**: 너무 빠른 요청 속도
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
HTTP 429, 500번대 에러 발생 시 자동 재시도:
```python
retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
```

### 3. 요청 간격 조정
- 각 종목마다 **1초** 대기
- 50개마다 **5초** 추가 대기
- 데이터 없을 시 **3, 6, 9, 12초** 지수 백오프

### 4. 타임아웃 설정
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
- 개선 후: ~10-15분 (안정적 수집)
  - 종목 수에 따라 다름
  - 속도보다 안정성 우선

## 📌 참고사항
- Yahoo Finance API는 무료이지만 rate limit 존재
- 너무 빠른 요청은 IP 차단 가능성
- 주말/공휴일엔 최신 데이터가 없을 수 있음
