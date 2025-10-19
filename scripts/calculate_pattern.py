#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
당일 패턴 계산 스크립트
오늘 날짜의 패턴만 계산하여 us_prices.pattern 컬럼에 저장
"""

import os
import requests
from datetime import datetime, date
from dotenv import load_dotenv

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


def get_bt_points(symbol):
    """특정 종목의 b포인트 조회"""
    url = f"{BASE_URL}/us_bt_points"
    params = {
        "종목코드": f"eq.{symbol}",
        "select": "b날짜,b가격",
        "order": "b날짜.asc"
    }

    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()

    return response.json()


def get_today_price(symbol, today):
    """특정 종목의 오늘 가격 조회"""
    url = f"{BASE_URL}/us_prices"
    params = {
        "종목코드": f"eq.{symbol}",
        "날짜": f"eq.{today}",
        "select": "종가"
    }

    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()

    data = response.json()
    return data[0]['종가'] if data else None


def calculate_pattern(close_price, max_b, second_b, mid_b, min_b):
    """패턴 계산"""
    if close_price > max_b:
        return '돌파'
    elif close_price > (second_b if second_b else max_b):
        return '돌파눌림'
    elif close_price > mid_b:
        return '박스권'
    elif close_price >= min_b:
        return '이탈'
    else:
        return '붕괴'


def update_pattern(symbol, today, pattern):
    """패턴 업데이트"""
    url = f"{BASE_URL}/us_prices"
    params = {
        "종목코드": f"eq.{symbol}",
        "날짜": f"eq.{today}"
    }

    data = {"pattern": pattern}
    response = requests.patch(url, headers=HEADERS, params=params, json=data)
    response.raise_for_status()

    return True


def calculate_today_pattern(symbol, today):
    """특정 종목의 당일 패턴 계산 및 업데이트"""

    # 1. b포인트 조회
    bt_points = get_bt_points(symbol)

    if len(bt_points) < 2:
        return 0  # b포인트가 2개 미만이면 스킵

    # 2. b포인트 정렬
    bt_points_sorted = sorted(bt_points, key=lambda x: x['b날짜'])

    # 3. 오늘 날짜가 어느 b포인트 범위에 속하는지 확인
    for i in range(1, len(bt_points_sorted)):
        curr_b = bt_points_sorted[i]
        start_date = curr_b['b날짜'][:10]  # YYYY-MM-DD 형식

        # 다음 b포인트 날짜
        if i + 1 < len(bt_points_sorted):
            next_b = bt_points_sorted[i + 1]
            end_date = next_b['b날짜'][:10]
        else:
            end_date = today

        # 오늘이 이 범위에 속하는지 확인
        if start_date <= today <= end_date:
            # 이전 b가격들
            prev_b_prices = [bt_points_sorted[j]['b가격'] for j in range(i)]
            prev_b_prices_sorted = sorted(prev_b_prices)

            # 통계 계산
            max_b = prev_b_prices_sorted[-1]
            second_b = prev_b_prices_sorted[-2] if len(prev_b_prices_sorted) >= 2 else max_b
            mid_b = prev_b_prices_sorted[len(prev_b_prices_sorted) // 2]
            min_b = prev_b_prices_sorted[0]

            # 오늘 종가 조회
            close_price = get_today_price(symbol, today)

            if close_price is None:
                return 0

            # 패턴 계산
            pattern = calculate_pattern(close_price, max_b, second_b, mid_b, min_b)

            # 패턴 업데이트
            update_pattern(symbol, today, pattern)

            return 1

    return 0


def main():
    print("=" * 60)
    print("📊 당일 패턴 계산 시작")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 오늘 날짜
    today = date.today().strftime('%Y-%m-%d')
    print(f"\n📅 대상 날짜: {today}")

    # 종목 목록 조회
    print("\n📋 종목 목록 조회 중...")
    symbols = get_stock_symbols()
    total_symbols = len(symbols)
    print(f"✓ 총 {total_symbols}개 종목")

    success_count = 0
    skip_count = 0

    print("\n📊 패턴 계산 중...")

    for idx, symbol in enumerate(symbols, 1):
        # 10개마다 진행상황 출력
        if idx % 10 == 0 or idx == 1:
            print(f"  [{idx}/{total_symbols}] 처리 중...")

        try:
            # 당일 패턴 계산 및 업데이트
            updated = calculate_today_pattern(symbol, today)

            if updated > 0:
                success_count += 1
            else:
                skip_count += 1

        except Exception as e:
            print(f"  ❌ {symbol} 패턴 계산 실패: {e}")
            skip_count += 1
            continue

        # 50개마다 상태 출력
        if idx % 50 == 0:
            print(f"  💾 {idx}개 종목 처리 완료")

    print("\n" + "=" * 60)
    print("✅ 패턴 계산 완료!")
    print(f"처리된 종목: {success_count}개")
    print(f"스킵된 종목: {skip_count}개 (당일 데이터 없음 또는 오류)")
    print(f"총 종목: {total_symbols}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
