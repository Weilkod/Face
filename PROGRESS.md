# FACEMETRICS — Implementation Progress

새 세션에서 이어서 작업할 수 있게 Phase 단위로 완료 내역을 기록한다.
각 항목은 **완료일 / 생성·수정 파일 / 검증 방법 / 새 세션을 위한 메모** 형식.

- **Spec source of truth:** `README.md` + `CLAUDE.md`
- **현재 단계:** Phase 1 ✅ → Phase 2 ✅ → Phase 3 sub-task 1 (크롤러) ✅ → Phase 3 sub-task 2 (DB write + Scheduler 글루) ✅ → 다음은 **sub-task 2 carry-over** (소스 품질 + Claude 캐시 미스 실검증)
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

## ✅ Phase 3 sub-task 2 — DB write + Scheduler 글루 (완료: 2026-04-13)

Phase 3 의 목표: 일일 일정/선발 투수 크롤링 → 이름 매칭 → `score_matchup()` 파이프라인 → `matchups` DB write → 오전 11시 게시. sub-task 1 이 read-only 크롤러였고, 이번 sub-task 2 는 **DB write + APScheduler 글루** 까지. 실제 소스 HTML/XHR 은 여전히 placeholder (아래 carry-over 섹션 참조).

### 3.2-1. `upsert_schedule()` + null-safe 재시도 ✅

**수정:** `backend/app/services/crawler.py` (파일 하단에 함수 추가 + `DailySchedule` import)

핵심 설계:
- 자연 키: `(game_date, home_team, away_team)`.
- **Null-safety (CLAUDE.md §5):** 한 번 확정된 선발은 이후 재크롤에서 `None` 으로 덮어써지지 않는다. 09:00 / 10:00 재시도 잡이 이 보장을 믿고 그대로 같은 entry 배치를 다시 밀어넣을 수 있음.
- **Mismatch → 리뷰 큐 (CLAUDE.md §5):** DB 의 확정 이름과 새 크롤 이름이 **다른** 경우, DB 값은 보존하고 `_append_review({reason: "upsert mismatch: confirmed starter disagrees with new crawl", ...})` 로 리뷰 큐에 기록. 단순 경고 로그만 찍고 끝내지 않음 (1차 리뷰에서 잡힌 버그).
- 반환: `{"inserted": n, "updated": n, "skipped": n}`. 끝에 한 번 commit.

### 3.2-2. `backend/app/scheduler.py` — 5개 KST 크론 잡 ✅

**신규 파일:** `backend/app/scheduler.py`

`AsyncIOScheduler(timezone=ZoneInfo("Asia/Seoul"))` 위에 `CronTrigger` 로 5개 잡 등록:

| 시각 (KST) | 잡 이름 | 역할 |
|---|---|---|
| 08:00 | `fetch_and_upsert_schedule` | 크롤러 → `upsert_schedule` |
| 09:00 | `retry_missing_starters` | `home_starter IS NULL OR away_starter IS NULL` 있으면 재크롤 |
| 10:00 | `retry_missing_starters` | 최종 재시도 (같은 함수) |
| 10:30 | `analyze_and_score_matchups` | 양쪽 선발 확정된 게임마다 `score_matchup()` 호출 → `matchups` upsert → **per-game commit**. **여기서 Phase 2 Claude 캐시 미스 경로가 처음 돌 예정.** |
| 11:00 | `publish_matchups` | `matchups.is_published = True` 플립 |

구조 포인트 (리뷰 3패스 거친 뒤 확정):
- **Per-game atomic 경계.** `try:` 안에 `score_matchup()` + `_upsert_matchup_row()` + `session.commit()` 이 한 덩어리로 묶여 있음. 실패하면 `session.rollback()` 한 뒤 다음 게임으로 continue — 이전에 커밋된 게임들은 살아남음.
- **Core Row 튜플 SELECT.** `analyze_and_score_matchups` 는 `select(DailySchedule.home_team, ..., DailySchedule.away_starter)` 로 ORM 인스턴스 대신 plain `Row` 를 받아옴. 그래서 per-game rollback 이 identity map 을 만료시켜도 loop body 의 Korean starter 이름 / team code 가 expired ORM attribute 가 아니라서 `MissingGreenlet` 위험 없음 (2패스 리뷰 블로커).
- **`_wrap()` helper.** 각 잡을 감싸서 예외가 scheduler / FastAPI 로 bubble 하지 않게 잡아 로그만 남김.
- **`build_scheduler()` 팩토리** 만 export. `.start()` / `.shutdown()` 은 호출부 (FastAPI lifespan) 책임.

### 3.2-3. FastAPI lifespan 에 scheduler wiring ✅

**수정:** `backend/app/main.py`

`@asynccontextmanager lifespan()` 에서 `build_scheduler()` 호출 → `scheduler.start()` → `yield` → `scheduler.shutdown(wait=False)`. `uvicorn app.main:app` 부팅하면 5개 잡이 자동 등록되고, 서버 끄면 깨끗이 정지.

### 3.2-4. `Matchup.is_published` 컬럼 추가 ✅

**수정:** `backend/app/models/matchup.py`

```python
is_published: Mapped[bool] = mapped_column(
    Boolean, nullable=False, default=False, server_default=false()
)
```

- `sqlalchemy.false()` expression 사용 (Postgres 에서 `FALSE` / SQLite 에서 `0` 으로 컴파일됨). 초기에 `server_default="0"` 문자열 리터럴로 썼다가 1차 리뷰에서 Postgres 호환성 문제 지적받고 교체.
- dev SQLite DB 는 `matchups` 가 이미 존재했기 때문에 `create_all` 로는 컬럼 추가 안 됨 → 수동으로 `ALTER TABLE matchups ADD COLUMN is_published BOOLEAN NOT NULL DEFAULT 0` 실행했음. **prod Postgres 로 넘어갈 때는 Alembic migration 으로 재현 필요.**

### 3.2-5. `scripts/crawl_today.py --write` 플래그 ✅

**수정:** `scripts/crawl_today.py`

`--write` 주면 step 6 에서 `upsert_schedule(session, entries)` 까지 태우고 `{inserted, updated, skipped}` 카운트 출력. 기본값은 read-only dry-run (이전 동작 유지). 헤더에 `[--write]` / `[dry-run]` 마커 표시.

### 3.2-6. Phase 3 sub-task 2 파일 맵

```
backend/app/
├── main.py                  (수정: lifespan → build_scheduler/start/shutdown)
├── scheduler.py             (신규: 5개 KST 잡 + build_scheduler)
├── models/matchup.py        (수정: is_published BOOLEAN default false())
└── services/crawler.py      (수정: upsert_schedule + mismatch → _append_review)

scripts/
└── crawl_today.py           (수정: --write 플래그)
```

### 3.2-7. 검증 스모크 (이번 세션에서 통과)

1. `python -c "from app.scheduler import build_scheduler; ..."` → 5 개 잡 (`fetch_schedule_08` / `retry_missing_09` / `retry_missing_10` / `analyze_score_1030` / `publish_11`) 등록 확인.
2. `upsert_schedule` 4단계 테스트: 첫 insert 2 rows → 재실행 all-skipped → TBD 쪽 starter 채우기 updated=1 → confirmed 쪽에 `None` 밀기 skipped (null-safe 통과).
3. 확정 이름 vs 다른 이름 mismatch → `data/crawler_review_queue.json` 에 reason `"upsert mismatch..."` entry 1건 추가됨 확인.
4. `analyze_and_score_matchups` 를 빈 DB + seeded 2 rows (unknown starter) 두 경우에 돌려서 각각 `{skipped: 0}` / `{skipped: 2}` 반환, `MissingGreenlet` 없음.
5. `scripts/crawl_today.py --date 2026-04-13 --write --loglevel WARNING` → 크롤러가 0 entries 반환 (여전히 소스 placeholder 한계) 하지만 CLI 가 깨끗하게 빠져나옴.

### 3.2-8. 리뷰 히스토리 (code-reviewer 3 pass)

- **1차:** 🔴 per-game `try/except` 범위 부족 (upsert 에러가 loop-level `session.commit()` 를 날림) / 🔴 upsert mismatch 가 리뷰 큐로 안 감 / 🟡 `server_default="0"` Postgres 호환성 → 전부 수정.
- **2차:** 🔴 rollback 후 ORM row 가 identity map 에서 expire 되면서 다음 iteration 의 attribute access 가 async 컨텍스트에서 lazy-load 를 걸음 (`MissingGreenlet`) → Core Row 튜플로 전환하며 해결.
- **3차:** 🟢 이번 diff 자체는 clean. 단, `score_matchup` 안쪽 `face_analyzer` / `fortune_generator` 가 **중간에 commit** 하기 때문에 Claude Vision 성공 + Claude Text 실패 시 고아 `face_scores` row 가 남는 문제는 **Phase 2 코드의 이슈**지 이번 diff 리그레션이 아님. Carry-over 로 기록.

---

## 🚨 Phase 3 sub-task 2 carry-over — 다음 세션 TODO

Sub-task 2 의 **글루 코드**는 완성됐지만, 실제로 10:30 잡이 의미 있게 돌려면 다음 항목들이 채워져야 함. 우선순위 순서:

### A. 데이터 소스 품질 (선순위 — 이거 없으면 10:30 잡이 skip 만 찍음)

- [ ] **Statiz → Daum 교체.** `https://baseball.daum.net/schedule/team` 또는 `https://sports.daum.net/schedule/kbo` 중 robots.txt 통과하는 쪽으로. 기존 `_fetch_statiz` 는 함수 이름 유지하면서 내부 URL/selector 만 교체 (호출부 영향 최소).
- [ ] **KBO JS-rendered 엔드포인트 탐색.** DevTools Network 탭에서 `S2i.MakeTable` 이 호출하는 실제 XHR 캡처 → `_fetch_kbo` 의 새 타겟으로. 현재 셀렉터는 speculative placeholder 상태.
- [ ] **네이버 JSON API 재검증.** 2026-04-13 기준 `gameTotalCount: 0` 이었음. 시즌 개막 이후에는 games 배열이 채워질 것이라 가정 중 — 실제 게임 데이터 들어오는 날 한 번 더 돌려서 parser 맞는지 확인.
- [ ] **KT / KW 로테이션 투수 시드.** `data/pitchers_2026.json` 에 2팀 추가 → `scripts/seed_pitchers.py` 재실행. 또는 크롤러가 미지 이름 만나면 리뷰 큐로 쌓는 현재 경로로 점진 채움 (둘 중 하나 선택).

### B. Phase 2 AI 파이프 실검증 (소스 채워지면 자동으로 트리거됨)

- [ ] **Claude 캐시 미스 경로 실검증.** `.env` 에 `ANTHROPIC_API_KEY` 넣은 상태로 10:30 잡 처음 돌 때:
  - (1) face_analyzer 의 첫 호출이 Claude Vision 실제 타고 `face_scores` row 가 기록되는지
  - (2) fortune_generator 의 첫 호출이 Claude Text 실제 타고 `fortune_scores` row 가 기록되는지
  - (3) 동일 `(pitcher_id, date)` 로 같은 잡 재실행 시 두 번째부터 DB 캐시 히트 (Claude 호출 0 회) 되는지
  - → 로그로 모두 확인. 완료 기준에 포함.
- [ ] **고아 score row 문제 (3차 리뷰 flag).** `face_analyzer` / `fortune_generator` 가 `score_matchup` 내부에서 중간 commit 을 치므로, Vision 성공 + Text 실패 시나리오에서 `face_scores` 만 남고 `matchups` 는 안 써지는 고아 상태 발생 가능. **재시도 안전성은 OK** (다음 run 이 캐시 히트) 지만 자동 복구 경로 없음. `claude-ai-integrator` 에게 savepoint 도입 or 문서화 위임.
- [ ] **Rollback 분기 유닛 테스트.** `analyze_and_score_matchups` 의 `except Exception` 분기는 현재 smoke 로 한 번도 안 탔음. Claude 를 mock 해서 중간 raise 시키고 "`matchups` 행 0개, `fortune_scores` 고아 1개, counts['failed']=1" 를 assert 하는 pytest 추가 권장 — 10:30 잡이 실제 API 와 처음 만나기 전에.

### C. 운영 자잘한 개선 (blocker 아님)

- [ ] **리뷰 큐 dedup.** `_append_review` 는 09:00 / 10:00 재시도 잡이 같은 `(date, team, side, crawled_name)` 조합을 여러 번 큐에 밀어넣음. `_append_review` 내부에서 동일 키 존재 확인 후 skip 하는 가드 추가.
- [ ] **리뷰 큐 concurrency.** `_append_review` JSON 파일 읽기-수정-쓰기 레이스 → fcntl advisory lock 또는 `review_queue` DB 테이블로 승격. 현재는 단일 프로세스라 문제 없지만 scheduler 잡이 동시에 돌면 깨질 수 있음.
- [ ] **`publish_matchups` 필터.** `select(Matchup).where(Matchup.game_date == gd, Matchup.is_published.is_(False))` 로 좁혀서 이미 published 된 row 재플립 방지 (harmless but wasteful).
- [ ] **`_get_pitcher` N+1.** `analyze_and_score_matchups` 는 게임당 2번 pitcher select. ≤5 게임/일이라 무시 가능하지만 `where(Pitcher.pitcher_id.in_([...]))` 배치 로드가 더 깔끔.
- [ ] **Alembic 도입 여부 결정.** 이번에 `is_published` 컬럼 추가 때 이미 수동 ALTER TABLE 썼음. prod Postgres 로 넘어가기 전에는 Alembic 환경 세팅 필요. 지금 dev SQLite 단계에서는 `create_all` + 수동 ALTER 로 버틸 수 있음.

### D. 실행 스모크 아이디어

- Scheduler 즉시 확인: dev 에서 `CronTrigger(hour=8,...)` 를 `IntervalTrigger(seconds=5)` 로 임시 교체해 5초마다 돌려보기. prod 전환 시 원복.
- 10:30 잡 수동 트리거: `python -c "import asyncio; from app.scheduler import analyze_and_score_matchups; asyncio.run(analyze_and_score_matchups())"` — 오늘 날짜 기준 daily_schedules 읽어서 full pipeline 타봄.
- `SELECT * FROM matchups WHERE game_date = date('now')` 로 write 결과 직접 확인 (`/api/today` 는 Phase 4).

---

## 🗣️ 다음 세션 시작 시 이 지시 그대로 주면 됨

> **"Phase 3 sub-task 2 는 글루까지 완료 (커밋 ready). 다음 세션 우선순위는 carry-over A (데이터 소스 품질) → B (Claude 캐시 미스 실검증). 먼저 `PROGRESS.md` §"Phase 3 sub-task 2 carry-over" 읽고, A 섹션에서 `_fetch_statiz` → Daum 교체부터 착수. Daum 한 곳이라도 실제 2026 시즌 경기 데이터가 뽑히기 시작하면 그걸로 `scripts/crawl_today.py --write` 돌려서 `daily_schedules` row 확보한 뒤, `.env` 에 `ANTHROPIC_API_KEY` 꽂고 `analyze_and_score_matchups()` 수동 호출해서 B 섹션의 (1)~(3) 로그 확인까지 가는 게 이번 세션 정의. 리뷰 큐 dedup / publish 필터 / Alembic 같은 C 섹션은 최종 커밋 직전에 시간 남으면."**

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
