# ⚾ FACEMETRICS — KBO 선발투수 관상×운세 Head-to-Head 시스템 기획서

> **프로젝트명:** FACEMETRICS — 관상과 운세로 보는 오늘의 승리투수
> **태그라인:** "확률이 반반이면 관상이 답이다"
> **버전:** v1.1
> **작성일:** 2026-04-13

---

## 1. 프로젝트 개요

### 1-1. 배경 및 목적

KBO 리그는 매 경기 당일 선발투수를 발표한다. 팬들은 선발 매치업을 보고 승패를 예측하는 재미를 즐기는데, **FACEMETRICS**는 여기에 **관상학**과 **운세(사주/별자리/띠)**라는 전혀 새로운 관점을 결합하여, 두 선발투수의 "기운"을 야구 퍼포먼스 요소에 매핑해 점수화하는 **엔터테인먼트 콘텐츠 서비스**를 만드는 것이 목적이다. 통계로 승부가 가리기 어려운 매치업에서 "확률이 반반이면 관상이 답이다"라는 직관을 시각화하는 것이 핵심 가치다.

### 1-2. 핵심 컨셉

```
당일 선발투수 매치업 발표
        ↓
투수 A의 관상 + 운세  vs  투수 B의 관상 + 운세
        ↓
야구 퍼포먼스 5개 항목에 매핑 (각 20점)
        ↓
100점 만점 Head-to-Head 비교 카드 생성
        ↓
"오늘의 관운상 승자" 예측 콘텐츠 제공
```

### 1-3. 타겟 사용자

- KBO 팬 중 재미 위주 승부예측을 즐기는 층
- 관상/운세/사주에 관심 있는 일반 대중
- 야구 커뮤니티(에펨코리아, 엠엘비파크, 디시 야갤 등) 공유 콘텐츠 소비자

### 1-4. 핵심 차별점

- 기존 승부예측: 성적, 통계(ERA, WHIP, FIP) 기반 → **이성적 분석**
- 본 서비스: 관상 + 운세 기반 → **비이성적이지만 재미있는 분석**
- 두 가지의 충돌 자체가 콘텐츠 (맞추면 "역시 관상!", 틀리면 "운이 안 따라줬네")

---

## 2. 평가 체계 설계

### 2-1. 5가지 항목 총괄표 (각 20점, 총 100점)

| # | 항목명 | 야구 의미 | 관상 요소 (10점) | 운세 요소 (10점) |
|---|--------|-----------|-----------------|-----------------|
| 1 | **제구력 (Command)** | 볼배합·코너워크·사사구 관리 | 눈매의 안정감·또렷함 | 오늘의 집중운·정밀운 |
| 2 | **구위 (Stuff)** | 구속·무브먼트·삼진능력 | 턱·광대·하관의 강인함 | 오늘의 체력운·활력운 |
| 3 | **멘탈 (Composure)** | 위기관리·득점권 피안타율·페이스조절 | 이마 넓이·인중 깊이·미간 | 오늘의 정신운·인내운 |
| 4 | **지배력 (Dominance)** | 이닝소화·QS율·경기 지배 | 눈썹 기세·얼굴 균형·이목구비 비율 | 오늘의 승부운·권위운 |
| 5 | **운명력 (Destiny)** | 상대전적·구장궁합·팀운 | 전체 인상 조화도·얼굴형 | 오늘의 총운세·상성운 |

> **점수 구성:** 관상 점수(10점) + 운세 점수(10점) = 항목당 20점

---

### 2-2. 항목별 세부 평가 기준

#### ① 제구력 (Command) — "공을 꽂는 눈"

**야구적 의미:**
선발투수에게 가장 중요한 능력. 원하는 코스에 공을 꽂을 수 있는가, 볼넷을 남발하지 않는가, 포수 미트에 정확히 넣는 섬세함.

**관상 평가 (10점):**

| 세부 요소 | 배점 | 평가 기준 |
|-----------|------|-----------|
| 눈매의 선명도 | 4점 | 눈동자가 또렷하고 초점이 분명한가. 흐릿하거나 풀린 눈은 감점. |
| 눈의 안정감 | 3점 | 눈이 안정적으로 고정되어 보이는가. 불안정하게 흔들리는 인상은 감점. |
| 눈과 눈썹 간격 | 3점 | 적당한 간격 = 여유 있는 시야. 너무 좁으면 조급, 너무 넓으면 산만. |

**운세 평가 (10점):**

| 세부 요소 | 배점 | 산출 기준 |
|-----------|------|-----------|
| 별자리 집중운 | 4점 | 당일 별자리 운세에서 "집중", "세밀", "정확" 키워드 기반 |
| 띠 정밀운 | 3점 | 12지신 당일 운에서 세심함·꼼꼼함 관련 운 |
| 사주 일간 기운 | 3점 | 오행(목화토금수) 중 당일 상생/상극 관계로 제어력 판단 |

---

#### ② 구위 (Stuff) — "강한 턱, 강한 공"

**야구적 의미:**
공 자체의 위력. 구속, 공의 무브먼트, 타자를 압도하는 삼진 능력. 피지컬이 뒷받침되어야 하는 영역.

**관상 평가 (10점):**

| 세부 요소 | 배점 | 평가 기준 |
|-----------|------|-----------|
| 턱·하관 라인 | 4점 | 각진 턱, 단단한 하관 = 강인한 체력과 파워. 둥근 턱은 약간 감점. |
| 광대뼈 돌출도 | 3점 | 적당히 나온 광대 = 에너지가 넘침. 지나치게 돌출 시 과잉, 평면적이면 부족. |
| 코의 크기·높이 | 3점 | 콧대가 적당히 높고 넓은 콧볼 = 호흡·체력의 상징. |

**운세 평가 (10점):**

| 세부 요소 | 배점 | 산출 기준 |
|-----------|------|-----------|
| 별자리 활력운 | 4점 | "에너지", "힘", "활력", "건강" 키워드 기반 |
| 띠 체력운 | 3점 | 12지신 당일 체력·건강 운세 |
| 사주 오행 강도 | 3점 | 일간의 오행 세기와 당일 천간 지지의 생조(生助) 관계 |

---

#### ③ 멘탈 (Composure) — "넓은 이마, 흔들리지 않는 마운드"

**야구적 의미:**
주자가 나가도 흔들리지 않는 정신력. 위기 상황 관리, 풀카운트에서의 승부, 홈런 맞고도 다음 타자를 잡는 회복력.

**관상 평가 (10점):**

| 세부 요소 | 배점 | 평가 기준 |
|-----------|------|-----------|
| 이마 넓이·높이 | 4점 | 넓고 높은 이마 = 사고력과 판단력. 좁거나 주름 많으면 감점. |
| 인중 깊이·길이 | 3점 | 뚜렷한 인중 = 인내심과 지구력. 짧거나 흐릿하면 감점. |
| 미간 간격 | 3점 | 적절한 미간 = 차분함. 너무 좁으면 조급함, 너무 넓으면 무심함. |

**운세 평가 (10점):**

| 세부 요소 | 배점 | 산출 기준 |
|-----------|------|-----------|
| 별자리 정신운 | 4점 | "안정", "평화", "차분", "인내" 키워드 기반 |
| 띠 인내운 | 3점 | 12지신 당일 심리안정·스트레스 관련 운 |
| 사주 용신 작용 | 3점 | 용신(사주에서 가장 필요한 오행)이 당일 활성화되는가 |

---

#### ④ 지배력 (Dominance) — "기세 등등한 눈썹"

**야구적 의미:**
경기를 완전히 지배하는 능력. 6이닝 이상 던지며 QS(퀄리티스타트) 달성, 상대 타선을 완전 침묵시키는 압도적 존재감.

**관상 평가 (10점):**

| 세부 요소 | 배점 | 평가 기준 |
|-----------|------|-----------|
| 눈썹의 기세·농도 | 4점 | 짙고 힘 있는 눈썹 = 강한 카리스마. 옅거나 산발적이면 감점. |
| 얼굴 좌우 균형 | 3점 | 균형 잡힌 이목구비 = 안정된 퍼포먼스. 비대칭이 심하면 감점. |
| 이목구비 비율 | 3점 | 황금비에 가까운 배치 = 전체적 조화와 완성도. |

**운세 평가 (10점):**

| 세부 요소 | 배점 | 산출 기준 |
|-----------|------|-----------|
| 별자리 승부운 | 4점 | "리더십", "주도", "승리", "지배" 키워드 기반 |
| 띠 권위운 | 3점 | 12지신 당일 사회운·대인 관계에서의 우위 |
| 사주 관성(官星) | 3점 | 관성(나를 극하는 오행)의 강약 → 적절하면 통제력, 과하면 압박 |

---

#### ⑤ 운명력 (Destiny) — "하늘이 내린 얼굴, 오늘의 운"

**야구적 의미:**
통계로 설명 안 되는 영역. 상대와의 전적, 특정 구장에서의 궁합, 팀 분위기, 경기 흐름이 자기편인가. "야구는 운빨"의 영역.

**관상 평가 (10점):**

| 세부 요소 | 배점 | 평가 기준 |
|-----------|------|-----------|
| 전체 인상 조화도 | 4점 | 첫인상에서 풍기는 "되는 사람" 느낌. 관상학의 총체적 기운. |
| 얼굴형 | 3점 | 각 얼굴형(둥근·긴·각진·역삼각)의 운세적 해석 적용. |
| 귀·입 조화 | 3점 | 귀 크기(복), 입 모양(실행력)의 관상적 해석. |

**운세 평가 (10점):**

| 세부 요소 | 배점 | 산출 기준 |
|-----------|------|-----------|
| 별자리 총운 | 3점 | 당일 별자리 종합 운세 등급 |
| 띠 총운 | 3점 | 12지신 당일 종합 운세 등급 |
| 상성(相性) 운 | 4점 | 두 투수 간 띠 궁합 + 별자리 궁합 + 오행 상생상극 관계. **이 항목만 상대 투수와의 관계로 산출** |

---

### 2-3. 상성(相性) 시스템 — 운명력의 핵심

운명력 항목의 "상성운"(4점)은 두 투수의 관계에서 산출되므로 별도 설계가 필요하다.

**띠 궁합표 (12지신):**

| 관계 | 설명 | 점수 영향 |
|------|------|-----------|
| 삼합(三合) | 자-진-신, 축-사-유, 인-오-술, 묘-미-해 | +2 |
| 육합(六合) | 자-축, 인-해, 묘-술, 진-유, 사-신, 오-미 | +1.5 |
| 원진(怨嗔) | 자-미, 축-오, 인-사, 묘-진, 신-해, 유-술 | -1.5 |
| 충(沖) | 자-오, 축-미, 인-신, 묘-유, 진-술, 사-해 | -2 |
| 기본 | 위에 해당하지 않는 관계 | 0 |

**별자리 원소 궁합:**

| 원소 조합 | 관계 | 점수 영향 |
|-----------|------|-----------|
| 같은 원소 (불-불, 물-물 등) | 동질 | +1 |
| 불-바람, 물-흙 | 상생 | +1.5 |
| 불-물, 바람-흙 | 상극 | -1 |
| 나머지 조합 | 중립 | 0 |

> 상성운 기본 점수 2점에서 위 두 궁합의 합산을 더해 0~4점 범위로 클램핑.

---

## 3. 스코어링 엔진 로직

### 3-1. 점수 산출 흐름

```
[입력]
├── 투수 프로필 사진 → Claude Vision API → 관상 원점수 (항목당 0~10)
├── 투수 생년월일/띠/별자리 + 당일 날짜 → Claude API → 운세 원점수 (항목당 0~10)
└── 상대 투수 띠/별자리 → 상성 계산 모듈 → 상성 보정값

[처리]
├── 항목별 점수 = 관상 원점수 + 운세 원점수 (각 10점, 합산 20점)
├── 운명력 항목만 상성 보정값 반영
└── 총점 = 5개 항목 합산 (100점 만점)

[출력]
├── 투수별 5개 항목 점수
├── 투수별 총점
├── 항목별 Head-to-Head 비교
└── 최종 승자 판정 + 한줄 코멘트
```

### 3-2. 점수 안정화 규칙

관상 점수는 사진이 바뀌지 않는 한 동일해야 하고, 운세 점수만 날마다 변해야 재미가 있다.

| 구분 | 변동성 | 전략 |
|------|--------|------|
| 관상 점수 | **고정** (시즌 중 불변) | 시즌 초 1회 산출 후 DB 캐싱. 사진 변경 시만 재산출. |
| 운세 점수 | **매일 변동** | 날짜 + 투수 생년월일을 시드로 결정론적 생성. 같은 날 같은 투수는 항상 같은 점수. |
| 상성 점수 | **매치업별 고정** | 두 투수 조합이 같으면 항상 동일. 룰 기반 계산 (AI 불필요). |

### 3-3. 결정론적 운세 생성 방법

Claude API의 temperature를 0으로 설정하더라도 완전한 결정론적 출력은 보장되지 않으므로, 다음과 같은 보완 전략을 사용한다.

1. **1차 생성:** Claude API로 운세 점수 생성
2. **즉시 캐싱:** 생성 즉시 DB에 `(투수ID, 날짜, 항목, 점수)` 저장
3. **2차 요청부터:** DB 캐시 반환 (API 미호출)
4. **폴백:** 날짜 + 생년월일 기반 해시 함수로 유사난수 생성 (API 장애 시)

---

## 4. AI 프롬프트 설계

### 4-1. 관상 분석 프롬프트 (Claude Vision)

```
[시스템 프롬프트]
당신은 30년 경력의 관상학 전문가이자 KBO 야구 분석가입니다.
선발투수의 얼굴 사진을 보고, 야구 퍼포먼스와 연결된 관상 요소를
정밀하게 분석하여 점수를 부여합니다.

반드시 아래 JSON 형식으로만 응답하세요.

[사용자 프롬프트]
이 KBO 선발투수의 관상을 분석해주세요.

## 평가 항목 및 기준

1. 제구력 (Command) — 눈매의 선명도(4), 눈의 안정감(3), 눈-눈썹 간격(3)
2. 구위 (Stuff) — 턱·하관 라인(4), 광대뼈(3), 코의 크기·높이(3)
3. 멘탈 (Composure) — 이마 넓이·높이(4), 인중(3), 미간(3)
4. 지배력 (Dominance) — 눈썹 기세·농도(4), 좌우 균형(3), 이목구비 비율(3)
5. 운명력 (Destiny) — 전체 인상 조화도(4), 얼굴형(3), 귀·입 조화(3)

## 응답 형식 (JSON)
{
  "pitcher_name": "이름",
  "command": { "score": 0, "detail": "눈매가... 총평" },
  "stuff": { "score": 0, "detail": "턱라인이... 총평" },
  "composure": { "score": 0, "detail": "이마가... 총평" },
  "dominance": { "score": 0, "detail": "눈썹이... 총평" },
  "destiny": { "score": 0, "detail": "전체적으로... 총평" },
  "overall_impression": "한줄 관상 총평"
}

각 score는 0~10 사이 정수입니다.
```

### 4-2. 운세 분석 프롬프트 (Claude Text)

```
[시스템 프롬프트]
당신은 사주명리학, 별자리 운세, 12지신 운세에 정통한 운세 전문가이며
동시에 KBO 야구 전문 해설가입니다.
투수의 생년월일과 오늘 날짜를 기반으로 야구 퍼포먼스에 매핑된
운세 점수를 산출합니다.

반드시 아래 JSON 형식으로만 응답하세요.

[사용자 프롬프트]
## 투수 정보
- 이름: {pitcher_name}
- 생년월일: {birth_date} ({zodiac_sign} / {chinese_zodiac})
- 오늘 날짜: {today_date}
- 상대팀: {opponent_team}
- 경기 구장: {stadium}

## 평가 항목
1. 제구력 운세 — 오늘의 집중운, 정밀운 (10점)
2. 구위 운세 — 오늘의 체력운, 활력운 (10점)
3. 멘탈 운세 — 오늘의 정신운, 인내운 (10점)
4. 지배력 운세 — 오늘의 승부운, 권위운 (10점)
5. 운명력 운세 — 오늘의 총운세 (10점)

## 응답 형식 (JSON)
{
  "pitcher_name": "이름",
  "date": "2026-04-13",
  "command_fortune": { "score": 0, "reading": "오늘 OO자리는..." },
  "stuff_fortune": { "score": 0, "reading": "체력운이..." },
  "composure_fortune": { "score": 0, "reading": "정신적으로..." },
  "dominance_fortune": { "score": 0, "reading": "승부운이..." },
  "destiny_fortune": { "score": 0, "reading": "총운은..." },
  "daily_summary": "오늘의 운세 한줄 요약",
  "lucky_inning": 1
}

각 score는 0~10 사이 정수입니다.
lucky_inning은 1~9 사이, 이 투수가 가장 운이 좋은 이닝입니다.
```

---

## 5. 데이터 모델 설계

### 5-1. 핵심 테이블

```
[pitchers] 투수 마스터
─────────────────────────────
pitcher_id       PK, INTEGER
kbo_player_id    INTEGER UNIQUE, nullable (KBO 공식 playerId, 크롤러가 학습·write-back)
name             TEXT (한글명)
name_en          TEXT (영문명, 외국인 투수용)
team             TEXT (소속팀 약칭: LG, SSG, KT 등)
birth_date       DATE
chinese_zodiac   TEXT (자/축/인/묘/.../해)
zodiac_sign      TEXT (양자리/황소자리/... )
zodiac_element   TEXT (불/흙/바람/물)
blood_type       TEXT (A/B/O/AB)
profile_photo    TEXT (사진 경로 또는 URL)
created_at       DATETIME
updated_at       DATETIME


[face_scores] 관상 점수 (시즌 고정)
─────────────────────────────
face_score_id    PK, INTEGER
pitcher_id       FK → pitchers
season           INTEGER (2026)
command          INTEGER (0~10)
stuff            INTEGER (0~10)
composure        INTEGER (0~10)
dominance        INTEGER (0~10)
destiny          INTEGER (0~10)
command_detail   TEXT (관상 분석 코멘트)
stuff_detail     TEXT
composure_detail TEXT
dominance_detail TEXT
destiny_detail   TEXT
overall_impression TEXT
analyzed_at      DATETIME


[fortune_scores] 운세 점수 (매일 변동)
─────────────────────────────
fortune_id       PK, INTEGER
pitcher_id       FK → pitchers
game_date        DATE
command          INTEGER (0~10)
stuff            INTEGER (0~10)
composure        INTEGER (0~10)
dominance        INTEGER (0~10)
destiny          INTEGER (0~10)
command_reading  TEXT (운세 풀이 코멘트)
stuff_reading    TEXT
composure_reading TEXT
dominance_reading TEXT
destiny_reading  TEXT
daily_summary    TEXT
lucky_inning     INTEGER (1~9)
generated_at     DATETIME


[matchups] 당일 매치업
─────────────────────────────
matchup_id       PK, INTEGER
game_date        DATE
home_team        TEXT
away_team        TEXT
stadium          TEXT
home_pitcher_id  FK → pitchers
away_pitcher_id  FK → pitchers
chemistry_score  REAL (상성 점수)
home_total       INTEGER (홈 투수 총점)
away_total       INTEGER (원정 투수 총점)
predicted_winner TEXT
winner_comment   TEXT (승자 예측 한줄평)
actual_winner    TEXT (경기 후 업데이트, 적중률 추적용)
created_at       DATETIME


[daily_schedules] KBO 일정
─────────────────────────────
schedule_id         PK, INTEGER
game_date           DATE
home_team           TEXT
away_team           TEXT
stadium             TEXT
game_time           TIME
home_starter        TEXT (선발투수 한글명)
away_starter        TEXT (선발투수 한글명)
home_starter_kbo_id INTEGER, nullable (GetKboGameList T_PIT_P_ID)
away_starter_kbo_id INTEGER, nullable (GetKboGameList B_PIT_P_ID)
source_url          TEXT
crawled_at          DATETIME
```

### 5-2. KBO 10개 구단 코드

| 코드 | 팀명 | 연고지 |
|------|------|--------|
| LG | LG 트윈스 | 서울 (잠실) |
| SSG | SSG 랜더스 | 인천 |
| KT | KT 위즈 | 수원 |
| NC | NC 다이노스 | 창원 |
| DS | 두산 베어스 | 서울 (잠실) |
| KIA | KIA 타이거즈 | 광주 |
| LOT | 롯데 자이언츠 | 부산 |
| SAM | 삼성 라이온즈 | 대구 |
| HH | 한화 이글스 | 대전 |
| KW | 키움 히어로즈 | 서울 (고척) |

---

## 6. API 엔드포인트 설계

### 6-1. 클라이언트용 API

```
GET  /api/today
     → 오늘 전체 매치업 리스트 + 각 투수 점수 요약

GET  /api/matchup/{matchup_id}
     → 특정 매치업 상세 (5항목 점수, 관상 코멘트, 운세 풀이 전부)

GET  /api/pitcher/{pitcher_id}
     → 투수 프로필 + 관상 점수 + 오늘 운세

GET  /api/history?date={YYYY-MM-DD}
     → 과거 특정 날짜 매치업 조회

GET  /api/accuracy
     → 누적 예측 적중률 통계
```

### 6-2. 관리자/배치용 API

```
POST /admin/crawl-schedule
     → 당일 KBO 일정 + 선발투수 크롤링 트리거

POST /admin/analyze-face/{pitcher_id}
     → 특정 투수 관상 분석 실행

POST /admin/generate-fortune?date={YYYY-MM-DD}
     → 특정 날짜 전체 선발투수 운세 생성

POST /admin/calculate-matchups?date={YYYY-MM-DD}
     → 매치업 점수 계산 + 승자 판정

POST /admin/update-result/{matchup_id}
     → 경기 결과 입력 (적중률 추적)
```

---

## 7. 자동화 파이프라인

### 7-1. 일일 스케줄

```
[08:00] 크롤링 배치
        ├── KBO 공식 사이트에서 당일 경기 일정 수집
        └── 선발투수 발표 확인 (미발표 시 09시, 10시 재시도)

[10:30] 분석 배치 (선발 확정 후)
        ├── 신규 투수 있으면 → 프로필 사진 수집 → 관상 분석
        ├── 전 선발투수 → 운세 생성
        └── 상성 계산 → 매치업 점수 산출

[11:00] 콘텐츠 발행
        ├── 프론트엔드 캐시 갱신
        └── (확장) SNS 자동 포스팅

[경기 종료 후] 결과 배치
        ├── 경기 결과 크롤링
        ├── 예측 적중 여부 기록
        └── 누적 적중률 갱신
```

### 7-2. 크롤링 대상

**단일 소스 정책: `koreabaseball.com`.** 네이버 스포츠·스탯티즈·Daum 등 다른 호스트로의 fallback 경로는 만들지 않는다. 공식 사이트 안에서 직접 문제를 해결한다 (사용자 지침 2026-04-13). 유일한 out-of-band fallback 은 `httpx` 접근이 완전히 실패했을 때의 **Playwright headless** 이다. 투수 프로필 사진은 수집 소스 제한 없음 (CLAUDE.md §6, 2026-04-14 지침).

**주 엔드포인트:** `POST https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList` — form body `date=YYYYMMDD&leId=1&srId=0,1,3,4,5,7` (1군 정규시리즈 필터, `backend/app/services/crawler.py:266` 기준). 단일 호출로 경기 리스트 + 선발투수 playerId (`T_PIT_P_ID`/`B_PIT_P_ID`) + 한글 이름 + 팀 + 구장 + 경기 시작 시각 + 취소 플래그를 반환한다. 구버전 2-step (`GetTodayGames` + GameCenter HTML 스크레이프) 체인은 폐기.

**robots.txt 해석:** `/ws/` 는 blanket-disallow 이지만 KBO 공식 1군 일정 페이지 전체가 SPA 로 `/ws/` 에 의존한다. `services/crawler._robots_allows()` 는 `www.koreabaseball.com/ws/*` 에 한해 `True` 를 반환한다 (narrow carve-out; 다른 prefix/호스트는 정상 robots 적용). 결정 근거는 `PROGRESS.md §A-2` 세션 3 로그.

**호출 규칙:** UA `FACEMETRICS/0.1 (+research)`, `Referer: https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx`, `/ws/` POST 에는 `X-Requested-With: XMLHttpRequest` 추가. 호스트당 1 req/sec 상한.

**선수 매칭:** `GetKboGameList` 가 반환하는 playerId 를 `pitchers.kbo_player_id` 로 1차 매칭 → 미매칭 시 한글 이름 exact → rapidfuzz fuzzy (≥ 85) 순. id-first 매칭 성공 시 해당 pitcher 로우의 `kbo_player_id` 를 lazy write-back 한다 (같은 `(pitcher_id, game_date)` 원자 트랜잭션 안에서, 실패 시 함께 롤백). 알 수 없는 이름은 review queue 로 보내고 조용히 드롭하지 않는다.

**선발 미발표 대응:** 08:00 1차 크롤에서 선발이 비어 있으면 09:00, 10:00 에 재시도 후 포기.

---

## 8. 프론트엔드 화면 설계

### 8-1. 메인 화면 — 오늘의 매치업 리스트

- 상단 히어로(라이트 톤, `min-h-[60vh]` 세로 중앙정렬, 가로 `text-center`): `header_image.png` (로고 이미지) + `KBO · 2026 · SEASON` 스몰 캡션 + **FACEMETRICS** 워드마크(`#0A192F`, `text-[3.15rem] md:text-[4.2rem]`) + 서브카피 "관상과 운세로 보는 오늘의 승리투수" + 이탤릭 태그라인 "확률이 반반이면 관상이 답이다" (`#B8860B`)
- 날짜 pill 은 히어로에서 제거 — 바로 아래 `오늘의 매치업` 섹션 헤더에서 `04 / 13 · SUN` 형태로 노출
- 매치업 카드 리스트: 흰 카드(`bg-white ring-1 ring-black/5` + soft shadow) + `[ FACEMETRICS 상세 ⌄ ]` 인터랙티브 버튼. 버튼 클릭 시 **해당 카드가 그 자리에서 아코디언 확장** (별도 페이지로 이동 X). 이전 ShineBorder 회전 애니메이션은 제거됨.

```
╔═══════════════════════════════════════════╗
║                                           ║
║           [ header_image.png ]             ║
║             KBO · 2026 · SEASON            ║
║             FACEMETRICS                    ║
║    관상과 운세로 보는 오늘의 승리투수       ║
║       "확률이 반반이면 관상이 답이다"        ║
║                                           ║
╠═══════════════════════════════════════════╣
║  TODAY'S MATCHUPS                          ║
║                                           ║
║  ┌─ 18:30 · 잠실 ──────── 개막 9차전 ─┐   ║
║  │  ⦿ 엔스      VS      곽빈 ⦿       │   ║
║  │  LG · ♏전갈 · 🐉용  두산 · ♓물고기 · 🐍뱀│   ║
║  │  78점 ━━━━━━━━━━━━━━ 72점         │   ║
║  │  FACEMETRICS 예측 · ⭐ 엔스 승     │   ║
║  │  ╭──────────────────────────╮     │   ║
║  │  │ [ FACEMETRICS 상세 ⌄ ]    │     │   ║
║  │  ╰──────────────────────────╯     │   ║
║  └───────────────────────────────────┘   ║
║                                           ║
║  ┌─ 18:30 · 문학 ────────────────────┐   ║
║  │  ⦿ 김광현    VS    쿠에바스 ⦿     │   ║
║  │  85점 ━━━━━━━━━━━━━━ 81점         │   ║
║  │  FACEMETRICS 예측 · ⭐ 김광현 승   │   ║
║  │  [ FACEMETRICS 상세 ⌄ ]           │   ║
║  └───────────────────────────────────┘   ║
║                                           ║
║  ... (나머지 3경기)                       ║
╚═══════════════════════════════════════════╝
```

### 8-2. 매치업 상세 — 카드 내 아코디언 확장

**핵심 UX 원칙:** 매치업 상세는 **별도 페이지가 아니라 카드 자체가 그 자리에서 확장**된다. 사용자가 `[ FACEMETRICS 상세 ⌄ ]` 버튼을 누르면 fade-up 애니메이션과 함께 카드 하단이 펼쳐지고, 스크롤 위치는 카드 상단으로 부드럽게 맞춰진다. 이는 "스크롤해서 아래로 내려가는 경험"이 아니라 "해당 매치업에 집중해서 확장하는 경험"을 주기 위함이다.

#### 확장 영역 구성 (위→아래)

1. **Five Elements 펜타곤 레이더 차트** (SVG, FIFA 선수카드 스타일)
   - 5축: 제구력 / 구위 / 멘탈 / 지배력 / 운명력
   - 두 투수 폴리곤이 **하나의 오각형에 겹쳐서** 그려짐 (홈 = coral `#F26B4E` 반투명, 원정 = mint `#059669` 반투명)
   - 각 axis 라벨 하단에 두 선수 점수 `16 / 14` 형식 병기 (홈 coral, 원정 mint)
   - 하단 범례: 🟧 엔스 78 │ 🟩 곽빈 72
2. **5항목 상세 블록** — 각 항목마다:
   - 헤더: `아이콘 · 항목명 (N, 엔스) (N, 곽빈)` 포맷으로 두 선수 총점 병기
   - 양방향 점수 바 (좌: coral, 우: mint, spring fill 애니)
   - 2컬럼 설명 카드:
     - `🙂 관상 N : <관상 근거 1줄>`
     - `✨ 운세 N : <운세 근거 1줄>`
3. **상성(Chemistry) 분석 박스** — 띠 궁합 + 원소 궁합 각각 한 줄 (coral tonal 카드, `bg-coral-light` + `border-coral/20`)
4. **승자 카드** — coral 솔리드 배경(`#F26B4E`) + `-45deg` 화이트 대각선 스트라이프 오버레이 패턴, 흰색 투수 이름 + 총점 + 한줄 코멘트 + 럭키이닝

```
╔═ 18:30 · 잠실 ══════════════ 개막 9차전 ═╗
║  ⦿ 엔스         VS         곽빈 ⦿        ║
║  LG · ♏전갈 · 🐉용  두산 · ♓물고기 · 🐍뱀 ║
║  78점 ━━━━━━━━━━━━━━ 72점                ║
║  FACEMETRICS 예측 · ⭐ 엔스 승            ║
║  ╭────────────────────────────────╮      ║
║  │ [ FACEMETRICS 상세 ⌃ ]  (열림) │      ║
║  ╰────────────────────────────────╯      ║
╠═══════════════════════════════════════════╣
║                                           ║
║           ─── FIVE ELEMENTS ───            ║
║                                           ║
║                 제구력                     ║
║                 16 / 14                    ║
║                  ╱╲                        ║
║              ╱       ╲                     ║
║      운명력           구위                 ║
║      12/15  ╲ ◆◇ ╱    17/12               ║
║              ╲ ╳ ╱      ← coral/mint 폴리곤 겹침 ║
║              ╱ ╳ ╲                         ║
║      지배력  ╱    ╲   멘탈                 ║
║      18/15 ╱      ╲  15/16                 ║
║                                           ║
║     🟧 엔스 78   │   🟩 곽빈 72            ║
║                                           ║
╠═══════════════════════════════════════════╣
║                                           ║
║  🎯 제구력 · Command   (16, 엔스)(14, 곽빈)║
║  엔 ████████░░ 16  │  14 ░░████████ 곽    ║
║  ┌─ 엔스 ──────────┐ ┌─ 곽빈 ──────────┐  ║
║  │🙂 관상 9 : 흔들림│ │🙂 관상 8 : 눈-눈│  ║
║  │ 없는 눈매가 코너│ │ 썹 간격이 적당해│  ║
║  │ 를 찌른다       │ │ 여유 있는 시야 │  ║
║  │✨ 운세 7 : 전갈 │ │✨ 운세 6 : 물고│  ║
║  │ 자리 집중운 상위│ │ 기자리 정밀운  │  ║
║  └─────────────────┘ └─────────────────┘  ║
║                                           ║
║  💥 구위 · Stuff       (17, 엔스)(12, 곽빈)║
║  (동일 포맷 — 관상/운세 설명 각 1줄)       ║
║                                           ║
║  🧘 멘탈 · Composure   (15, 엔스)(16, 곽빈)║
║  (동일 포맷)                               ║
║                                           ║
║  👑 지배력 · Dominance (18, 엔스)(15, 곽빈)║
║  (동일 포맷)                               ║
║                                           ║
║  ✨ 운명력 · Destiny   (12, 엔스)(15, 곽빈)║
║  (동일 포맷)                               ║
║                                           ║
╠═══════════════════════════════════════════╣
║  ⚔️ 상성 분석 · Chemistry                  ║
║  띠: 용띠 vs 뱀띠 — 중립 관계 (+0)         ║
║  원소: 전갈(물) vs 물고기(물) — 동질 +1   ║
║  "순수 실력과 기운의 대결. 물 원소가       ║
║   곽빈에게 미세한 손을 들어준다."          ║
╠═══════════════════════════════════════════╣
║                                           ║
║         오늘의 FACEMETRICS 승자            ║
║  ┌──────────────────────────────────┐    ║
║  │          ⭐ 엔스 ⭐                │    ║
║  │          78  vs  72                │    ║
║  │  "기세의 눈썹이 마운드를 지배한다" │    ║
║  │                                   │    ║
║  │  🎰 럭키이닝: 엔스 5회 / 곽빈 3회  │    ║
║  └──────────────────────────────────┘    ║
║                                           ║
╚═══════════════════════════════════════════╝
```

#### 설명 포맷 규칙

모든 평가 근거는 다음 두 줄 포맷을 **반드시** 따른다:

```
🙂 관상 N : <관상 점수 N의 근거 1줄>
✨ 운세 N : <운세 점수 N의 근거 1줄>
```

- `🙂` (노란 웃는 얼굴) = 관상 설명 전용 아이콘
- `✨` = 운세 설명 전용 아이콘
- N은 0~10 정수, 항목 총점(20) = 관상 + 운세
- 근거 문장은 **한 줄 안에** 들어가도록 Claude API 프롬프트에서 길이 제한

### 8-3. 투수 프로필 화면

```
┌─────────────────────────────────────────┐
│  ← 뒤로                                 │
├─────────────────────────────────────────┤
│           [큰 프로필 사진]               │
│            임찬규 (LG)                   │
│                                         │
│  생년월일: 1995.07.02                    │
│  별자리: ♋ 게자리 (물)                   │
│  띠: 🐷 돼지띠                           │
│  혈액형: A형                             │
├─────────────────────────────────────────┤
│  📊 관상 레이더 차트                      │
│                                         │
│         제구력(8)                        │
│           ╱╲                            │
│    운명력(6) ──── 구위(7)               │
│           ╲╱                            │
│    지배력(9) ──── 멘탈(7)               │
│                                         │
│  "날카로운 눈매와 강한 눈썹이 마운드     │
│   위의 지배자 기질을 보여준다."          │
├─────────────────────────────────────────┤
│  📅 최근 운세 추이                       │
│                                         │
│  4/13  ★★★★☆  78점                    │
│  4/07  ★★★☆☆  65점                    │
│  4/01  ★★★★★  88점  ← 시즌 최고      │
│  3/26  ★★★☆☆  71점                    │
├─────────────────────────────────────────┤
│  🎯 예측 적중 기록                       │
│  적중: 3회 / 전체: 5회 (60%)            │
└─────────────────────────────────────────┘
```

---

## 9. 기술 스택 상세

### 9-1. 기술 선정표

| 영역 | 기술 | 선정 이유 |
|------|------|-----------|
| **Frontend 프레임워크** | Next.js 14 App Router + TypeScript | `"use client"` 호환, SSR 프리페치로 로딩 플래시 제거, Vercel 최적화 |
| **스타일링** | Tailwind CSS + shadcn/ui (`cn()` 유틸) | 라이트 SaaS 팔레트(coral/mint + ink 3단), 커스텀 키 `coral`/`mint`/`ink` 확장 |
| **애니메이션** | framer-motion + tailwindcss-animate | stagger 등장, spring 바 채움, count-up, fade-up/radar-in 키프레임 |
| **아이콘** | lucide-react | Sparkles, TrendingUp 등 라인 아이콘 (이전 dicons 의존 제거) |
| **폰트** | Pretendard Variable (단일 패밀리) | 국문·영문 모두 Pretendard로 통일. FACEMETRICS 워드마크는 `text-[4.2rem] font-bold tracking-tight` + `#0A192F` |
| **차트** | Recharts (라이트 테마 커스텀) | 5각형 레이더 차트(FIFA 스타일 오버레이, coral/mint 반투명) |
| **상태/페칭** | TanStack Query (SSR hydrate) | `/api/today` 캐싱, 매치업 상세 프리페치 |
| **Backend** | FastAPI (Python 3.11+) | 비동기 처리, 자동 API 문서, 타입 힌트 |
| **AI 엔진** | Anthropic Claude API | Vision(관상) + Text(운세) 통합 |
| **DB** | SQLite (`aiosqlite`, 개발) → PostgreSQL (`asyncpg`, 운영) | 초기 빠른 개발, 이후 확장성. Alembic env 가 두 드라이버 모두 인식 |
| **ORM** | SQLAlchemy 2.0 (async) | Python 표준 ORM, `Mapped[...]` 타입 힌트, `AsyncSession` 필수 |
| **Migrations** | Alembic 1.13.3 | 단일 진실 원천. `scripts/init_db.py` 가 `alembic upgrade head` 로 위임. `Base.metadata.create_all` 금지 |
| **크롤러** | httpx + rapidfuzz | `httpx.AsyncClient` 비동기 HTTP, rapidfuzz 로 한글 이름 fuzzy 매칭(≥ 85) |
| **스케줄러** | APScheduler (KST) | `app/scheduler.py` 내 5 잡 (08:00/09:00/10:00/10:30/11:00 KST). `lifespan` 에서 기동 |
| **컨테이너화** | Docker + docker-compose (로컬 smoke) | `backend/Dockerfile` (python:3.12-slim + tini, non-root uid 1000), `frontend/Dockerfile` (node 20-alpine 멀티스테이지, Next `output: 'standalone'`), `docker-compose.yml` 에 sqlite bind-mount |
| **배포 (FE)** | Vercel | Next.js 최적 배포, OG route Edge Runtime |
| **배포 (BE)** | Railway / Fly.io | FastAPI + Postgres. APScheduler 싱글톤 보장 필요 (replicas ≥ 2 주의) |
| **CI/CD** | GitHub Actions | `.github/workflows/ci.yml` — backend(`pytest` + import smoke + alembic upgrade), frontend(`type-check` + `build`) |

### 9-1-1. 디자인 시스템 (FACEMETRICS 톤앤매너)

전체 톤은 **라이트 SaaS (Notion/Linear/Harmonic 계열)**. 루트 배경은 오프화이트, 카드는 순백, 강조는 coral 단일 액센트 + mint 서브 액센트로 구성한다. 이전 버전의 obsidian/gold/crimson/jade 다크 오리엔탈 톤은 전면 폐기.

| 토큰 | 값 | 용도 |
|------|-----|------|
| `bg` | `#f7f7f7` | 루트 배경 (오프화이트) |
| `white` | `#ffffff` | 카드 배경 |
| `coral` | `#F26B4E` / light `#FEF3F0` / dark `#C54A30` | 홈팀, 제구력·지배력 바, 프라이머리 액센트, 우승 카드 솔리드 배경 |
| `mint` | `#059669` / light `#D1FAE5` / dark `#065F46` | 원정팀, 멘탈·구위 바, 세컨더리 액센트 |
| `ink` | `#111827` / muted `#6B7280` / faint `#9CA3AF` | 본문·보조·비활성 텍스트 3단 |
| `#0A192F` | 워드마크 | `FACEMETRICS` 로고 전용 색 (ink DEFAULT 보다 딥블루 계열) |
| `#B8860B` | 태그라인 | `"확률이 반반이면 관상이 답이다"` 이탤릭 전용 색 (다크 골드) |
| 페이스텔 태그 | `bg-gray-100/text-gray-700`, `bg-orange-100/text-orange-800`, `bg-blue-100/text-blue-800`, `bg-emerald-100/text-emerald-800` | 경기 시간/구장·경기 성격 칩 |

- **카드 스타일**: `rounded-2xl bg-white ring-1 ring-black/5` + soft shadow (`0 1px 2px / 0 8px 24px rgba(17,24,39,0.04~0.05)`). ShineBorder 회전 애니메이션은 전 구역에서 제거.
- **우승자 카드**: coral 솔리드(`#F26B4E`) + `repeating-linear-gradient(-45deg, transparent 10px, rgba(255,255,255,0.35) 10px 11px)` 화이트 대각선 스트라이프 오버레이. 흰색 타이포.
- **Aurora 히어로 제거**: 히어로는 `min-h-[60vh] flex items-center justify-center` 중앙정렬 구조. `header_image.png` → subtitle → 워드마크 → 서브카피 → 태그라인 수직 스택. 배경은 플랫 `#f7f7f7`.
- **레이더 차트**: 링 `rgba(17,24,39,0.08)`, 외곽링 `rgba(17,24,39,0.18)`, 홈 폴리곤 coral 22% 투명, 원정 폴리곤 mint 18% 투명, 노드 stroke 흰색.
- **관상 이모지**: 🙂 (노란 웃는 얼굴) / **운세 이모지**: ✨

### 9-2. 디렉토리 구조

```
facemetrics/
├── frontend/                          # Next.js 14 App Router (src/ layout)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                   # 라이트 테마, Pretendard Variable
│   │   │   ├── page.tsx                     # "/" TodayMatchups (히어로 + 아코디언)
│   │   │   ├── globals.css                  # bar-fill, fade-up, radar-in 키프레임
│   │   │   ├── history/page.tsx             # 과거 기록
│   │   │   ├── pitcher/[id]/page.tsx        # 투수 프로필
│   │   │   └── api/og/matchup/[id]/route.tsx # @vercel/og Edge, 1200×630 공유 카드
│   │   ├── components/                      # 플랫 구조 (subfolder 없음)
│   │   │   ├── MatchupCard.tsx              # 아코디언 카드 (흰 카드 + ring + soft shadow)
│   │   │   ├── RadarChart.tsx               # SVG 5축 레이더 (coral/mint 오버레이)
│   │   │   ├── ScoreBar.tsx
│   │   │   ├── AxisDetail.tsx               # 5항목 설명 블록 (🙂/✨)
│   │   │   ├── ShareButton.tsx              # OG route 링크 + 다운로드
│   │   │   └── Footer.tsx                   # 면책 고지 푸터
│   │   ├── lib/
│   │   │   └── api.ts                       # FastAPI 클라이언트 + USE_MOCK 플래그
│   │   └── types/
│   │       └── index.ts                     # MatchupSummary, PitcherDetail 등
│   ├── preview/draft.html                   # 디자인 톤 소스 오브 트루스
│   ├── public/                              # 정적 에셋 (header_image 등)
│   ├── tailwind.config.ts                   # coral/mint/ink 토큰 + 키프레임
│   ├── next.config.mjs                      # output: 'standalone'
│   ├── Dockerfile                           # node 20-alpine 멀티스테이지
│   └── package.json
│
├── backend/                           # FastAPI 앱
│   ├── app/
│   │   ├── main.py                          # FastAPI + lifespan (스케줄러 기동)
│   │   ├── config.py                        # pydantic-settings (.env)
│   │   ├── db.py                            # AsyncSession 팩토리
│   │   ├── scheduler.py                     # APScheduler 5 잡 (KST)
│   │   ├── models/                          # SQLAlchemy Mapped[...] 모델
│   │   │   ├── pitcher.py
│   │   │   ├── face_score.py
│   │   │   ├── fortune_score.py
│   │   │   ├── matchup.py
│   │   │   └── daily_schedule.py
│   │   ├── schemas/                         # Pydantic v2
│   │   │   ├── ai.py                        # Claude 응답 스키마
│   │   │   ├── crawler.py                   # GetKboGameList 파서 스키마
│   │   │   └── response.py                  # 라우터 응답 스키마
│   │   ├── routers/
│   │   │   ├── today.py                     # GET /api/today
│   │   │   ├── matchup.py                   # GET /api/matchup/{id}
│   │   │   ├── pitcher.py                   # GET /api/pitcher/{id}
│   │   │   ├── history.py                   # GET /api/history
│   │   │   ├── accuracy.py                  # GET /api/accuracy
│   │   │   ├── admin.py                     # POST /admin/*
│   │   │   └── _helpers.py                  # pitcher_summary() 공용
│   │   ├── services/
│   │   │   ├── crawler.py                   # koreabaseball.com /ws/ 전용 + 이름 매처
│   │   │   ├── face_analyzer.py             # Claude Vision + 캐시 write-through
│   │   │   ├── fortune_generator.py         # Claude Text + 결정론 캐시
│   │   │   ├── chemistry_calculator.py      # 띠·별자리 룰 기반 상성
│   │   │   ├── scoring_engine.py            # 5축 합산 + predicted_winner
│   │   │   └── hash_fallback.py             # Claude 실패 시 해시 스코어러
│   │   └── prompts/
│   │       ├── face_analysis.txt
│   │       └── fortune_reading.txt
│   ├── alembic/                             # 마이그레이션 (단일 진실 원천)
│   │   ├── env.py                           # async aiosqlite/asyncpg 모두 지원
│   │   └── versions/
│   │       ├── 0001_initial_schema.py       # 5 테이블 초기 생성
│   │       └── 0002_add_kbo_player_id.py    # A-5 세션 10
│   ├── alembic.ini
│   ├── tests/                               # pytest (async)
│   │   ├── conftest.py                      # 임시 sqlite DATABASE_URL 주입
│   │   ├── test_analyze_rollback.py         # 원자 트랜잭션 회귀 가드
│   │   └── test_kbo_id_matcher.py           # id-first + lazy write-back
│   ├── Dockerfile                           # python:3.12-slim + tini (non-root uid 1000)
│   └── requirements.txt
│
├── data/                              # 정적 데이터 + sqlite bind-mount 대상
│   ├── pitchers_2026.json
│   ├── zodiac_compatibility.json
│   ├── constellation_elements.json
│   └── facemetrics.db                       # (dev, git-ignored)
│
├── scripts/                           # 유틸리티 (독립 실행)
│   ├── init_db.py                           # alembic upgrade head 위임
│   ├── seed_pitchers.py                     # 투수 10명 시딩
│   ├── verify_ai_pipeline.py                # 실 Claude 파이프라인 캐시 미스/히트 검증
│   ├── crawl_today.py                       # GetKboGameList 단발 크롤
│   └── crawl_pitcher_images.py              # 프로필 사진 수확
│
├── .claude/                           # 에이전트 정의 + 훅
│   ├── agents/                              # react-ui-dev, fastapi-backend-dev 등
│   └── hooks/code-reviewer-gate.sh          # stop hook: 자동 code-reviewer
├── .github/workflows/ci.yml           # backend pytest + frontend build
├── docker-compose.yml                 # backend:8000 + frontend:3000 (로컬 smoke)
├── .dockerignore
├── CLAUDE.md                          # 에이전트용 실행 가이드
├── PROGRESS.md                        # 세션 저널 (ARCHIVE.md 로 이동 예정)
├── ARCHIVE.md                         # 완료 Phase 세부 로그
├── KBO_CRAWLING_GUIDE.md              # /ws/ 엔드포인트 레퍼런스
└── README.md                          # 본 스펙
```

---

## 10. 확장 가능성

### 10-1. 콘텐츠 확장

| 확장 기능 | 설명 |
|-----------|------|
| **타자 운세** | 당일 선발 라인업의 1~9번 타자 운세 (타격운, 출루운) |
| **팀 총운** | 팀 전체의 당일 기운 합산 |
| **주간 운세 달력** | 투수 로테이션 + 주간 운세 미리보기 |
| **관운상 랭킹** | 이번 주/이번 달 관운상 최강 투수 랭킹 |
| **시즌 MVP** | 관상+운세 누적 최고점 투수 "관운상 MVP" |

### 10-2. 커뮤니티 확장

| 확장 기능 | 설명 |
|-----------|------|
| **적중률 트래킹** | "관운상이 진짜 맞추나?" 일별/월별 적중률 공개 |
| **팬 투표** | 관운상 vs 팬 예측 vs 실제 결과 3자 비교 |
| **공유 카드** | 매치업 대결 카드 이미지 자동 생성 → SNS 공유 |
| **알림 서비스** | 내 팀 선발투수 운세 당일 푸시 알림 |

---

## 11. 리스크 및 대응

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| 선발투수 당일 변경 | 이미 생성한 콘텐츠 무효화 | 변경 감지 시 자동 재생성 + "선발 변경" 알림 |
| Claude API 장애 | 운세/관상 생성 불가 | 해시 기반 폴백 점수 + 이전 데이터 재활용 |
| 크롤링 차단 | 일정/선발 데이터 수집 불가 | `httpx` → Playwright headless fallback + 수동 입력 백업 (단일 소스 `koreabaseball.com` 정책은 유지, §7-2 참조) |
| 투수 사진 없음 | 관상 분석 불가 | 모든 가용 소스에서 수집 (KBO 공식/뉴스/SNS/검색), 실루엣 플레이스홀더 금지 (CLAUDE.md §6) |
| "도박 조장" 오해 | 법적/이미지 리스크 | 모든 화면에 "엔터테인먼트 목적" 면책 고지. 배팅 연동 절대 없음. |

---

## 12. 개발 로드맵

### Phase 1: 기반 구축 (1주)

- [ ] DB 스키마 생성 및 마이그레이션
- [ ] KBO 10개 구단 투수 마스터 데이터 구축 (이름, 생년월일, 띠, 별자리)
- [ ] 투수 프로필 사진 수집
- [ ] 띠 궁합표, 별자리 원소 매핑 정적 데이터 구축

### Phase 2: AI 엔진 (1주)

- [ ] Claude Vision 관상 분석 프롬프트 설계 및 테스트
- [ ] Claude Text 운세 생성 프롬프트 설계 및 테스트
- [ ] 프롬프트 튜닝 (점수 분포가 한쪽에 쏠리지 않도록 캘리브레이션)
- [ ] 상성 계산 모듈 구현
- [ ] 종합 스코어링 엔진 구현

### Phase 3: 크롤러 + 배치 (1주)

- [ ] KBO 공식 사이트 일정 크롤러 구현
- [ ] 선발투수 매칭 로직 (크롤링 이름 → DB pitcher_id 매핑)
- [ ] 일일 자동화 파이프라인 구축 (APScheduler)
- [ ] 경기 결과 크롤러 (적중률 추적용)

### Phase 4: 프론트엔드 (1주)

- [ ] Next.js 14 App Router 초기화 + Tailwind/shadcn 세팅
- [ ] 라이트 팔레트(coral/mint/ink)·폰트(Pretendard Variable 단일)·`globals.css` (bar-fill/fade-up/radar-in/stripes 키프레임)
- [ ] `NumberTicker` primitive 작성 (shine-border/timeline/aurora-background 등 다크 톤 스니펫은 폐기)
- [ ] FACEMETRICS 메인 히어로: `min-h-[60vh]` 세로 중앙정렬 + `header_image.png` + `KBO · 2026 · SEASON` 캡션 + 워드마크(`#0A192F`) + "관상과 운세로 보는 오늘의 승리투수" + 태그라인 "확률이 반반이면 관상이 답이다" (`#B8860B`)
- [ ] `MatchupCard` — 흰 카드 + ring + soft shadow, framer stagger 등장 + `[ FACEMETRICS 상세 ⌄ ]` 아코디언 토글
- [ ] `RadarPentagon` — Recharts 라이트 커스텀 5각형 (holding coral/mint 반투명 오버레이, 축 라벨 아래 점수 표기)
- [ ] `CategoryBlock` — 5항목 설명 (`(N, 홈투수)(N, 원정투수)` 헤더 + `🙂 관상 N : 설명` / `✨ 운세 N : 설명` 2줄)
- [ ] `ChemistryNote` — 상성 박스 (coral-light 카드, 띠/별자리 코멘트)
- [ ] `WinnerCard` — coral 솔리드 + `-45deg` 화이트 대각선 스트라이프 오버레이 패턴
- [ ] 투수 프로필 `RadarChart` + `FortuneTimeline` (Timeline 재사용)
- [ ] `lib/api.ts` + TanStack Query SSR hydrate (`/api/today` 프리페치)
- [ ] 반응형 (모바일 1열 · 태블릿 2열 · 데스크톱 카드 리스트 + 스포트라이트)
- [ ] 면책 고지 footer (§부록)

### Phase 5: 마감 + 런칭 (3~5일)

- [ ] 통합 테스트
- [ ] 배포 (Vercel + Railway)
- [ ] 면책 고지문 삽입
- [ ] 시즌 개막일 맞춰 소프트 런칭
- [ ] 커뮤니티 공유용 카드 이미지 생성 기능

---

## 부록: 면책 고지문 (안)

> ⚠️ **본 서비스는 100% 엔터테인먼트 목적으로 제작되었습니다.**
>
> 관상 및 운세 분석은 과학적 근거가 없으며, 실제 경기 결과를 예측하는 용도로 사용할 수 없습니다. 스포츠 도박 또는 베팅의 참고 자료로 절대 활용하지 마십시오. 본 서비스의 예측은 재미 요소일 뿐이며, 어떠한 경기 결과에 대해서도 책임지지 않습니다.

---

*끝.*
