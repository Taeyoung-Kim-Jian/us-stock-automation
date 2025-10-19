#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 주식 가격 업데이트 스크립트
매일 최신 가격 정보를 Supabase DB에 저장
"""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
import time

# 환경변수 로드
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
    exit(1)


def get_stock_symbols():
    """DB에서 미국 주식 종목 코드 목록 조회"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DISTINCT "종목코드"
        FROM us_bt_points
        ORDER BY "종목코드"
    ''')

    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

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


def update_stock_price(cursor, symbol, price_data):
    """us_prices 테이블에 가격 데이터 업데이트"""

    # INSERT ... ON CONFLICT UPDATE 사용
    cursor.execute('''
        INSERT INTO us_prices ("종목코드", "날짜", "시가", "고가", "저가", "종가", "거래량")
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT ("종목코드", "날짜")
        DO UPDATE SET
            "시가" = EXCLUDED."시가",
            "고가" = EXCLUDED."고가",
            "저가" = EXCLUDED."저가",
            "종가" = EXCLUDED."종가",
            "거래량" = EXCLUDED."거래량"
    ''', (
        symbol,
        price_data['date'],
        price_data['open'],
        price_data['high'],
        price_data['low'],
        price_data['close'],
        price_data['volume']
    ))


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

    # DB 연결
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()

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
                update_stock_price(cursor, symbol, price_data)
                success_count += 1
            except Exception as e:
                print(f"  ❌ {symbol} DB 저장 실패: {e}")
                fail_count += 1
                conn.rollback()
                continue
        else:
            fail_count += 1

        # API 속도 제한 고려 (짧은 대기)
        time.sleep(0.1)

        # 50개마다 커밋
        if idx % 50 == 0:
            conn.commit()
            print(f"  💾 {idx}개 종목 저장 완료")

    # 최종 커밋
    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ 가격 업데이트 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {total_symbols}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
