# US 주식 서브패턴 분석 및 AI 예측 시스템

## 개요

미국 주식의 B포인트 구간별 서브패턴을 분석하고, 유사 패턴 매칭을 통해 투자 예측을 제공하는 AI 시스템입니다.

## 주요 기능

### 1. 서브패턴 분석
- **B포인트 구간 추출**: 연속된 B포인트 사이의 가격 패턴 분석
- **정규화**: MinMaxScaler를 사용한 가격 정규화 (ML 학습용)
- **특징 계산**:
  - 수익률 (시작 B가격 → 종료 B가격)
  - 최고수익률 (기간 중 최대 상승률)
  - 최저수익률 (기간 중 최대 하락률)
  - 변동성 (가격 표준편차)
  - 메인 패턴 (기간 중 가장 많이 나타난 패턴)

### 2. 유사 패턴 매칭
- **코사인 유사도**: 현재 진행 중인 패턴과 과거 패턴 비교
- **유사도 임계값**: 70% 이상 유사한 패턴만 선택
- **Top 20 선정**: 가장 유사한 상위 20개 패턴 분석

### 3. AI 예측
- **예상 수익률**: 유사 패턴의 평균 수익률
- **예상 기간**: 목표 달성까지 예상 일수
- **신뢰도**: 유사 패턴 개수 기반 신뢰도 점수
- **투자 점수**: 4가지 요소 기반 종합 점수 (0-100)

### 4. 투자 점수 계산 (0-100점)

```python
투자점수 = 0

# 1. 예상 수익률 (40점)
if 평균_예상수익률 >= 30%: 투자점수 += 40
elif 평균_예상수익률 >= 20%: 투자점수 += 30
elif 평균_예상수익률 >= 10%: 투자점수 += 20
elif 평균_예상수익률 >= 5%: 투자점수 += 10

# 2. 신뢰도 (30점) - 유사 패턴 개수
if len(유사패턴) >= 15: 투자점수 += 30
elif len(유사패턴) >= 10: 투자점수 += 20
elif len(유사패턴) >= 5: 투자점수 += 10

# 3. 현재 패턴 (20점)
if 현재패턴 == '돌파': 투자점수 += 20
elif 현재패턴 == '돌파눌림': 투자점수 += 15
elif 현재패턴 == '박스권': 투자점수 += 10

# 4. 현재 수익률 (10점) - 아직 손실 구간이면 더 좋음
if 현재_수익률 < -5%: 투자점수 += 10
elif 현재_수익률 < 0%: 투자점수 += 7
elif 현재_수익률 < 5%: 투자점수 += 5
```

### 5. 매수가 추천
- **5단계 분할매수**: 현재가 기준 -2%, -4%, -6%, -8%, -10%
- **평균 매수가**: 5단계 평균
- **목표가**: 평균 예상 수익률 기반 계산

### 6. 매수 추천 등급
- **적극 매수**: 투자점수 70점 이상
- **매수**: 투자점수 50~69점
- **관망**: 투자점수 30~49점
- **매수 보류**: 투자점수 30점 미만

## 데이터베이스 구조

### us_subpatterns 테이블
```sql
- 종목코드, 종목명
- 시작_b순번, 시작_b날짜, 시작_b가격
- 종료_b순번, 종료_b날짜, 종료_b가격
- 기간, 수익률, 최고수익률, 최저수익률
- 변동성, 메인패턴
- 정규화_가격 (JSONB)
```

### us_pattern_predictions 테이블
```sql
- 종목코드, 종목명, 분석일시
- 현재_b순번, 현재_b날짜, 현재_b가격
- 현재_경과일수, 현재_수익률, 현재가
- 유사패턴_개수, 평균_예상수익률, 최소_예상수익률, 최대_예상수익률
- 평균_최고수익률, 평균_예상기간
- 투자점수, 신뢰도
- 매수1~5, 평균_매수가, 목표가, 목표_수익률
- 메인패턴, 매수추천
- 유사패턴_목록 (JSONB)
```

## 사용 방법

### 1. 데이터베이스 설정
```bash
# Supabase SQL Editor에서 실행
sql/11_create_us_subpattern_tables.sql
```

### 2. 스크립트 실행
```bash
cd us-stock-automation/scripts
python analyze_us_subpatterns.py
```

### 3. 환경 변수 설정
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
```

### 4. GitHub Actions (자동화)
- 매일 한국시간 오전 9시 자동 실행
- 수동 실행: Actions 탭에서 "Run workflow" 클릭

## 프론트엔드 통합

### us_modal.js
```javascript
// 예측 데이터 자동 로드
const predictionResult = await SWINGINV.db
  .from('us_pattern_predictions')
  .select('*')
  .eq('종목코드', code)
  .order('분석일시', { ascending: false })
  .limit(1)
  .single();

// UI 업데이트
updatePredictionUI(predictionResult.data);
```

### 표시 정보
- **투자점수**: 0-100점 (색상 코딩)
- **메인패턴**: 돌파, 돌파눌림, 박스권, 이탈, 기타
- **매수추천**: 적극 매수, 매수, 관망, 매수 보류
- **예상수익률**: 평균/최소/최대
- **매수가 추천**: 5단계 분할매수가
- **목표가**: 예상 목표가 및 수익률

## 성능 최적화

### 1. 데이터 필터링
- 활성 종목만 분석 (100개)
- 최근 2년 데이터만 사용
- 최소 5일 이상 패턴만 포함

### 2. 병렬 처리
- Promise.all로 데이터 동시 로드
- 배치 삽입 (100개씩)

### 3. 인덱스
```sql
idx_us_subpatterns_code
idx_us_subpatterns_duration
idx_us_subpatterns_return
idx_us_subpatterns_pattern
idx_us_pattern_predictions_code
idx_us_pattern_predictions_date
idx_us_pattern_predictions_score
```

## ML 알고리즘

### 1. 정규화
```python
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
normalized_prices = scaler.fit_transform(prices)
```

### 2. 유사도 계산
```python
from sklearn.metrics.pairwise import cosine_similarity
similarity = cosine_similarity(current_pattern, historical_pattern)
```

### 3. 예측 로직
```python
# 유사도 70% 이상 패턴 선정
similar_patterns = [p for p in all_patterns if similarity(p) > 0.7]

# 상위 20개 선택
top_20 = sorted(similar_patterns, key=lambda x: x.similarity, reverse=True)[:20]

# 평균 예상 수익률 계산
expected_return = mean([p.return for p in top_20])
```

## 모니터링

### 1. 로그 확인
```bash
# GitHub Actions에서 실행 로그 확인
Actions → Daily US Stock Management → 최신 실행
```

### 2. 데이터 검증
```sql
-- 서브패턴 개수 확인
SELECT COUNT(*) FROM us_subpatterns;

-- 예측 데이터 확인
SELECT 종목명, 투자점수, 매수추천, 평균_예상수익률
FROM us_pattern_predictions
ORDER BY 투자점수 DESC
LIMIT 10;

-- 최신 예측 확인
SELECT * FROM us_latest_predictions
WHERE 투자점수 >= 70;
```

## 문제 해결

### 1. 예측 데이터가 없음
- 서브패턴이 충분한지 확인 (최소 10개 이상)
- B포인트 데이터가 있는지 확인
- 가격 데이터가 최신인지 확인

### 2. 유사 패턴이 3개 미만
- 더 많은 서브패턴 데이터 필요
- 유사도 임계값 조정 고려 (현재 0.7)
- 과거 데이터 범위 확대 고려

### 3. 투자점수가 낮음
- 예상 수익률이 낮은 경우
- 유사 패턴이 적은 경우
- 현재 패턴이 불리한 경우 (이탈 등)

## 참고 사항

### 한국 주식과의 차이
- **테이블명**: `subpatterns` → `us_subpatterns`
- **가격 테이블**: `prices` → `us_prices`
- **B포인트 테이블**: `bt_points` → `us_bt_points`
- **통화**: 원화 → 달러
- **Market 필드**: 'KR' → 'US'

### 다음 단계
1. Supabase에서 테이블 생성
2. Python 스크립트 실행으로 데이터 생성
3. 프론트엔드에서 예측 결과 확인
4. GitHub Actions로 자동화 설정
5. 실전 투자 전 충분한 검증

## 라이선스
MIT License

## 작성자
Claude Code - AI-powered stock analysis system
