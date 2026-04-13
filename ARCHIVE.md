# FACEMETRICS — Archive

> 이 파일은 `PROGRESS.md` 에서 자동 이관된 완료 세션 상세 내역이다.  
> 검색 용도로만 활용. 새 작업은 `PROGRESS.md` 에서 진행.

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

현재 10명 수록:

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

`init_db.py` + `seed_pitchers.py` 연속 실행 → `data/facemetrics.db` 에 pitchers 10 row, 모든 프로필 사진 연결 완료.

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
- 순수 동기, 의존성 없음, API 키 불필요

**검증:** `hash_face_scores(1, 2026)` = `command=9, stuff=3, composure=6, dominance=10, destiny=4`. `hash_fortune_scores(1, 2026-04-13)` = `command=6, stuff=8, composure=8, dominance=10, destiny=4, lucky_inning=3`.

### 2-3. face_analyzer (Claude Vision) ✅

**생성:** `backend/app/services/face_analyzer.py`
- `async def get_or_create_face_scores(session, pitcher, season=2026) -> FaceScore`
- 플로우: `(pitcher_id, season)` 캐시 히트 → 즉시 반환. 미스면 base64/url → Claude Vision → JSON 파싱 → `FaceAnalysisResult`.
- 실패 핸들링: 1차 실패 → `temperature=0` 재시도 → 2차 실패 → `hash_face_scores` 폴백.
- `profile_photo is None` → Claude 스킵, 경고 로그 + 폴백.
- 클라이언트는 지연 초기화 (`_get_client()`) — 모듈 임포트 시점에 API 키 없어도 폭발 X.
- `analyzed_at` 는 KST 타임스탬프 (`datetime.now(tz=ZoneInfo("Asia/Seoul"))` naive cast).

### 2-4. fortune_generator (Claude Text) ✅

**생성:** `backend/app/services/fortune_generator.py`
- `async def get_or_create_fortune_scores(session, pitcher, game_date, *, opponent_team, stadium) -> FortuneScore`
- 플로우: `(pitcher_id, game_date)` 캐시 히트 → 즉시 반환. 미스면 → Claude Text (temperature=0.7) → JSON 파싱.
- 재시도/폴백 동일 (`temperature=0` 재시도 → `hash_fortune_scores`).
- `generated_at` KST.

### 2-5. chemistry_calculator (룰 기반, AI 없음) ✅

**생성:** `backend/app/services/chemistry_calculator.py`
- `ChemistryBreakdown(base, zodiac_delta, zodiac_label, element_delta, element_label, raw, final)` 데이터클래스 (frozen).
- `calculate_chemistry(home_cz, away_cz, home_el, away_el) -> ChemistryBreakdown`
- `chemistry_for_pitchers(home, away)` 덕타입 래퍼
- `data/zodiac_compatibility.json` + `data/constellation_elements.json` 에서 룰·메타 로드.
- 띠 매칭 순서: 동일띠 → 삼합(+2) → 육합(+1.5) → 원진(-1.5) → 충(-2) → 중립.
- 원소: 동일(+1), 상생(+1.5), 상극(-1), 나머지 중립.

**검증:**

| 케이스 | 기대 | 결과 |
|---|---|---|
| 자+진, 물+불 | 삼합+2, 상극-1, final=3.0 | ✅ |
| 자+오, 물+불 | 충-2, 상극-1, raw=-1 → clamp 0.0 | ✅ |
| 진+진, 불+불 | 동일띠 0, 동질+1, final=3.0 | ✅ |
| 알 수 없는 입력 | `ValueError` | ✅ |

### 2-6. scoring_engine (컴바이너) ✅

**생성:** `backend/app/services/scoring_engine.py`
- `AXIS_ORDER = ("command", "stuff", "composure", "dominance", "destiny")` — 전역 고정.
- 상성은 destiny 축에만 가산. destiny 총점 최대 24, 다른 축 최대 20.
- **Public API:** `async def score_matchup(...)` + `def score_matchup_from_raw(...)` (순수 동기, 캘리브레이션 전용).

### 2-7. 캘리브레이션 스모크 ✅

`score_matchup_from_raw` + `hash_fallback` 로 5 매치업 실행:

```
원태인(70.0) vs 곽빈(64.0)     → home 근소한 우세
네일(70.0) vs 카스타노(76.0)   → away 근소한 우세
손주영(62.0) vs 박세웅(71.0)   → away 우세
임찬규(72.5) vs 문동주(55.5)   → home 압도적 우세
양현종(74.0) vs 하트(86.0)     → away 우세
```
총점 분포 55~86, 홈 2승/원정 3승, 계통적 편향 없음.

### 2-8. Phase 2 파일 맵

```
backend/app/
├── prompts/
│   ├── __init__.py               # load_prompt() with lru_cache
│   ├── face_analysis.txt
│   └── fortune_reading.txt
├── schemas/
│   ├── __init__.py
│   └── ai.py                     # Pydantic v2 result models
└── services/
    ├── __init__.py
    ├── hash_fallback.py
    ├── chemistry_calculator.py
    ├── face_analyzer.py
    ├── fortune_generator.py
    └── scoring_engine.py
```

---

## ✅ Phase 3 sub-task 1 — 크롤러 read-only (완료: 2026-04-13)

### 3.1-1. 생성 파일 ✅

- `backend/app/schemas/crawler.py` — Pydantic v2 `ScheduleEntry`
- `backend/app/services/crawler.py` — 메인 크롤러 모듈
- `scripts/crawl_today.py` — CLI 드라이런 엔트리포인트

### 3.1-2. 크롤러 구조 ✅

**Public API:**
- `async def fetch_today_schedule(game_date: date) -> list[ScheduleEntry]`
- `async def match_pitcher_name(session, name, team) -> Optional[int]`

**최종 소스 구성:** KBO `GetKboGameList` 단일 소스 (네이버/스탯티즈는 세션 2에서 제거). `/ws/` robots carve-out 적용.

### 3.1-3. 드라이런 스모크 ✅

robots 차단 로깅 정상, 크래시 없음. "No games found" graceful.

### 3.1-4. 코드 리뷰 2라운드 ✅

주요 fix: `NAVER_TEAM_MAP` 중복 키, `follow_redirects=False`, `_RobotsBlocked` sentinel, cold-cache rate limit.

---

## ✅ Phase 3 sub-task 2 — DB write + Scheduler (완료: 2026-04-13)

### 3.2-1. `upsert_schedule()` ✅

자연 키 `(game_date, home_team, away_team)`. null-safe (확정 선발 덮어쓰기 방지). mismatch → 리뷰 큐.

### 3.2-2. `backend/app/scheduler.py` — 5개 KST 크론 잡 ✅

| 시각 (KST) | 잡 | 역할 |
|---|---|---|
| 08:00 | `fetch_and_upsert_schedule` | 크롤 → upsert |
| 09:00 | `retry_missing_starters` | 선발 null 재크롤 |
| 10:00 | `retry_missing_starters` | 최종 재시도 |
| 10:30 | `analyze_and_score_matchups` | `score_matchup()` → matchups upsert |
| 11:00 | `publish_matchups` | `is_published = True` 플립 |

설계 포인트: per-game atomic 경계, Core Row 튜플 SELECT (MissingGreenlet 방지), `_wrap()` 예외 격리.

### 3.2-3. 검증 스모크 ✅

5개 잡 등록, upsert 4단계 테스트, null-safe 통과, mismatch → 리뷰 큐 확인.

### 3.2-4. Phase 3 sub-task 2 파일 맵

```
backend/app/
├── main.py        (수정: lifespan → scheduler wiring)
├── scheduler.py   (신규)
├── models/matchup.py  (수정: is_published BOOLEAN)
└── services/crawler.py  (수정: upsert_schedule)
scripts/
└── crawl_today.py  (수정: --write 플래그)
```

---

## 🕰️ 세션 로그

### 세션 1 (2026-04-13)
Phase 1 + Phase 2 + Phase 3 sub-task 1 완료. 크롤러 초기 구현 (KBO/Naver/Statiz 3-tier 폴백 포함).

### 세션 2 (2026-04-13)
- **완료:** A-1 (헤더), A-2 (GetTodayGames POST 코드), A-3 (GameCenter `_fetch_starters`), A-4 (네이버/스탯티즈 경로 제거).
- `backend/app/services/crawler.py` 951→603줄 재작성. KBO 단일 소스.
- **🚨 블로커:** `robots.txt` 가 `Disallow: /ws/` → `_fetch_kbo` 전체 우회.

### 세션 3 (2026-04-13) — blocker 해제
- GameCenter HTML 안 JS 레퍼런스에서 `/ws/Main.asmx/GetKboGameList` 발견.
- 단일 엔드포인트가 게임ID + 팀코드 + 선발투수 ID/이름 + 구장 + 경기시각 + 취소/확정 플래그 전부 반환.
- `/ws/` robots carve-out 추가 (사용자 승인 2026-04-13).
- **smoke (실 데이터):** `date(2026,4,14)` → 5경기 5/5 확정.  
  `LOT(67539=나균안) @ LG(51111=송승기)`, `KT(64001=고영표) @ NC(56928=버하겐)`, `KW(64350=하영민) @ KIA(77637=양현종)` 등.
- A-2/A-3/A-7 해소, A-5/A-6 blocker → nice-to-have 강등.
- BeautifulSoup import 제거, `_fetch_starters` / `KBO_GAME_CENTER` 삭제.

### 세션 4 (2026-04-13) — Phase 4 + §A-5/A-6 + §C
- **Phase 4 완료:** API 라우터 6개 + Pydantic v2 응답 스키마 + `_helpers.py` 공유 헬퍼. `create_app()` 기동 시 `/api/today` 포함 15개 라우트 등록 확인.
  - `GET /api/today`, `/api/matchup/{id}`, `/api/pitcher/{id}`, `/api/history?date=`, `/api/accuracy`
  - `POST /admin/crawl-schedule`, `/admin/analyze-face/{id}`, `/admin/generate-fortune`, `/admin/calculate-matchups`, `/admin/update-result/{id}`
- **§A-5 완료:** `pitchers.kbo_player_id` + `daily_schedules.home/away_starter_kbo_id` 컬럼 추가. `match_pitcher_by_kbo_id()` 신규. `upsert_schedule()` kbo_id 저장. scheduler ID 우선 → name 폴백 매칭. `init_db.py` idempotent SQLite ALTER.
- **§A-6 부분완료:** `seed_pitchers.py` 에서 JSON `kbo_player_id` 필드 지원. 프로필 페이지 파싱 수확기는 ASMX 엔드포인트 검증 후 구현 예정(TODO 주석).
- **§C-1/C-2 완료:** `publish_matchups` `is_published.is_(False)` 필터, `_append_review` dedup.
- **code-reviewer 지적사항 처리:** `AXIS_ORDER` 단일 소스(`scoring_engine.py`), `MatchupSummary` disclaimer 설계 의도 주석, `init_db.py` dead import 제거.
- **미완:** §B (Claude API 실검증) — API 키 없어서 다음 세션으로 이월. Phase 5 (프론트) 미착수.
