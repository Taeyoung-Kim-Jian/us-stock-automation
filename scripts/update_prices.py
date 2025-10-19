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


def get_latest_price(symbol):
    """yfinance로 최신 가격 조회"""
    try:
        ticker = yf.Ticker(symbol)
        # 최근 2일 데이터 조회 (당일 + 전날)
        hist = ticker.history(period="2d")

        if hist.empty:
            print(f"  ⚠️  {symbol}: 데이터 없음")
            return None

        # 가장 최근 데이터
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
        print(f"  ❌ {symbol} 조회 실패: {e}")
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
        # 10개마다 진행상황 출력
        if idx % 10 == 0 or idx == 1:
            print(f"  [{idx}/{total_symbols}] 처리 중...")

        # 가격 조회
        price_data = get_latest_price(symbol)

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

        # API 속도 제한 고려 (짧은 대기)
        time.sleep(0.2)

        # 50개마다 상태 출력
        if idx % 50 == 0:
            print(f"  💾 {idx}개 종목 처리 완료")

    print("\n" + "=" * 60)
    print("✅ 가격 업데이트 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {total_symbols}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
