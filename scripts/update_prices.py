#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 주식 가격 업데이트 스크립트 (네이버 금융 기반)
매일 최신 가격 정보를 Supabase DB에 저장
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
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


def fetch_price_from_naver(symbol):
    """
    네이버 금융에서 미국 주식 최근 거래일 시세 가져오기 (HTML 스크래핑)
    NASDAQ: 종목코드.O (예: AAPL.O)
    NYSE: 종목코드 그대로 (예: JPM)
    """
    # NASDAQ (.O) 먼저 시도, 실패하면 NYSE (그대로) 시도
    symbols_to_try = [f"{symbol}.O", symbol]

    for stock_code in symbols_to_try:
        try:
            url = f"https://finance.naver.com/world/sise.naver?symbol={stock_code}"

            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # 시세 테이블 찾기
            table = soup.select_one("table.tbl_exchange")
            if not table:
                continue

            rows = table.select("tr")
            valid_rows = [r for r in rows if len(r.select("td")) >= 7 and r.select_one("td.date")]

            if not valid_rows:
                continue

            # 첫 번째 행 (최근 거래일)
            cols = [c.text.strip().replace(",", "") for c in valid_rows[0].select("td")]

            if len(cols) < 7:
                continue

            # 날짜 파싱 (YYYY.MM.DD → YYYY-MM-DD)
            date_str = cols[0].replace(".", "-")

            return {
                "date": date_str,
                "close": float(cols[1]) if cols[1] else 0,
                "open": float(cols[3]) if cols[3] else 0,
                "high": float(cols[4]) if cols[4] else 0,
                "low": float(cols[5]) if cols[5] else 0,
                "volume": int(float(cols[6])) if cols[6] else 0,
            }

        except:
            continue

    # 모든 시도 실패
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
    print("🇺🇸 미국 주식 가격 업데이트 시작 (네이버 금융 스크래핑)")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 종목 목록 조회
    print("\n📋 종목 목록 조회 중...")
    symbols = get_stock_symbols()
    total_symbols = len(symbols)
    print(f"✓ 총 {total_symbols}개 종목")

    success_count = 0
    fail_count = 0

    print("\n📊 가격 업데이트 중...\n")

    for idx, symbol in enumerate(symbols, 1):
        # 가격 조회
        price_data = fetch_price_from_naver(symbol)

        if price_data:
            try:
                # DB 업데이트
                update_stock_price(symbol, price_data)
                print(f"  [{idx}/{total_symbols}] ✅ {symbol}: {price_data['date']} ${price_data['close']:.2f}")
                success_count += 1
            except Exception as e:
                print(f"  [{idx}/{total_symbols}] ❌ {symbol}: DB 저장 실패 - {e}")
                fail_count += 1
        else:
            print(f"  [{idx}/{total_symbols}] ⚠️  {symbol}: 데이터 없음")
            fail_count += 1

        # 네이버 서버 부하 방지
        time.sleep(0.4)

        # 50개마다 진행상황
        if idx % 50 == 0:
            print(f"\n  💾 {idx}/{total_symbols} 처리 완료 (성공: {success_count}, 실패: {fail_count})\n")

    print("\n" + "=" * 60)
    print("✅ 가격 업데이트 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {total_symbols}개")
    print(f"성공률: {success_count/total_symbols*100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
