#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 주식 가격 업데이트 스크립트
매일 최신 가격 정보를 Supabase DB에 저장
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
import time
import logging

# yfinance 로거의 레벨을 ERROR로 설정하여 불필요한 로그를 줄임
logging.getLogger('yfinance').setLevel(logging.ERROR)

# User-Agent 설정으로 봇 차단 우회
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# 환경변수 로드
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 환경변수가 설정되지 않았습니다.")
    exit(1)

# Supabase REST API 설정
BASE_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# yfinance용 세션 설정 (User-Agent 추가, 재시도 로직)
def create_yfinance_session():
    """Yahoo Finance API 호출용 세션 생성"""
    session = requests.Session()

    # User-Agent 설정 (브라우저처럼 보이게)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    # 재시도 전략 설정
    retry_strategy = Retry(
        total=3,  # 총 3번 재시도 (너무 많으면 시간 낭비)
        backoff_factor=5,  # 5초, 10초, 15초 대기 (더 긴 대기)
        status_forcelist=[500, 502, 503, 504],  # 429는 제외 (수동 처리)
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

# yfinance 세션 객체 생성
YF_SESSION = create_yfinance_session()


def get_stock_symbols():
    """DB에서 미국 주식 종목 코드 목록 조회"""
    url = f"{BASE_URL}/us_bt_points"
    params = {
        "select": "종목코드",
        "order": "종목코드.asc"
    }

    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()

    data = response.json()
    symbols = list(set([row['종목코드'] for row in data]))
    symbols.sort()

    return symbols


def get_latest_price(symbol, retries=3, session=None):
    """yfinance로 최신 가격 조회 (재시도 로직 포함)"""
    for attempt in range(retries):
        try:
            # 세션을 사용하여 ticker 생성
            ticker = yf.Ticker(symbol, session=session)

            # 최근 7일 데이터 조회 (주말/휴일 고려)
            hist = ticker.history(period="7d", timeout=30)

            if hist.empty:
                # 데이터가 없으면 재시도
                if attempt < retries - 1:
                    time.sleep(5)  # 5초 대기
                    continue
                raise ValueError(f"{symbol}: No data found after {retries} retries")

            # 가장 최근 데이터 (데이터가 있을 경우)
            latest = hist.iloc[-1]

            return {
                'date': latest.name.strftime('%Y-%m-%d'),
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'close': float(latest['Close']),
                'volume': int(latest['Volume'])
            }

        except Exception as e:
            error_msg = str(e)

            # 429 에러 (Rate Limit) 특별 처리
            if "429" in error_msg or "too many" in error_msg.lower():
                wait_time = 30 + (attempt * 30)  # 30, 60, 90초 대기
                if attempt < retries - 1:
                    print(f"  ⏳ {symbol}: Rate limit - {wait_time}초 대기 중...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ❌ {symbol}: Rate limit 초과")
                    return None

            # 마지막 시도 실패 시 에러 메시지 출력
            if attempt == retries - 1:
                # 에러 타입별로 다른 메시지 출력
                if "No data found" in error_msg or "possibly delisted" in error_msg:
                    print(f"  ⚠️  {symbol}: 데이터 없음 (상장폐지 가능성)")
                elif "JSONDecodeError" in str(type(e)) or "Expecting value" in error_msg:
                    print(f"  ❌ {symbol}: API 응답 에러 (차단 가능성)")
                else:
                    print(f"  ❌ {symbol}: {error_msg[:100]}")

            # 재시도 전 대기
            if attempt < retries - 1:
                wait_time = 10  # 일반 에러는 10초 대기
                time.sleep(wait_time)

    return None


def update_stock_price(symbol, price_data):
    """us_prices 테이블에 가격 데이터 업데이트 (Upsert)"""
    url = f"{BASE_URL}/us_prices"

    # 기존 데이터 확인
    params = {
        "종목코드": f"eq.{symbol}",
        "날짜": f"eq.{price_data['date']}"
    }

    check_response = requests.get(url, headers=HEADERS, params=params)
    existing_data = check_response.json()

    data = {
        "종목코드": symbol,
        "날짜": price_data['date'],
        "시가": price_data['open'],
        "고가": price_data['high'],
        "저가": price_data['low'],
        "종가": price_data['close'],
        "거래량": price_data['volume']
    }

    if existing_data:
        # UPDATE
        response = requests.patch(url, headers=HEADERS, params=params, json=data)
    else:
        # INSERT
        response = requests.post(url, headers=HEADERS, json=data)

    response.raise_for_status()
    return True


def main():
    print("=" * 60)
    print("🇺🇸 미국 주식 가격 업데이트 시작")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 종목 목록 조회
    print("\n📋 종목 목록 조회 중...")
    symbols = get_stock_symbols()
    total_symbols = len(symbols)
    print(f"✓ 총 {total_symbols}개 종목")

    success_count = 0
    fail_count = 0

    print("\n📊 가격 업데이트 중...")

    for idx, symbol in enumerate(symbols, 1):
        # 진행상황 출력
        print(f"  [{idx}/{total_symbols}] {symbol} 처리 중...")

        # 가격 조회
        price_data = get_latest_price(symbol, session=YF_SESSION)

        if price_data:
            try:
                # DB 업데이트
                update_stock_price(symbol, price_data)
                success_count += 1
            except Exception as e:
                print(f"  ❌ {symbol} DB 저장 실패: {e}")
                fail_count += 1
                continue
        else:
            fail_count += 1

        # API 속도 제한 고려 (충분한 대기 시간)
        time.sleep(2.0)  # 2초 간격으로 요청 (API 차단 방지)

        # 10개마다 추가 대기
        if idx % 10 == 0:
            print(f"  💾 {idx}개 종목 처리 완료 (10초 대기...)")
            time.sleep(10)  # 10개마다 10초 추가 대기

    print("\n" + "=" * 60)
    print("✅ 가격 업데이트 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {total_symbols}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
