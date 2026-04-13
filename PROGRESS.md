# FACEMETRICS — Implementation Progress

새 세션에서 이어서 작업할 수 있게 Phase 단위로 완료 내역을 기록한다.
각 항목은 **완료일 / 생성·수정 파일 / 검증 방법 / 새 세션을 위한 메모** 형식.

- **Spec source of truth:** `README.md` + `CLAUDE.md`
- **현재 단계:** Phase 1 ✅ → Phase 2 ✅ → Phase 3 sub-task 1 (크롤러) ✅ → 다음은 Phase 3 sub-task 2 (DB write + APScheduler)
- **DB URL (dev):** `sqlite+aiosqlite:///data/facemetrics.db` (repo root 기준)
- **자동화:** Stop hook (`.claude/hooks/code-reviewer-gate.sh`) 등록 — 응답이 끝날 때 untracked/modified 코드(.py/.ts/.tsx/.js/.jsx) 해시가 바뀌면 자동으로 code-reviewer 서브에이전트 호출 강제. 마커 `.claude/.last-reviewed-hash` 로 루프 방지.

---

## ✅ Phase 1 — 기반 구축 (완료: 2026-04-13)

Phase 1 의 목적: FastAPI 백엔드 스켈레톤 + 5개 핵심 테이블 + 시즌 마스터 시드 데이터까지 세팅해서, Phase 2 의 AI 엔진이 `pitchers` 테이블을 소비할 수 있는 상태로 만든다.

### 1-1. FastAPI 스캐폴딩 ✅

**생성:**
- `backend/requirements.txt` — fastapi, uvicorn, sqlalchemy[asyncio], aiosqlite, asyncpg, pydantic-settings, httpx, beautifulsoup4, rapidfuzz, apscheduler, anthropic 등
- `backend/.env.example` — `DATABASE_URL`, `ANTHROPIC_API_KEY`, scheduler KST 설정 템플릿 (절대 `.env` 를 커밋하지 말 것)
- `backend/app/__init__.py`
- `backend/app/config.py` — `pydantic-settings` 기반 `Settings`, `get_settings()` 캐시, `is_sqlite` 헬퍼
- `backend/app/main.py` — `create_app()` 팩토리, CORS, `GET /health`

**검증:** (아직 uvicorn 기동은 안 해봤음 — Phase 2 에서 라우터 붙이면서 같이 검증)

### 1-2. 비동기 DB 레이어 ✅

**생성:**
- `backend/app/db.py` — `Base` (DeclarativeBase), `engine` (create_async_engine), `SessionLocal` (async_sessionmaker), `get_session()` 의존성. SQLite 경로면 상위 디렉토리 자동 생성.

### 1-3. SQLAlchemy 모델 5종 ✅

README §5-1 스키마 그대로.

**생성:**
- `backend/app/models/__init__.py` — 전체 export
- `backend/app/models/pitcher.py` — `pitchers`
- `backend/app/models/face_score.py` — `face_scores` (UNIQUE `pitcher_id+season` — 시즌 고정 불변 조건 강제)
- `backend/app/models/fortune_score.py` — `fortune_scores` (UNIQUE `pitcher_id+game_date` — 결정론적 캐시 강제)
- `backend/app/models/matchup.py` — `matchups`
- `backend/app/models/daily_schedule.py` — `daily_schedules`

**⚠️ 중요 — Python 3.14 + SQLAlchemy 호환 이슈 메모:**
- 로컬 Python 은 **3.14.3**. SQLAlchemy **2.0.36** 에서는 `Mapped[str | None]` + `from __future__ import annotations` 조합이 `de_stringify_union_elements` 에서 터짐 (`TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'`).
- **해결:** SQLAlchemy 를 **2.0.49** 로 업그레이드 + 모든 모델에서 `from __future__ import annotations` 제거 + `str | None` → `Optional[str]` 로 통일. requirements.txt 의 핀 2.0.36 은 Phase 2 합류 전에 2.0.49 이상으로 올려야 한다 (현재 로컬은 2.0.49 설치돼 있음).
- 새 세션에서 `pip install -r backend/requirements.txt` 하기 전에 `requirements.txt` 의 `sqlalchemy[asyncio]==2.0.36` 을 `>=2.0.49,<2.1` 로 바꿔두는 걸 추천.

### 1-4. `scripts/init_db.py` ✅

**생성:**
- `scripts/init_db.py` — `Base.metadata.create_all` 을 async 로 실행. Alembic 없이 dev SQLite 부트스트랩 용.

**검증:**
```
$ python scripts/init_db.py
[init_db] tables created on sqlite+aiosqlite:///C:/Users/YANG/Lucky_pocky/data/facemetrics.db
[init_db] registered tables: ['daily_schedules', 'face_scores', 'fortune_scores', 'matchups', 'pitchers']
```
→ 5개 테이블 전부 생성 확인.

### 1-5. `data/zodiac_compatibility.json` ✅

README §2-3 의 삼합/육합/원진/충 표를 정적 JSON 으로. 기본 점수 2.0 + 보정 + `[0, 4]` clamp 메타데이터 포함. Phase 2 `chemistry_calculator` 가 이 파일을 로드해서 룰 매칭.

### 1-6. `data/constellation_elements.json` ✅

12별자리 → 4원소(불/흙/바람/물) 매핑 + 서양 점성술 날짜 범위(MM-DD). `element_compat` 에 동질(+1)/상생(+1.5)/상극(-1) 룰 포함. `seed_pitchers.py` 가 이 파일로 `zodiac_sign` / `zodiac_element` 를 산출.

### 1-7. `data/pitchers_2026.json` ✅

현재 10명 수록 (manifest 순서):
| # | 이름 | 팀 | 생년월일 | 계산된 띠/별자리 |
|---|------|----|----------|------------------|
| 1 | 원태인 | SAM | 2000-04-06 | 진/양자리(불) |
| 2 | 곽빈 | DS | 1999-05-28 | 묘/쌍둥이자리(바람) |
| 3 | 네일 (James Naile) | KIA | 1993-05-23 | 유/쌍둥이자리(바람) |
| 4 | 카스타노 (Daniel Castano) | SSG | 1994-09-17 | 술/처녀자리(흙) |
| 5 | 손주영 | LG | 1998-06-09 | 인/쌍둥이자리(바람) |
| 6 | 박세웅 | LOT | 1995-11-30 | 해/사수자리(불) |
| 7 | 임찬규 | LG | 1992-11-20 | 신/전갈자리(물) |
| 8 | 문동주 | HH | 2003-12-23 | 미/염소자리(흙) |
| 9 | 양현종 | KIA | 1988-03-01 | 진/물고기자리(물) |
| 10 | 하트 (Kyle Hart) | NC | 1992-11-23 | 신/사수자리(불) |

**⚠️ teams_pending: `KT`, `KW`** — 이 두 팀의 2026 선발 로테이션은 아직 시드에 없다. Phase 3 크롤러가 실제 일정/선발을 잡으면서 채우거나, 사용자가 JSON 에 직접 추가하면 `seed_pitchers.py` 재실행으로 upsert 됨.

**⚠️ 생년월일 정확도:** 한국 투수는 공개 프로필 기준 best-effort, 외국인(네일/카스타노/하트)은 근사치. 띠·별자리가 치명적으로 어긋나면 점수 계산이 틀어지므로 런칭 전에 verify 필요.

### 1-8. `scripts/seed_pitchers.py` ✅

**로직:**
1. `pitchers_2026.json` 로드
2. `constellation_elements.json` 의 signs 리스트로 `zodiac_sign_for()` 실행 (염소자리 12/22 → 01/19 year-wrap 처리됨)
3. `chinese_zodiac_for()` = `(year - 1900) % 12` 인덱스 (1900 = 자)
4. `data/pitcher_images/manifest.json` 의 `success` 배열에서 `manifest_index` 로 `profile_photo` 해결 (KBO 소스 우선, 없으면 namuwiki 폴백)
5. `(name, team)` 기준 upsert — 있으면 UPDATE, 없으면 INSERT
6. `engine.begin()` 안에서 `create_all` 도 한 번 돌려서 DB 가 비어 있어도 안전하게 돌아감

**검증:**
```
$ python scripts/seed_pitchers.py
[seed_pitchers] season=2026 inserted=10 updated=0
[seed_pitchers] db url: sqlite+aiosqlite:///C:/Users/YANG/Lucky_pocky/data/facemetrics.db
[seed_pitchers] photos wired from manifest: 10
```

스팟체크 (utf-8 stdout 기준):
```
 1  원태인   SAM  2000-04-06  띠=진  양자리(불)
 2  곽빈    DS   1999-05-28  띠=묘  쌍둥이자리(바람)
 ...
 8  문동주   HH   2003-12-23  띠=미  염소자리(흙)
 9  양현종   KIA  1988-03-01  띠=진  물고기자리(물)
10  하트    NC   1992-11-23  띠=신  사수자리(불)
```
→ 2000/1988 = 용띠(진), 1992 = 원숭이띠(신), 1995 = 돼지띠(해), 2003 = 양띠(미) 모두 검증 완료. Year-wrap(염소자리) 도 정상.

### 1-9. 스모크 테스트 ✅

`init_db.py` + `seed_pitchers.py` 연속 실행 → `data/facemetrics.db` 에 pitchers 10 row, 모든 프로필 사진 연결 완료. `.gitignore` 에 `*.db` 있어서 DB 파일은 커밋되지 않음.

---

## 🔜 Phase 2 시작 전 체크리스트 (새 세션용)

1. **Python 환경 확인**
   - 로컬 Python 은 3.14.3. 가상환경 쓸 거면 `python -m venv .venv && .venv/Scripts/activate`.
   - SQLAlchemy 는 반드시 **≥ 2.0.49** (requirements.txt 핀은 아직 2.0.36 이므로 먼저 수정할 것).
2. **설치**
   - `pip install -r backend/requirements.txt`
   - 처음이면 `.env.example` → `.env` 복사 후 `ANTHROPIC_API_KEY` 채우기.
3. **DB 부팅**
   - `python scripts/init_db.py`
   - `python scripts/seed_pitchers.py`
4. **서버 부팅 (선택)**
   - `cd backend && uvicorn app.main:app --reload` → `GET http://localhost:8000/health` 가 `{"status":"ok"}` 반환하는지만 확인.

---

## ✅ Phase 2 — AI 엔진 (완료: 2026-04-13)

Phase 2 의 목적: Phase 1 의 DB 스키마 위에 **관상/운세 점수 산출 + 상성 계산 + 매치업 스코어링** 파이프라인을 얹어서, Phase 3 의 크롤러/스케줄러가 `score_matchup()` 한 번만 호출하면 matchups 행을 채울 수 있는 상태로 만든다.

불변 조건 (CLAUDE.md §2):
- 관상은 시즌 고정 — `(pitcher_id, season)` 캐시 히트 시 Claude 미호출.
- 운세는 `(pitcher_id, game_date)` 결정론적 캐시 — 두 번째 호출은 절대 API 를 타지 않는다.
- 상성은 룰 기반, 운명력 축에만 적용, `[0, 4]` clamp.
- Claude API 실패 시 500 금지 — 해시 폴백으로 내려준다.

### 2-1. 프롬프트 & 스키마 ✅

**생성:**
- `backend/app/prompts/face_analysis.txt` — README §4-1 그대로. `===SYSTEM===` / `===USER===` 구분자. 시스템 블록에 변수 X → prompt caching 안정.
- `backend/app/prompts/fortune_reading.txt` — README §4-2. `{pitcher_name} {birth_date} {zodiac_sign} {chinese_zodiac} {today_date} {opponent_team} {stadium}` 자리표시자.
- `backend/app/prompts/__init__.py` — `load_prompt(name) -> (system, user_template)`, `lru_cache`, 주석 라인 스트립.
- `backend/app/schemas/__init__.py` — 패키지 마커.
- `backend/app/schemas/ai.py` — Pydantic v2 `AxisScore`, `FortuneAxis`, `FaceAnalysisResult`, `FortuneReadingResult` (`score: int ge=0 le=10`, `lucky_inning ge=1 le=9`, `ConfigDict(extra="ignore")` 로 Claude 스키마 드리프트 내성).

### 2-2. 해시 폴백 ✅

**생성:** `backend/app/services/hash_fallback.py`
- `hash_face_scores(pitcher_id, season)` → 5축 int + detail 스트링
- `hash_fortune_scores(pitcher_id, game_date)` → 5축 int + reading 스트링 + `lucky_inning`
- `sha256(f"{pid}-{season}-{axis}") % 11 + 2` 로 클램프, 평균을 ~5.5 로 올려 0/10 쏠림 방지.
- 순수 동기, 의존성 없음, API 키 불필요 — Phase 2 전체 스모크가 이걸로 돈다.

**검증:** `hash_face_scores(1, 2026)` = `command=9, stuff=3, composure=6, dominance=10, destiny=4` (평균 6.4, 범위 고루 분포). `hash_fortune_scores(1, 2026-04-13)` = `command=6, stuff=8, composure=8, dominance=10, destiny=4, lucky_inning=3`.

### 2-3. face_analyzer (Claude Vision) ✅

**생성:** `backend/app/services/face_analyzer.py`
- `async def get_or_create_face_scores(session, pitcher, season=2026) -> FaceScore`
- 플로우: `(pitcher_id, season)` 캐시 히트 → 즉시 반환 (⚠️ Claude 재호출 금지). 미스면 `profile_photo` 로컬/URL 분기 → base64 or url source → `AsyncAnthropic.messages.create(model=claude-opus-4-6, system=[{cache_control: ephemeral}], ...)` → JSON 파싱 → `FaceAnalysisResult`.
- 실패 핸들링: 1차 실패 → `temperature=0` 재시도 → 2차 실패 → `hash_face_scores` 폴백.
- `profile_photo is None` → Claude 스킵, 경고 로그 + 폴백.
- 클라이언트는 지연 초기화 (`_get_client()`) — 모듈 임포트 시점에 API 키 없어도 폭발 X.
- `analyzed_at` 는 KST 타임스탬프 (`datetime.now(tz=ZoneInfo("Asia/Seoul"))` naive cast).
- 로깅: `pitcher_id, model, input_tokens, output_tokens, cache_read_tokens`.

### 2-4. fortune_generator (Claude Text) ✅

**생성:** `backend/app/services/fortune_generator.py`
- `async def get_or_create_fortune_scores(session, pitcher, game_date, *, opponent_team, stadium) -> FortuneScore`
- 플로우: `(pitcher_id, game_date)` 캐시 히트 → 즉시 반환. 미스면 `load_prompt("fortune_reading")` → user 블록 포맷 → `AsyncAnthropic.messages.create(model=claude-sonnet-4-6, system=[{cache_control: ephemeral}], temperature=0.7)` → JSON 파싱 → `FortuneReadingResult`.
- 재시도/폴백 동일 (`temperature=0` 재시도 → `hash_fortune_scores`).
- `generated_at` KST.
- ⚠️ 코드리뷰 1 차 지적 사항 반영: 초기에 `_get_client` 중복 정의 + `__wrapped__` 더미가 있었음 → 삭제 완료.

### 2-5. chemistry_calculator (룰 기반, AI 없음) ✅

**생성:** `backend/app/services/chemistry_calculator.py`
- `ChemistryBreakdown(base, zodiac_delta, zodiac_label, element_delta, element_label, raw, final)` 데이터클래스 (frozen).
- `calculate_chemistry(home_cz, away_cz, home_el, away_el) -> ChemistryBreakdown`
- `chemistry_for_pitchers(home, away)` 덕타입 래퍼 — ORM 의존성 없음 → 테스트 쉬움.
- `data/zodiac_compatibility.json` + `data/constellation_elements.json` 에서 룰·메타 로드. `base_score` 와 `clamp_range` 를 **JSON `_meta` 에서 읽음** → 설계 바뀌면 JSON 만 수정.
- 띠 매칭 순서: 동일띠 → 삼합(+2) → 육합(+1.5) → 원진(-1.5) → 충(-2) → 중립. (동일띠는 삼합 스캔 전에 걸러 자기 자신과 삼합 매칭되는 걸 방지.)
- 원소: 동일(+1), 상생 불-바람/물-흙(+1.5), 상극 불-물/바람-흙(-1), 나머지 중립.
- 알 수 없는 띠/원소 → `ValueError` (사일런트 폴백 X).
- clamp: `max(0, min(4, base + zodiac_delta + element_delta))`.

**검증 (서브에이전트 스모크):**
| 케이스 | 기대 | 결과 |
|---|---|---|
| 자+진, 물+불 | 삼합+2, 상극-1, final=3.0 | ✅ |
| 자+오, 물+불 | 충-2, 상극-1, raw=-1 → clamp 0.0 | ✅ |
| 진+진, 불+불 | 동일띠 0, 동질+1, final=3.0 | ✅ |
| 알 수 없는 입력 | `ValueError` | ✅ |

### 2-6. scoring_engine (컴바이너) ✅

**생성:** `backend/app/services/scoring_engine.py`
- 데이터클래스 (frozen): `AxisTotal`, `PitcherScoreCard`, `MatchupScore`.
- `AXIS_ORDER = ("command", "stuff", "composure", "dominance", "destiny")` — 프로젝트 전역 고정 순서.
- **상성은 destiny 축에만 가산.** 나머지 4축은 `chemistry=0.0`. destiny 총점 = face + fortune + chemistry.final (최대 24), 다른 축은 최대 20.
- 양 투수는 **같은** chemistry 값을 공유 (대칭 속성, 더블 카운트 X).
- 승자 판정: 축별로 `winner_side` ("home"/"away"/"tie") 기록, 매치업 전체 승자는 `home.total` vs `away.total` 비교.
- 한줄평 (룰 기반, AI 없음): gap≥15 압도, ≥8 우세, ≥3 근소, <3 박빙 (상성 라벨 삽입).
- **Public API:**
  - `async def score_matchup(session, home_pitcher, away_pitcher, game_date, *, season=2026, opponent_team_for_home="", opponent_team_for_away="", stadium="") -> MatchupScore` — face/fortune 캐시 통해 로드 → 내부에서 `score_matchup_from_raw` 호출.
  - `def score_matchup_from_raw(home, away, home_face, home_fortune, away_face, away_fortune, game_date) -> MatchupScore` — 순수 동기, DB/AI 없이 스코어링. **캘리브레이션 전용 경로.**

### 2-7. 캘리브레이션 스모크 ✅

`score_matchup_from_raw` + `hash_fallback` 로 시드된 10명 중 5 매치업 실행 (Claude API 콜 없음):

```
원태인(70.0) vs 곽빈(64.0)     → home: 원태인 근소한 우세 — 경기 흐름이 관건
  chem=원진/상생 final=2.0
네일(70.0) vs 카스타노(76.0)   → away: 카스타노 근소한 우세 — 경기 흐름이 관건
  chem=원진/상극 final=0.0
손주영(62.0) vs 박세웅(71.0)   → away: 박세웅 우세 — 오늘은 박세웅 쪽에 기운이 기운다
  chem=육합/상생 final=4.0
임찬규(72.5) vs 문동주(55.5)   → home: 임찬규 압도적 우세 — 관상과 운세가 모두 그 편
  chem=중립/상생 final=3.5
양현종(74.0) vs 하트(86.0)     → away: 하트 우세 — 오늘은 하트 쪽에 기운이 기운다
  chem=삼합/상극 final=3.0
```

- 총점 분포 55~86 (이론상 0~108). 0/108 쏠림 없음.
- 홈 2승 / 원정 3승 — 계통적 편향 없음.
- 상성은 5 케이스 중 4 개에서 non-zero, 클램프 바닥(0.0)과 천장(4.0) 둘 다 히트.
- 한줄평 4 가지 템플릿 (근소/근소/우세/압도/우세) 모두 작동.

### 2-8. 코드 리뷰 라운드트립 ✅

`code-reviewer` 서브에이전트 리뷰 → 2 건 크리티컬 + 1 건 노트:

1. ❌ **Fix**: `fortune_generator._get_client` 중복 정의 + `__wrapped__` 더미 제거.
2. ❌ **Fix**: `face_analyzer` / `fortune_generator` 의 `datetime.utcnow()` → KST 로 교체 (`ZoneInfo("Asia/Seoul")`). CLAUDE.md §4 "hardcoded UTC 금지" 준수.
3. ⚠️ **Note**: destiny 축만 최대 24, 나머지 4축 최대 20 → 스펙과 일치 (의도된 비대칭). 수정 불필요.

"검증 불가" 로 플래그된 항목은 아래 처럼 이미 Phase 1 시점에 충족되어 있음을 재확인:
- `FaceScore` / `FortuneScore` `UniqueConstraint` 존재 (DB 레벨 중복 삽입 차단) → Phase 1 §1-3 참조.
- `zodiac_compatibility.json._meta.clamp_range == [0, 4]` → Phase 1 §1-5 참조.

### 2-9. Phase 2 스모크 최종 결과

```
$ cd backend && python -c "... imports + hash + KST ..."
imports OK
hash face: {'command': 9, ..., 'destiny': 4, 'overall_impression': '(폴백)...'}
hash fortune: {'command': 6, ..., 'lucky_inning': 3}
now_kst face: 2026-04-13 20:18:58
now_kst fort: 2026-04-13 20:18:58
prompt load OK
```

⚠️ **실제 Claude API 호출은 아직 검증 전.** `ANTHROPIC_API_KEY` 가 환경에 없어서 face_analyzer/fortune_generator 의 **캐시 미스 경로**는 Phase 3 통합 시점에 실제 키를 꽂고 (1) 첫 호출이 Claude 를 타는지, (2) 두 번째 호출이 DB 캐시에서 바로 반환되는지 둘 다 로그로 확인해야 한다. 캐시 히트 경로와 폴백 경로는 이번 Phase 에서 이미 검증됨.

### 2-10. Phase 2 파일 맵

```
backend/app/
├── prompts/
│   ├── __init__.py               # load_prompt() with lru_cache
│   ├── face_analysis.txt         # README §4-1
│   └── fortune_reading.txt       # README §4-2
├── schemas/
│   ├── __init__.py
│   └── ai.py                     # Pydantic v2 result models
└── services/
    ├── __init__.py
    ├── hash_fallback.py          # deterministic outage fallback
    ├── chemistry_calculator.py   # rule-based 상성, clamp [0,4]
    ├── face_analyzer.py          # Claude Vision + season cache
    ├── fortune_generator.py      # Claude Text + daily cache
    └── scoring_engine.py         # MatchupScore combiner
```

---

## 🔜 Phase 3 시작 전 체크리스트 (새 세션용)

1. `.env` 에 `ANTHROPIC_API_KEY` 세팅 (Phase 2 캐시 미스 경로 실제 검증 전까지 AI 파이프라인은 "논리적으로만" 완성).
2. `python -c "from app.services.scoring_engine import score_matchup_from_raw; ..."` 로 Phase 2 스모크 재현 (필요 시).
3. Phase 3 크롤러가 채워야 하는 나머지 2 팀 (**KT, KW**) 의 선발 로테이션은 `data/pitchers_2026.json` 이 아직 비어 있다. 크롤 결과를 JSON 에 upsert 하거나 크롤러가 직접 DB 에 쓸지 설계 필요.

---

## ✅ Phase 3 sub-task 1 — 크롤러 (완료: 2026-04-13)

Phase 3 의 목표: 일일 일정/선발 투수 크롤링 → 이름 매칭 → 스케줄러가 `score_matchup()` 로 matchups 생성. 이번 sub-task 는 **read-only 크롤러** 까지. DB write + APScheduler 는 sub-task 2 로 분리.

### 3.1-1. 생성 파일 ✅

**신규:**
- `backend/app/schemas/crawler.py` — Pydantic v2 `ScheduleEntry` (`home_team, away_team, stadium, game_time, home_starter_name, away_starter_name, source: Literal["kbo","naver","statiz"], source_url`). `from __future__ import annotations` 없음, `Optional[X]` 명시.
- `backend/app/services/crawler.py` — 메인 크롤러 모듈
- `scripts/crawl_today.py` — CLI 드라이런 엔트리포인트

### 3.1-2. 크롤러 내부 구조 ✅

**Public API:**
- `async def fetch_today_schedule(game_date: date) -> list[ScheduleEntry]` — KBO → 네이버 → 스탯티즈 폴백 체인. 첫 non-empty 소스가 승. 모두 empty 면 `[]` 반환 (never raises).
- `async def match_pitcher_name(session, name, team) -> Optional[int]` — `_normalize_name()` (strip whitespace) → `(name, team)` exact → `name_en` (영문 이름) exact → `rapidfuzz.fuzz.WRatio ≥ 85` 퍼지 매칭 (same team scope). 실패 시 `_append_review()` 로 `data/crawler_review_queue.json` JSON 큐에 `{date, team, name, reason, best_fuzzy_score}` append. **Never raises.**

**HTTP 레이어:**
- `_make_client()` — `httpx.AsyncClient`, UA `FACEMETRICS/0.1 (+research)`, timeout 10s, **`follow_redirects=False`** (Statiz 로그인 리다이렉트 silent-follow 차단용).
- `_robots_allows(client, url)` — 호스트별 `urllib.robotparser.RobotFileParser` 캐시. robots.txt fetch 자체도 rate-limited (cold cache 에서 data fetch 직전 sleep). fetch 실패 시 fail-open (robots 엔드포인트 자체가 500 일 때 크롤러가 죽지 않게).
- `_RobotsBlocked(Exception)` — robots 차단 시 내부 sentinel, except 분기로 "API call failed" 오탐 로그 방지.

**소스 3종 (각각 `async def _fetch_{kbo,naver,statiz}`):**
- `_fetch_kbo`: `https://www.koreabaseball.com/Schedule/Schedule.aspx?gameDate=YYYYMMDD` — HTTP 200 나오지만 게임 행이 JS 렌더링 (`S2i.MakeTable` 호출). CSS 셀렉터는 SPECULATIVE 로 주석 명시 (`KBO_ROW_SEL` 등). 0 rows 매칭 시 warning 로그 + `[]` 반환 (no crash).
- `_fetch_naver`: **JSON API 우선** `https://api-gw.sports.naver.com/schedule/games?gameDate=YYYYMMDD&...` → 실패/empty 시 HTML 폴백 `https://sports.naver.com/kbaseball/schedule/index` (HTML 은 JS SPA 라 현재 0 rows).
  - **라이브 검증 2026-04-13:** API 는 `{"code":200,"result":{"games":[],"gameTotalCount":0}}` 정상 반환 (오늘은 오프데이). 엔드포인트는 VERIFIED. `games[0]` 객체의 키 (`homeTeamCode`, `homeStartingPitcherName`, `gameDateTime`, `stadium`) 는 공개 Naver Sports API 관행 기반 SPECULATIVE — 첫 실제 경기일에 검증 필요.
  - `NAVER_TEAM_MAP` 중복 `"SS"` 키 이슈 해결: `"SK": "SSG"` (SK Wyverns 레거시), `"SS": "SAM"` (Samsung). Naver 가 실제로 SSG에 다른 코드를 쓰면 `_normalize_team()` 폴백이 잡음. 이것도 첫 실제 경기일 검증 대상.
- `_fetch_statiz`: `www.statiz.co.kr/schedule.php?opt=1&sy=&sm=&sd=` — 라이브 검증 시 **robots.txt 가 해당 경로를 disallow**. skip 로깅 후 `[]`. 로그인 벽 + robots 두 방어선 통과 못 함 → 사실상 dead source. 다음 sub-task 에서 daum.net 으로 교체 검토.

**레이트 리밋 / robots:**
- CLAUDE.md §5: ≤1 req/sec per host + robots.txt 준수 + UA 헤더.
- 각 `_fetch_*` 내부에서 `asyncio.sleep(RATE_LIMIT_S=1.0)` + `_robots_allows()` 프리체크. 크로스-소스 sleep 은 없음 (다른 호스트).
- robots.txt fetch 본체도 1초 sleep 후 호출 (cold cache 시 같은 호스트 2회 연속 요청 방지).

### 3.1-3. 이름 매처 검증 ✅

18 케이스 전부 통과 (kbo-data-crawler 서브에이전트 스모크):
| 입력 | 기대 | 결과 |
|---|---|---|
| `원태인` / SAM | id=1 exact | ✅ |
| `james naile` / KIA | id=3 `name_en` exact | ✅ |
| `James Naile` / KIA | id=3 | ✅ |
| `네일 ` (trailing space) / KIA | id=3 normalize | ✅ |
| `곽 빈` (internal space) / DS | id=2 | ✅ |
| `원태인이` (1 extra char) / SAM | id=1 fuzzy ~92 | ✅ |
| `소형준` / KT | None → review queue | ✅ |
| `손주영` / DS (wrong team) | None → review queue | ✅ |

리뷰 큐 JSON 파일은 UTF-8 로 누적. 레이스 컨디션은 아직 미해결 (sub-task 2 에서 fcntl 락 or DB 테이블로 승격 예정).

### 3.1-4. 드라이런 스모크 (`scripts/crawl_today.py`) ✅

```
INFO  httpx  GET https://www.koreabaseball.com/robots.txt 200
INFO  httpx  GET https://www.koreabaseball.com/Schedule/Schedule.aspx?gameDate=20260413 200
WARN  [crawler:kbo] selector 0 rows — site HTML may have changed
INFO  [crawler] kbo → 0 → trying naver
INFO  httpx  GET https://api-gw.sports.naver.com/robots.txt 404  (fail-open)
INFO  httpx  GET https://api-gw.sports.naver.com/schedule/games?...&gameDate=20260413 200
WARN  [crawler:naver-api] API returned 0 games for 2026-04-13 — trying HTML
INFO  httpx  GET https://sports.naver.com/robots.txt 200
INFO  [crawler:naver] robots.txt disallows /kbaseball/schedule/index — skipping HTML
INFO  [crawler] naver → 0 → trying statiz
INFO  httpx  GET http://www.statiz.co.kr/robots.txt 200
INFO  [crawler:statiz] robots.txt disallows /schedule.php — skipping source
ERROR [crawler] ALL sources empty for 2026-04-13 — returning empty list.
```

→ 3-tier 폴백 체인 정상, robots 차단 로깅 정상, 크래시 없음. 스크립트 최종 출력도 "No games found" 안내문으로 graceful.

### 3.1-5. 코드 리뷰 라운드트립 ✅

**1라운드** — 3건 critical:
1. ❌ **Fix**: `_fetch_naver` 의 `NAVER_TEAM_MAP` 중복 `"SS"` 키 silent overwrite → SSG 가 SAM 으로 매핑되는 데이터 손상 버그. `"SK": "SSG"` + `"SS": "SAM"` 로 분리.
2. 🚫 **Reject (false positive)**: `from __future__ import annotations` 가 위험하다는 지적은 PROGRESS.md §1-3 오독. 해당 이슈는 `Mapped[...]` **정의** 파일 한정이고, `crawler.py` 는 `Pitcher` 를 runtime import/use 할 뿐 (`select(Pitcher)`, `list[Pitcher]`). PEP 563 lazy eval 과 무관. 모델 파일들은 여전히 `__future__` 없음 — 원상 유지.
3. ❌ **Fix**: `follow_redirects=True` + robots.txt 체크 없음 = CLAUDE.md §5 위반. `_make_client()` 를 `follow_redirects=False` 로, `_robots_allows()` 헬퍼 추가 + 4개 fetch 사이트 전부 프리체크.

**2라운드** — 1라운드 fix 재검증 + 3건 minor:
1. ❌ **Fix**: cold-cache 에서 robots.txt fetch 와 data fetch 가 같은 호스트에 zero delay 로 연속 → "≤1 req/sec per host" 미세 위반. `_robots_allows()` 안에 `asyncio.sleep(RATE_LIMIT_S)` 추가.
2. ❌ **Fix**: Naver API 가 robots 차단될 때 `raise RuntimeError(...)` 패턴이 except 핸들러에서 "API call failed" warning 으로 오분류. `_RobotsBlocked` sentinel exception 클래스 추가 + except 에서 별도 분기.
3. ❌ **Fix**: `fetch_today_schedule` 의 inter-source `asyncio.sleep` 2곳이 redundant (소스마다 호스트가 다름 + 각 `_fetch_*` 내부에서 이미 sleep). 제거.
4. ℹ️ **Note**: `_ROBOTS_CACHE` 는 프로세스 로컬 모듈 dict — Gunicorn 멀티워커에서는 워커별로 1회씩 fetch. 현 스펙상 허용 범위.

**최종 verdict (라운드 2):** "fix-then-ship" → minor 3건 처리 후 드라이런 재실행 → 출력 동일하게 graceful, 오탐 로그 사라짐. 크롤러 sub-task 승인.

### 3.1-6. Phase 3 sub-task 1 파일 맵

```
backend/app/
├── schemas/
│   └── crawler.py              # Pydantic v2 ScheduleEntry
└── services/
    └── crawler.py              # fetch_today_schedule + match_pitcher_name
                                # + _fetch_{kbo,naver,statiz} + _robots_allows

scripts/
└── crawl_today.py              # CLI dry run (read-only, no DB write yet)

data/
└── crawler_review_queue.json   # 미매칭 이름 누적 (최초 생성됨)
```

---

## 🗺️ Phase 3 sub-task 2 — DB write + Scheduler (다음 세션 TODO)

### 인수인계 (가장 먼저 읽을 것)

1. **현재 tracked/untracked 상태:**
   - `backend/app/services/crawler.py` 는 아직 git **untracked**. 2라운드 리뷰까지 마쳤지만 아직 커밋 X. sub-task 2 착수 전에 `git add backend/` + `git commit -m "feat: Phase 3 sub-task 1 crawler"` 권장.
   - `.claude/settings.json`, `.claude/hooks/code-reviewer-gate.sh` 도 새로 추가됨 (Stop hook 자동화). 커밋 해서 팀 공유 가능. `.claude/.last-reviewed-hash` 는 이미 `.gitignore` 에 추가돼 제외됨.

2. **Stop hook 주의:** 이 세션부터 `응답 종료 시 code-reviewer 게이트`가 자동으로 발동. 코드를 수정한 뒤 stop 하려고 하면 훅이 1회 블록하며 code-reviewer 서브에이전트 호출을 강제한다. 루프 방지는 diff 해시 마커로 처리. 끄고 싶으면 `/hooks` 메뉴에서 disable.

3. **Phase 2 캐시 미스 경로 실제 검증은 여전히 미완료.** `.env` 에 `ANTHROPIC_API_KEY` 넣고 Phase 3 sub-task 2 의 분석 잡이 처음 도는 순간에 (1) 첫 호출 Claude 히트, (2) 두 번째 호출 DB 캐시 히트 둘 다 로그 확인해야 함. sub-task 2 완료 정의에 포함.

### sub-task 2 체크리스트

- [ ] **`upsert_schedule(session, entries)` in `crawler.py`** — `list[ScheduleEntry]` 를 `daily_schedules` 테이블에 `(game_date, home_team, away_team)` 자연 키로 upsert. `home_starter` / `away_starter` 는 raw 이름 문자열 저장 (pitcher FK 는 `matchups` 테이블 몫).
- [ ] **`backend/app/scheduler.py`** — `AsyncIOScheduler(timezone=ZoneInfo("Asia/Seoul"))` 로 다음 5개 잡:
  - `08:00 KST` → `fetch_today_schedule` → `upsert_schedule`
  - `09:00 KST` → 선발 미발표 (`home_starter IS NULL OR away_starter IS NULL`) 재시도
  - `10:00 KST` → 최종 재시도. 이후는 TBD 슬롯 confirmed-unknown 마킹.
  - `10:30 KST` → complete matchup 마다 `score_matchup()` 호출, `matchups` 쓰기. **여기서 Phase 2 캐시 미스 경로 처음 돌음.**
  - `11:00 KST` → `matchups.is_published = True` 게시 플래그.
- [ ] **Statiz → daum 교체.** `https://baseball.daum.net/schedule/team` 또는 `https://sports.daum.net/schedule/kbo` 중 robots.txt 통과하는 쪽으로. 기존 `_fetch_statiz` 는 함수 이름 유지하면서 내부 URL 만 교체하는 게 호출부 영향 최소.
- [ ] **KBO JS-rendered 엔드포인트 탐색.** DevTools Network 탭에서 `S2i.MakeTable` 이 호출하는 실제 XHR 캡처 → 그걸 `_fetch_kbo` 의 새 타겟으로. 현재 HTML 셀렉터는 speculative placeholder.
- [ ] **KT / KW 로테이션 투수 시드.** `data/pitchers_2026.json` 에 2팀 추가 → `scripts/seed_pitchers.py` 재실행. 아니면 크롤러가 미지 이름 만나면 리뷰 큐로 넣는 현재 경로로 점진 채움.
- [ ] **`scripts/crawl_today.py --write` 플래그.** 현재는 read-only 드라이런. `--write` 주면 `upsert_schedule` 까지 태우는 모드 추가.
- [ ] **리뷰 큐 concurrency.** `_append_review` JSON 파일 읽기-수정-쓰기 레이스 → fcntl advisory lock 붙이거나 `review_queue` DB 테이블로 승격.
- [ ] **Alembic 도입 여부 결정.** 지금까지는 `Base.metadata.create_all` 만 쓰고 있는데, `daily_schedules` / `matchups` 에 새 컬럼 추가가 얼마나 자주 일어날지에 따라 결정. 현재 dev SQLite 상태에서는 `create_all` 로 충분.

### 실행 스모크 아이디어

- sub-task 2 완료 시 `python scripts/crawl_today.py --write` → DB 에 `daily_schedules` row 생성 → `python -c "await score_matchup(...)"` → `matchups` row 생성 → `/api/today` (Phase 4 에서 생길) 전에 직접 `SELECT * FROM matchups` 로 확인.
- APScheduler 는 dev 환경에서 `trigger="interval", seconds=5` 같은 짧은 간격으로 전환해서 즉시 잡 실행 확인 가능. prod 전환 시 `CronTrigger(hour=..., minute=..., timezone=KST)` 로 교체.

---

## 🗺️ Phase 4~6 (개략, 상세는 그때 채움)

- **Phase 4:** `app/routers/{today, matchup, pitcher, admin}.py`, Pydantic response schemas, pytest
- **Phase 5:** `frontend/` 를 Next.js 14 App Router 로 재초기화 (draft.html 은 톤앤매너 레퍼런스로 보존), shadcn/ui, Pretendard, Recharts 레이더
- **Phase 6:** docker-compose, 면책 고지, Vercel + Railway 배포, GitHub Actions 게이트, 공유 카드 PNG

---

## 📁 파일 맵 스냅샷 (Phase 1 종료 시점)

```
backend/
├── .env.example
├── requirements.txt
└── app/
    ├── __init__.py
    ├── config.py
    ├── db.py
    ├── main.py
    └── models/
        ├── __init__.py
        ├── pitcher.py
        ├── face_score.py
        ├── fortune_score.py
        ├── matchup.py
        └── daily_schedule.py

scripts/
├── crawl_pitcher_images.py    # 기존 (Phase 1 전)
├── init_db.py                 # 신규 Phase 1
└── seed_pitchers.py           # 신규 Phase 1

data/
├── pitcher_images/
│   ├── manifest.json          # 기존 (Phase 1 전)
│   ├── kbo/                   # 10장 (gitignored)
│   └── namuwiki/              # (gitignored)
├── zodiac_compatibility.json  # 신규 Phase 1
├── constellation_elements.json # 신규 Phase 1
├── pitchers_2026.json         # 신규 Phase 1
└── facemetrics.db             # 신규 Phase 1 (gitignored)
```
