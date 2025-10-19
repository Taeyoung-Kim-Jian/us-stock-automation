#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
당일 패턴 계산 스크립트
오늘 날짜의 패턴만 계산하여 us_prices.pattern 컬럼에 저장
"""

import os
import psycopg2
from datetime import datetime, date
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
    exit(1)


# 패턴 계산 SQL (당일만 처리)
PATTERN_UPDATE_SQL = """
WITH b_points_ranked AS (
    SELECT
        "b날짜",
        "b가격",
        ROW_NUMBER() OVER (ORDER BY "b날짜") as rn
    FROM us_bt_points
    WHERE "종목코드" = %s
),
date_ranges AS (
    SELECT
        curr."b날짜" as start_date,
        COALESCE(
            (SELECT "b날짜" - INTERVAL '1 day'
             FROM b_points_ranked
             WHERE rn = curr.rn + 1),
            CURRENT_DATE::date
        ) as end_date,
        curr.rn,
        ARRAY(
            SELECT "b가격"
            FROM b_points_ranked prev
            WHERE prev.rn < curr.rn
            ORDER BY prev."b날짜"
        ) as prev_b_prices
    FROM b_points_ranked curr
    WHERE curr.rn >= 2
),
b_statistics AS (
    SELECT
        start_date,
        end_date,
        (SELECT MAX(v) FROM unnest(prev_b_prices) v) as max_b,
        (SELECT v FROM unnest(prev_b_prices) v ORDER BY v DESC LIMIT 1 OFFSET 1) as second_b,
        (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v) FROM unnest(prev_b_prices) v) as mid_b,
        (SELECT MIN(v) FROM unnest(prev_b_prices) v) as min_b
    FROM date_ranges
    WHERE array_length(prev_b_prices, 1) >= 1
)
UPDATE us_prices p
SET pattern = CASE
    WHEN p."종가" > s.max_b THEN '돌파'
    WHEN p."종가" > COALESCE(s.second_b, s.max_b) THEN '돌파눌림'
    WHEN p."종가" > s.mid_b THEN '박스권'
    WHEN p."종가" >= s.min_b THEN '이탈'
    ELSE '붕괴'
END
FROM b_statistics s
WHERE p."종목코드" = %s
  AND p."날짜" = %s
  AND p."날짜" >= s.start_date
  AND p."날짜" <= s.end_date
"""


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


def calculate_today_pattern(cursor, symbol, today):
    """특정 종목의 당일 패턴 계산 및 업데이트"""
    cursor.execute(PATTERN_UPDATE_SQL, (symbol, symbol, today))
    return cursor.rowcount


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

    # DB 연결
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()

    success_count = 0
    updated_count = 0
    skip_count = 0

    print("\n📊 패턴 계산 중...")

    for idx, symbol in enumerate(symbols, 1):
        # 10개마다 진행상황 출력
        if idx % 10 == 0 or idx == 1:
            print(f"  [{idx}/{total_symbols}] 처리 중...")

        try:
            # 당일 패턴 계산 및 업데이트
            updated_rows = calculate_today_pattern(cursor, symbol, today)

            if updated_rows > 0:
                updated_count += updated_rows
                success_count += 1
            else:
                skip_count += 1

        except Exception as e:
            print(f"  ❌ {symbol} 패턴 계산 실패: {e}")
            conn.rollback()
            continue

        # 50개마다 커밋
        if idx % 50 == 0:
            conn.commit()
            print(f"  💾 {idx}개 종목 처리 완료")

    # 최종 커밋
    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ 패턴 계산 완료!")
    print(f"처리된 종목: {success_count}개")
    print(f"업데이트된 행: {updated_count}개")
    print(f"스킵된 종목: {skip_count}개 (당일 데이터 없음)")
    print(f"총 종목: {total_symbols}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
