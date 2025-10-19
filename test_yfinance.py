#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yfinance 연결 테스트 스크립트
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yfinance as yf
import time

def create_yfinance_session():
    """Yahoo Finance API 호출용 세션 생성"""
    session = requests.Session()

    # User-Agent 설정 (브라우저처럼 보이게)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    # 재시도 전략 설정
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

def test_ticker(symbol, session):
    """단일 종목 테스트"""
    print(f"\n테스트 종목: {symbol}")
    print("-" * 40)

    try:
        ticker = yf.Ticker(symbol, session=session)
        hist = ticker.history(period="7d", timeout=30)

        if hist.empty:
            print(f"❌ {symbol}: 데이터 없음")
            return False

        latest = hist.iloc[-1]
        print(f"✅ {symbol}: 성공")
        print(f"   날짜: {latest.name.strftime('%Y-%m-%d')}")
        print(f"   종가: ${latest['Close']:.2f}")
        print(f"   거래량: {int(latest['Volume']):,}")
        return True

    except Exception as e:
        print(f"❌ {symbol}: 에러 - {str(e)[:100]}")
        return False

def main():
    print("=" * 60)
    print("🧪 yfinance 연결 테스트")
    print("=" * 60)

    # 세션 생성
    session = create_yfinance_session()

    # 테스트할 종목들
    test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]

    success = 0
    total = len(test_symbols)

    for symbol in test_symbols:
        if test_ticker(symbol, session):
            success += 1
        time.sleep(1)  # 1초 대기

    print("\n" + "=" * 60)
    print(f"테스트 결과: {success}/{total} 성공")
    print("=" * 60)

if __name__ == "__main__":
    main()
