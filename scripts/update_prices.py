#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 주식 가격 업데이트 스크립트 (한국투자증권 API)
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
KIS_APP_KEY = os.getenv('KIS_APP_KEY')
KIS_APP_SECRET = os.getenv('KIS_APP_SECRET')
KIS_IS_REAL = os.getenv('KIS_IS_REAL', 'false').lower() == 'true'

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 환경변수가 설정되지 않았습니다.")
    exit(1)

if not KIS_APP_KEY or not KIS_APP_SECRET:
    print("❌ KIS_APP_KEY 또는 KIS_APP_SECRET 환경변수가 설정되지 않았습니다.")
    exit(1)

# Supabase REST API 설정
BASE_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}


class KISStockAPI:
    """한국투자증권 API 클라이언트"""

    def __init__(self, app_key, app_secret, is_real=True):
        self.app_key = app_key
        self.app_secret = app_secret

        if is_real:
            self.base_url = "https://openapi.koreainvestment.com:9443"
        else:
            self.base_url = "https://openapivts.koreainvestment.com:29443"

        self.access_token = None
        self._get_access_token()

    def _get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"

        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            self.access_token = result.get("access_token")
            print("✓ 한투 API 접근 토큰 발급 완료")

        except Exception as e:
            print(f"❌ 토큰 발급 실패: {e}")
            raise

    def get_current_price(self, exchange_code, symbol):
        """해외주식 현재가 조회"""
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "HHDFS00000300"
        }

        params = {
            "AUTH": "",
            "EXCD": exchange_code,
            "SYMB": symbol
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get("rt_cd") == "0":
                output = result.get("output", {})

                # 현재 날짜 (미국 시간 기준은 API에서 제공 안하므로 한국 시간 사용)
                today = datetime.now().strftime("%Y-%m-%d")

                return {
                    "date": today,
                    "close": float(output.get("last", 0)),
                    "open": float(output.get("open", 0)) if output.get("open") else float(output.get("last", 0)),
                    "high": float(output.get("high", 0)) if output.get("high") else float(output.get("last", 0)),
                    "low": float(output.get("low", 0)) if output.get("low") else float(output.get("last", 0)),
                    "volume": int(output.get("tvol", 0))
                }
            else:
                return None

        except Exception as e:
            return None


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


def determine_exchange(symbol):
    """
    종목 코드로 거래소 구분
    간단한 휴리스틱: 대부분 나스닥이므로 NAS 먼저 시도
    """
    # 일반적으로 알려진 NYSE 종목들
    nyse_stocks = {
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW',
        'USB', 'PNC', 'TFC', 'COF', 'AXP', 'BK', 'STT', 'MTB',
        'FITB', 'HBAN', 'RF', 'CFG', 'KEY', 'WMT', 'JNJ', 'PG',
        'KO', 'PEP', 'DIS', 'NKE', 'MCD', 'HD', 'CVX', 'XOM',
        'BA', 'CAT', 'MMM', 'GE', 'UNH', 'UPS', 'HON', 'IBM',
        'V', 'MA', 'T', 'VZ', 'PM', 'MO', 'ABT', 'TMO', 'DHR',
        'BMY', 'LLY', 'ABBV', 'MRK', 'PFE', 'AMGN', 'GILD'
    }

    return "NYS" if symbol in nyse_stocks else "NAS"


def update_stock_exchange(symbol, exchange_code):
    """us_bt_points 테이블에 거래소 정보 업데이트 (Upsert)"""
    url = f"{BASE_URL}/us_bt_points"

    # 거래소명 변환
    exchange_name = "NASDAQ" if exchange_code == "NAS" else "NYSE" if exchange_code == "NYS" else "AMEX"

    # 기존 데이터 확인
    params = {
        "종목코드": f"eq.{symbol}"
    }

    check_response = requests.get(url, headers=HEADERS, params=params)
    existing_data = check_response.json()

    data = {
        "거래소": exchange_name
    }

    try:
        if existing_data:
            # UPDATE - 기존 레코드가 있으면 업데이트
            response = requests.patch(url, headers=HEADERS, params=params, json=data)
        else:
            # INSERT - 없으면 새로 생성 (종목코드 포함)
            data["종목코드"] = symbol
            response = requests.post(url, headers=HEADERS, json=data)

        response.raise_for_status()
        return True
    except Exception as e:
        # 거래소 컬럼이 없거나 에러 발생 시 무시
        return False


def update_stock_price(symbol, price_data, exchange_code=None):
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

    # 거래소 정보 업데이트 (선택사항)
    if exchange_code:
        update_stock_exchange(symbol, exchange_code)

    return True


def main():
    print("=" * 60)
    print("🇺🇸 미국 주식 가격 업데이트 시작 (한국투자증권 API)")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 모드: {'실전투자' if KIS_IS_REAL else '모의투자'}")
    print("=" * 60)

    # 한투 API 클라이언트 생성
    api = KISStockAPI(KIS_APP_KEY, KIS_APP_SECRET, KIS_IS_REAL)

    # 종목 목록 조회
    print("\n📋 종목 목록 조회 중...")
    symbols = get_stock_symbols()
    total_symbols = len(symbols)
    print(f"✓ 총 {total_symbols}개 종목")

    success_count = 0
    fail_count = 0

    print("\n📊 가격 업데이트 중...\n")

    for idx, symbol in enumerate(symbols, 1):
        # 거래소 구분
        exchange = determine_exchange(symbol)

        # 가격 조회
        price_data = api.get_current_price(exchange, symbol)

        if price_data and price_data['close'] > 0:
            try:
                # DB 업데이트 (거래소 정보 포함)
                update_stock_price(symbol, price_data, exchange)
                print(f"  [{idx}/{total_symbols}] ✅ {symbol} ({exchange}): ${price_data['close']:.2f}")
                success_count += 1
            except Exception as e:
                print(f"  [{idx}/{total_symbols}] ❌ {symbol}: DB 저장 실패 - {e}")
                fail_count += 1
        else:
            # NAS 실패 시 NYS 시도
            if exchange == "NAS":
                price_data = api.get_current_price("NYS", symbol)
                if price_data and price_data['close'] > 0:
                    try:
                        # DB 업데이트 (NYS로 거래소 정보 저장)
                        update_stock_price(symbol, price_data, "NYS")
                        print(f"  [{idx}/{total_symbols}] ✅ {symbol} (NYS): ${price_data['close']:.2f}")
                        success_count += 1
                        continue
                    except Exception as e:
                        print(f"  [{idx}/{total_symbols}] ❌ {symbol}: DB 저장 실패 - {e}")
                        fail_count += 1
                        continue

            print(f"  [{idx}/{total_symbols}] ⚠️  {symbol}: 데이터 없음")
            fail_count += 1

        # API 호출 제한 대응
        time.sleep(0.1)

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
