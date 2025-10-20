#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 종목 활성/비활성 관리 자동화 스크립트 (REST API 버전)
DATABASE_URL 없이 ANON_KEY만으로 작동합니다!

실행 방법:
    python scripts/manage_us_stocks_rest.py

환경 변수:
    SUPABASE_URL, SUPABASE_ANON_KEY (또는 SUPABASE_KEY)
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# =====================================================
# 설정값 (필요에 따라 조정)
# =====================================================
MIN_INVESTMENT_SCORE = 60   # 최소 투자점수
MIN_VOLUME = 100000         # 최소 평균거래량
MAX_ACTIVE_STOCKS = 100     # 최대 활성 종목 수
DATA_VALIDITY_DAYS = 30     # 데이터 유효 기간 (일)

# =====================================================
# Supabase 연결
# =====================================================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = (
    os.getenv('SUPABASE_ANON_KEY') or
    os.getenv('SUPABASE_KEY') or
    os.getenv('SUPABASE_SERVICE_KEY')
)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 오류: SUPABASE_URL 또는 SUPABASE_ANON_KEY 환경변수가 없습니다.")
    print("\n.env 파일 확인:")
    print("SUPABASE_URL=https://sssmldmhcfuodutvvcqf.supabase.co")
    print("SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1...")
    sys.exit(1)

# supabase-py 확인
try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py가 설치되지 않았습니다.")
    print("\n설치 방법:")
    print("pip install supabase")
    sys.exit(1)

# Supabase 클라이언트 생성
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 연결 성공")
except Exception as e:
    print(f"❌ Supabase 연결 실패: {e}")
    sys.exit(1)


def calculate_investment_score():
    """투자점수 계산 (실제 데이터 기반)"""
    print("\n📊 1단계: 투자점수 계산 중...")

    try:
        # 모든 종목 가져오기
        result = supabase.table('us_stocks').select('종목코드, pattern').execute()
        stocks = result.data

        if not stocks:
            print("   ⚠️  종목 데이터가 없습니다.")
            return

        print(f"   총 {len(stocks)}개 종목 처리 중...")

        updated_count = 0
        for stock in stocks:
            code = stock['종목코드']
            pattern = stock.get('pattern', '기타')

            score = 0  # 0-100 점수

            # 1. 수익률 점수 (35점 만점)
            try:
                price_result = supabase.table('us_prices').select('종가, 날짜')\
                    .eq('종목코드', code)\
                    .order('날짜', desc=False)\
                    .limit(2)\
                    .execute()

                if len(price_result.data) >= 2:
                    first_price = price_result.data[0]['종가']

                    latest_result = supabase.table('us_prices').select('종가')\
                        .eq('종목코드', code)\
                        .order('날짜', desc=True)\
                        .limit(1)\
                        .single()\
                        .execute()

                    if latest_result.data and first_price > 0:
                        latest_price = latest_result.data['종가']
                        return_pct = ((latest_price - first_price) / first_price) * 100

                        # 수익률이 높을수록 점수 높음 (-50% = 0점, 0% = 17.5점, 50% = 35점)
                        score += max(0, min(35, (return_pct + 50) * 0.35))
            except:
                pass

            # 2. 거래량 점수 (20점 만점)
            try:
                volume_result = supabase.table('us_prices').select('거래량')\
                    .eq('종목코드', code)\
                    .order('날짜', desc=True)\
                    .limit(20)\
                    .execute()

                if volume_result.data:
                    volumes = [v['거래량'] for v in volume_result.data if v.get('거래량')]
                    if volumes:
                        avg_volume = sum(volumes) / len(volumes)

                        # 평균거래량 업데이트
                        supabase.table('us_stocks').update({
                            '평균거래량': int(avg_volume)
                        }).eq('종목코드', code).execute()

                        # 거래량이 높을수록 점수 높음 (log scale)
                        if avg_volume > 0:
                            import math
                            volume_score = min(20, math.log10(avg_volume + 1) * 2)
                            score += volume_score
            except:
                pass

            # 3. 패턴 점수 (25점 만점)
            pattern_scores = {
                '돌파': 25,
                '돌파눌림': 20,
                '박스권': 15,
                '이탈': 5,
                '기타': 10
            }
            score += pattern_scores.get(pattern, 10)

            # 4. B가격 위치 점수 (20점 만점)
            try:
                bt_result = supabase.table('us_bt_points').select('b가격')\
                    .eq('종목코드', code)\
                    .order('b날짜', desc=True)\
                    .limit(1)\
                    .single()\
                    .execute()

                if bt_result.data and bt_result.data.get('b가격'):
                    b_price = bt_result.data['b가격']

                    # 최신 가격 가져오기
                    latest_result = supabase.table('us_prices').select('종가')\
                        .eq('종목코드', code)\
                        .order('날짜', desc=True)\
                        .limit(1)\
                        .single()\
                        .execute()

                    if latest_result.data and b_price > 0:
                        current_price = latest_result.data['종가']
                        deviation = ((current_price - b_price) / b_price) * 100

                        # B가격 근처일수록 점수 높음 (±5% = 20점, ±10% = 10점, ±20% = 0점)
                        abs_dev = abs(deviation)
                        b_score = max(0, 20 - abs_dev)
                        score += b_score
            except:
                pass

            # 최종 점수 (0-100)
            score = max(0, min(100, score))

            # 종목 업데이트
            supabase.table('us_stocks').update({
                '투자점수': round(score, 1),
                '최근업데이트일': datetime.now().date().isoformat()
            }).eq('종목코드', code).execute()

            updated_count += 1
            if updated_count % 50 == 0:
                print(f"   진행: {updated_count}/{len(stocks)}")

        print(f"   ✓ 투자점수 계산 완료: {updated_count}개 종목")

    except Exception as e:
        print(f"   ❌ 오류: {e}")


def manage_active_stocks():
    """종목 활성/비활성 관리"""
    print(f"\n🔄 2단계: 종목 활성/비활성 처리 중...")
    print(f"   기준: 투자점수 >= {MIN_INVESTMENT_SCORE}점")

    try:
        # 모든 종목 가져오기 (투자점수 순)
        result = supabase.table('us_stocks')\
            .select('종목코드, 투자점수, 평균거래량, 활성여부')\
            .order('투자점수', desc=True)\
            .execute()

        stocks = result.data

        if not stocks:
            print("   ⚠️  종목 데이터가 없습니다.")
            return

        # 활성화할 종목 선정 (Top 100)
        active_candidates = [
            s for s in stocks[:MAX_ACTIVE_STOCKS]
            if (s.get('투자점수', 0) >= MIN_INVESTMENT_SCORE and
                s.get('평균거래량', 0) >= MIN_VOLUME)
        ]

        active_codes = [s['종목코드'] for s in active_candidates]

        # 비활성화
        deactivated = 0
        for stock in stocks:
            if stock['종목코드'] not in active_codes and stock.get('활성여부'):
                supabase.table('us_stocks').update({
                    '활성여부': False,
                    '비활성화일': datetime.now().date().isoformat(),
                    '비활성화사유': f"투자점수: {stock.get('투자점수', 0)}점"
                }).eq('종목코드', stock['종목코드']).execute()
                deactivated += 1

        # 활성화
        activated = 0
        for code in active_codes:
            supabase.table('us_stocks').update({
                '활성여부': True,
                '활성화일': datetime.now().date().isoformat(),
                '비활성화일': None,
                '비활성화사유': None
            }).eq('종목코드', code).execute()
            activated += 1

        print(f"   ✓ 비활성화: {deactivated}개 종목")
        print(f"   ✓ 활성화: {activated}개 종목")

    except Exception as e:
        print(f"   ❌ 오류: {e}")


def save_monthly_snapshot():
    """월별 스냅샷 저장 (us_proper에 표시된 종목 기록)"""
    print("\n📸 3단계: 월별 스냅샷 저장 중...")

    try:
        current_month = datetime.now().strftime('%Y-%m')

        # us_swing_proper_view에서 현재 적정가 근접 종목 가져오기
        result = supabase.table('us_swing_proper_view').select(
            '종목코드, 종목명, 적정매수가, 현재가, 괴리율, pattern, 투자점수, b가격일자'
        ).execute()

        proper_stocks = result.data

        if not proper_stocks:
            print("   ⚠️  적정가 근접 종목이 없습니다.")
            return

        saved_count = 0
        updated_count = 0

        for stock in proper_stocks:
            try:
                # UPSERT: 이미 있으면 업데이트, 없으면 삽입
                existing = supabase.table('us_monthly_snapshots').select('id')\
                    .eq('종목코드', stock['종목코드'])\
                    .eq('스냅샷년월', current_month)\
                    .execute()

                snapshot_data = {
                    '종목코드': stock['종목코드'],
                    '종목명': stock['종목명'],
                    '스냅샷년월': current_month,
                    '적정매수가': stock.get('적정매수가'),
                    '현재가': stock.get('현재가'),
                    '괴리율': stock.get('괴리율'),
                    'pattern': stock.get('pattern'),
                    '투자점수': stock.get('투자점수'),
                    'b가격일자': stock.get('b가격일자')
                }

                if existing.data:
                    # 이미 존재하면 업데이트
                    supabase.table('us_monthly_snapshots').update(snapshot_data)\
                        .eq('종목코드', stock['종목코드'])\
                        .eq('스냅샷년월', current_month)\
                        .execute()
                    updated_count += 1
                else:
                    # 새로 삽입
                    supabase.table('us_monthly_snapshots').insert(snapshot_data).execute()
                    saved_count += 1

            except Exception as e:
                print(f"   ⚠️  {stock['종목코드']} 저장 실패: {e}")
                continue

        print(f"   ✓ 신규 저장: {saved_count}개 종목")
        print(f"   ✓ 업데이트: {updated_count}개 종목")
        print(f"   ✓ 스냅샷 년월: {current_month}")

    except Exception as e:
        print(f"   ❌ 오류: {e}")


def generate_report():
    """관리 현황 리포트 생성"""
    print("\n" + "="*60)
    print("📊 미국 종목 관리 현황 리포트")
    print("="*60)

    try:
        # 전체 통계
        result = supabase.table('us_stocks').select('활성여부, 투자점수').execute()
        stocks = result.data

        if not stocks:
            print("\n⚠️  데이터가 없습니다.")
            return

        total = len(stocks)
        active = len([s for s in stocks if s.get('활성여부')])
        inactive = total - active

        active_scores = [s.get('투자점수', 0) for s in stocks if s.get('활성여부')]
        avg_score = sum(active_scores) / len(active_scores) if active_scores else 0
        max_score = max(active_scores) if active_scores else 0
        min_score = min(active_scores) if active_scores else 0

        print(f"\n📈 전체 현황:")
        print(f"   전체 종목: {total:,}개")
        print(f"   활성 종목: {active:,}개")
        print(f"   비활성 종목: {inactive:,}개")
        print(f"   활성 종목 평균 점수: {avg_score:.1f}점")
        print(f"   최고 점수: {max_score:.1f}점")
        print(f"   최저 점수: {min_score:.1f}점")

        # Top 10
        print(f"\n🏆 Top 10 활성 종목:")
        top_stocks = sorted(
            [s for s in stocks if s.get('활성여부')],
            key=lambda x: x.get('투자점수', 0),
            reverse=True
        )[:10]

        for i, stock in enumerate(top_stocks, 1):
            code = stock.get('종목코드', 'N/A')
            score = stock.get('투자점수', 0)
            print(f"   {i:2d}. {code} - {score:.1f}점")

    except Exception as e:
        print(f"\n❌ 리포트 생성 오류: {e}")

    print("\n" + "="*60)
    print(f"⏰ 리포트 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 미국 종목 관리 시스템 시작 (REST API 버전)")
    print("=" * 60)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 투자점수 계산
        calculate_investment_score()

        # 2. 종목 활성/비활성 처리
        manage_active_stocks()

        # 3. 월별 스냅샷 저장
        save_monthly_snapshot()

        # 4. 리포트 생성
        generate_report()

        print("\n✅ 모든 작업이 성공적으로 완료되었습니다!")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
