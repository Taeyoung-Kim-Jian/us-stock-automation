#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 주식 가격 업데이트 스크립트 (네이버 금융 기반)
매일 최신 가격 정보를 Supabase DB에 저장
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
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
    네이버 금융 API에서 미국 주식 시세 가져오기
    API URL: https://polling.finance.naver.com/api/realtime/worldstock/stock/{symbol}
    """
    try:
        # 네이버 금융 API (비공식)
        api_url = f"https://polling.finance.naver.com/api/realtime/worldstock/stock/{symbol}"

        response = requests.get(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.naver.com/"
            },
            timeout=15
        )
        response.raise_for_status()

        data = response.json()

        # API 응답 확인
        if not data or "datas" not in data:
            return None

        stock_data = data["datas"][0] if data["datas"] else None
        if not stock_data:
            return None

        # 필요한 데이터 추출 (모든 숫자 필드에서 쉼표 제거)
        close_str = str(stock_data.get("closePrice", "0"))
        close = float(close_str.replace(",", ""))

        open_str = str(stock_data.get("openPrice", close_str))
        open_price = float(open_str.replace(",", ""))

        high_str = str(stock_data.get("highPrice", close_str))
        high_price = float(high_str.replace(",", ""))

        low_str = str(stock_data.get("lowPrice", close_str))
        low_price = float(low_str.replace(",", ""))

        # 거래량 (쉼표 제거)
        volume_str = str(stock_data.get("accumulatedTradingVolume", "0"))
        volume = int(volume_str.replace(",", ""))

        # 거래일 (localTradedAt: "20250117" 형식)
        date_str = str(stock_data.get("localTradedAt", ""))
        if len(date_str) == 8:
            trade_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        return {
            "date": trade_date,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close,
            "volume": volume
        }

    except requests.exceptions.RequestException as e:
        print(f"  ❌ {symbol}: 네트워크 에러 - {str(e)[:80]}")
        return None
    except Exception as e:
        print(f"  ❌ {symbol}: 파싱 에러 - {str(e)[:80]}")
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
    print("🇺🇸 미국 주식 가격 업데이트 시작 (네이버 금융)")
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
        print(f"  [{idx}/{total_symbols}] {symbol} 처리 중...")

        # 가격 조회
        price_data = fetch_price_from_naver(symbol)

        if price_data:
            try:
                # DB 업데이트
                update_stock_price(symbol, price_data)
                print(f"  ✅ {symbol}: {price_data['date']} ${price_data['close']:.2f}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ {symbol} DB 저장 실패: {e}")
                fail_count += 1
                continue
        else:
            fail_count += 1

        # 네이버 서버 부하 방지 (짧은 대기)
        time.sleep(0.5)

        # 10개마다 상태 출력
        if idx % 10 == 0:
            print(f"  💾 {idx}개 종목 처리 완료\n")

    print("\n" + "=" * 60)
    print("✅ 가격 업데이트 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {total_symbols}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
