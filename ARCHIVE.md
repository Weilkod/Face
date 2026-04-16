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

### 1-9. 스모크 테스트 ✅

`init_db.py` + `seed_pitchers.py` 연속 실행 → `data/facemetrics.db` 에 pitchers 10 row, 모든 프로필 사진 연결 완료.

---

## ✅ Phase 2 — AI 엔진 (완료: 2026-04-13, 실검증 2026-04-14)

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

### 2-3. face_analyzer (Claude Vision) ✅

**생성:** `backend/app/services/face_analyzer.py`
- `async def get_or_create_face_scores(session, pitcher, season=2026) -> FaceScore`
- 플로우: `(pitcher_id, season)` 캐시 히트 → 즉시 반환. 미스면 base64/url → Claude Vision → JSON 파싱 → `FaceAnalysisResult`.
- 실패 핸들링: 1차 실패 → `temperature=0` 재시도 → 2차 실패 → `hash_face_scores` 폴백.
- `profile_photo is None` → Claude 스킵, 경고 로그 + 폴백.
- 클라이언트는 지연 초기화 (`_get_client()`) — 모듈 임포트 시점에 API 키 없어도 폭발 X.
- `analyzed_at` 는 KST 타임스탬프.

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

### 2-6. scoring_engine (컴바이너) ✅

**생성:** `backend/app/services/scoring_engine.py`
- `AXIS_ORDER = ("command", "stuff", "composure", "dominance", "destiny")` — 전역 고정.
- 상성은 destiny 축에만 가산. destiny 총점 최대 24, 다른 축 최대 20.
- **Public API:** `async def score_matchup(...)` + `def score_matchup_from_raw(...)` (순수 동기, 캘리브레이션 전용).

### 2-7. 캘리브레이션 스모크 ✅

`score_matchup_from_raw` + `hash_fallback` 로 5 매치업 실행. 총점 분포 55~86, 홈 2승/원정 3승, 계통적 편향 없음.

### 2-8. 실 Claude API 검증 — 세션 8 (2026-04-14)

브랜치: `claude/session-8-ai-validation`.

- **B-1 캐시 미스→히트 경로 실검증.** `scripts/verify_ai_pipeline.py` 가 `pitcher_id=1,2` 의 profile_photo 를 manifest KBO URL 로 override 한 뒤 face/fortune 을 1회씩 실호출, 두번째 호출에서 캐시 히트(Claude 호출 0회)를 row count assertion 으로 검증. 4번의 실 Claude 호출(Vision×2 + Text×2) 모두 200 OK, 토큰 사용 로그 적재됨. `score_matchup()` 통합도 정상.
- **B-2 caller-managed transaction 으로 전환.** `face_analyzer.get_or_create_face_scores` / `fortune_generator.get_or_create_fortune_scores` 의 내부 `commit/refresh` → `flush` 로 교체. 호출자가 트랜잭션 경계 책임.
  - `scheduler.analyze_and_score_matchups` 의 외층 try/commit/rollback 이 매치업 1건을 진짜 atomic 하게 묶음 — face × 2 + fortune × 2 + matchup × 1 이 한 트랜잭션.
  - `admin.analyze_face` 와 `admin.generate_fortune` 에 명시적 `await session.commit()` / `rollback()` 추가 (generate_fortune 은 부분 성공 의미 보존 위해 per-iteration commit).
- **B-3 rollback 유닛 테스트** — `backend/tests/test_analyze_rollback.py` 3건:
  - `test_happy_path_persists_all_rows` — mock 으로 face/fortune 모두 성공 → face×2 + fortune×2 + matchup×1 검증.
  - `test_fortune_failure_rolls_back_face_rows` — face 성공 + Claude Text + hash fallback 모두 raise → 모든 행 0 (B-2 회귀 가드).
  - `test_face_failure_rolls_back_cleanly` — Claude Vision + hash fallback 모두 raise → 모든 행 0.
  - 실행: `pytest backend/tests/ -v` → 3 passed, 2.36s.
- **부수 산출물:** `backend/tests/conftest.py` (DATABASE_URL 임시 파일 주입), `scripts/verify_ai_pipeline.py` (재현 가능한 실 API 검증).

### 2-9. Phase 2 파일 맵

```
backend/app/
├── prompts/
│   ├── __init__.py
│   ├── face_analysis.txt
│   └── fortune_reading.txt
├── schemas/
│   ├── __init__.py
│   └── ai.py
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

### 3.1-1. 생성 파일

- `backend/app/schemas/crawler.py` — Pydantic v2 `ScheduleEntry`
- `backend/app/services/crawler.py` — 메인 크롤러 모듈
- `scripts/crawl_today.py` — CLI 드라이런 엔트리포인트

### 3.1-2. 크롤러 구조

**Public API:**
- `async def fetch_today_schedule(game_date: date) -> list[ScheduleEntry]`
- `async def match_pitcher_name(session, name, team) -> Optional[int]`

**최종 소스 구성:** KBO `GetKboGameList` 단일 소스 (네이버/스탯티즈는 세션 2에서 제거). `/ws/` robots carve-out 적용.

### 3.1-3. 드라이런 스모크

robots 차단 로깅 정상, 크래시 없음. "No games found" graceful.

### 3.1-4. 코드 리뷰 2라운드

주요 fix: `NAVER_TEAM_MAP` 중복 키, `follow_redirects=False`, `_RobotsBlocked` sentinel, cold-cache rate limit.

---

## ✅ Phase 3 sub-task 2 — DB write + Scheduler (완료: 2026-04-13)

### 3.2-1. `upsert_schedule()`

자연 키 `(game_date, home_team, away_team)`. null-safe (확정 선발 덮어쓰기 방지). mismatch → 리뷰 큐.

### 3.2-2. `backend/app/scheduler.py` — 5개 KST 크론 잡

| 시각 (KST) | 잡 | 역할 |
|---|---|---|
| 08:00 | `fetch_and_upsert_schedule` | 크롤 → upsert |
| 09:00 | `retry_missing_starters` | 선발 null 재크롤 |
| 10:00 | `retry_missing_starters` | 최종 재시도 |
| 10:30 | `analyze_and_score_matchups` | `score_matchup()` → matchups upsert |
| 11:00 | `publish_matchups` | `is_published = True` 플립 |

설계 포인트: per-game atomic 경계, Core Row 튜플 SELECT (MissingGreenlet 방지), `_wrap()` 예외 격리.

### 3.2-3. 검증 스모크

5개 잡 등록, upsert 4단계 테스트, null-safe 통과, mismatch → 리뷰 큐 확인. 실 데이터 smoke: `date(2026,4,14)` → 5경기 5/5 선발 확정 수신.

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

## ✅ Phase 4 — API 라우터 (완료: 2026-04-13, 세션 4)

커밋: `72a5803` + 코드리뷰 수정 `1ee88ce`

**GET 엔드포인트:**
- `/api/today` — 당일 매치업 리스트 (`TodayResponse { date, day_of_week, matchups[] }`)
- `/api/matchup/{id}` — 매치업 상세 (5축 점수 + 상성 + 승자)
- `/api/pitcher/{id}` — 투수 프로필 + face_scores + today_fortune
- `/api/history?date=YYYY-MM-DD` — 과거 매치업 + 실제 결과
- `/api/accuracy` — 적중률 통계

**POST 엔드포인트 (admin):**
- `/admin/crawl-schedule` — 수동 크롤 트리거
- `/admin/analyze-face/{id}` — face_scores 재생성
- `/admin/generate-fortune` — fortune_scores 생성
- `/admin/calculate-matchups` — matchup 점수 계산
- `/admin/update-result/{id}` — 실제 결과 업데이트

**구조:**
- `app/schemas/response.py` — Pydantic v2 응답 스키마
- `app/routers/_helpers.py` — 공유 `pitcher_summary()` 헬퍼
- `python -c "from app.main import app"` import OK 확인

---

## ✅ Phase 5 — 프론트엔드 초기 구축 (완료: 2026-04-13, 세션 4)

커밋: `1ee88ce`, `e846880`

- Next.js 14 App Router (`frontend/`) — `npm run build` clean
- Pages: `/` (TodayMatchups hero + accordion), `/history`, `/pitcher/[id]`
- Components: `MatchupCard`(아코디언), `RadarChart`(SVG 5축), `ScoreBar`, `AxisDetail`, `Footer`
- Mock data: 3개 매치업 (엔스/곽빈, 김광현/쿠에바스, 네일/페디)
- `src/lib/api.ts` USE_MOCK 플래그, `src/types/index.ts`
- Tailwind 커스텀 색상 `draft.html` 픽셀 매칭, bar-fill 애니메이션
- 레거시 `shine-border.tsx`, `timeline.tsx` 삭제

### 5-1. 후속 해소 — 세션 4/5 BLOCK

- **D-1~D-6** C1/C2/C3/I1/I6/C4/I3/I4/I5 — PR #1 + 후속 커밋으로 해소
- **D-4 (partial)** Tailwind 토큰화 — `tailwind.config.ts` 에 `ink.title: "#0A192F"` 토큰 신규 추가 후 `page.tsx:46` 리팩터 (세션 10, PR #9)
- **D-7** `PitcherProfile` 삭제 → `PitcherDetail` 통합 (세션 7, 프론트 어댑터 레이어)
- **D-8** 360px 모바일 뷰포트 smoke test — dev 서버 + 3 경로 200 + 정적 분석 + 사용자 로컬 DevTools 육안 검수 통과 (세션 7)
- **D-9** Share card PNG 생성 — `@vercel/og` Edge route + ShareButton (세션 5)

---

## ✅ Phase 6 — 배포 인프라 준비 (완료: 2026-04-13~14)

### 6-1. Alembic 마이그레이션 도입 (세션 5)

브랜치: `claude/add-alembic-vercel-og-rIYEo`

- `backend/alembic.ini`, `backend/alembic/env.py` (async `aiosqlite`/`asyncpg` 모두 지원)
- `backend/alembic/versions/0001_initial_schema.py` — Phase 4 스키마 그대로 5 테이블
- `requirements.txt` 에 `alembic==1.13.3` 추가
- `scripts/init_db.py` 가 `Base.metadata.create_all` → `command.upgrade(cfg, 'head')` 로 교체
- 검증: 신규 SQLite 에 `upgrade head` → `downgrade base` 라운드트립 OK, SQLAlchemy `Base.metadata` ↔ alembic 실제 컬럼 drift 0건
- SQLite 는 `render_as_batch=True` 로 향후 ALTER 안전, env.py 는 런타임에 `app.config.get_settings().database_url` 주입

### 6-2. 공유 카드 (@vercel/og) (세션 5)

브랜치: `claude/add-alembic-vercel-og-rIYEo`

- `@vercel/og` ^0.11.1 추가 (`frontend/package.json`)
- `frontend/src/app/api/og/matchup/[id]/route.tsx` — Edge Runtime, 1200×630 PNG
  - 쿼리스트링 only (`home/away/homeTotal/awayTotal/winner/...`)로 백엔드 round-trip 없이 edge 캐싱
  - `s-maxage=3600 stale-while-revalidate=86400` — 11:00 KST publish job 이후 점수가 frozen 이라 안전
  - 면책 푸터 ("엔터테인먼트 목적 · 베팅과 무관") CLAUDE.md §6 준수
- `frontend/src/components/ShareButton.tsx` — `buildShareUrl()` + 다운로드 핸들러
- `MatchupCard.tsx` 에 ShareButton 마운트, "공유 이미지 저장" 버튼
- 검증: `npm run build` clean — 새 라우트 `ƒ /api/og/matchup/[id]` Edge 로 등록

### 6-3. 사후 code-reviewer 집행 (세션 6)

브랜치: `claude/fix-post-hoc-review-98a36f3` · 커밋: `741fc34`

세션 5 가 `code-reviewer-gate.sh` stop hook 을 우회한 채로 commit/push 했기 때문에 (post-commit 이라 `git diff HEAD` clean → silent pass) 사후로 리뷰 게이트를 집행.

리뷰어 Verdict: **BLOCK** (Critical 1 / Important 2 / Nits 3) → 3건 수정:

- **R1 (Critical)** `scripts/seed_pitchers.py` — `Base.metadata.create_all` 제거. Alembic 단일 진실 원칙 복원, 선행 요구사항 (`init_db.py` 먼저) docstring 에 명시, 미사용 `Base` import 삭제.
- **R2 (Important)** `backend/alembic/versions/0001_initial_schema.py` — pitchers `updated_at` 에 `onupdate=sa.func.now()` 추가. `app/models/pitcher.py:28` 와 metadata drift 해소 (ORM hook 이라 DDL 변화 0, autogenerate 재실행 시 잡음 제거).
- **R3 (Important)** `frontend/src/app/api/og/matchup/[id]/route.tsx` — `paramInt(req, key, fallback, {min, max})` 로 시그니처 확장 후 `homeTotal`/`awayTotal` 에 `{min: 0, max: 100}` 적용. `?homeTotal=99999999` 같은 악의적 URL 이 OG 카드에 7자리 숫자 분사하는 브랜드 오염 차단.

검증: `ast.parse` OK, `npx tsc --noEmit` clean, `paramInt` 호출자 2건 모두 신 시그니처로 업데이트됨 확인.

### 6-4. 배포 스켈레톤 도입 (세션 9)

브랜치: `claude/session-9-phase6-deploy`

- `backend/Dockerfile` — `python:3.12-slim` + tini, non-root(uid 1000), `PYTHONPATH=/app/backend`, 엔트리가 `scripts/init_db.py`(alembic upgrade head) 후 uvicorn 기동. 이미지에 `.env` 미포함(런타임 env vars 만 의존).
- `frontend/Dockerfile` — node 20-alpine 멀티스테이지(deps → builder → runner), non-root, `next start -H 0.0.0.0`. 주 배포 타깃은 Vercel 이라 이 파일은 로컬 compose 용.
- `docker-compose.yml` — backend(8000) + frontend(3000), `./data:/app/data` 바인드 마운트로 sqlite 퍼시스트, `DATABASE_URL` 절대경로 주입(`sqlite+aiosqlite:////app/data/facemetrics.db`), `env_file.required=false` 로 `.env` 미존재 허용.
- `.dockerignore` — 루트 단일 파일. `.venv`/`node_modules`/`.next`/`data/*.db`/`**/.env`/docs 제외.
- `.github/workflows/ci.yml` — PR + main push 트리거, concurrency cancel-in-progress. backend job: py 3.12, pip cache, alembic upgrade, import smoke, `pytest backend/tests -v`. frontend job: node 20, npm cache, `npm run type-check`, `npm run build`.

**code-reviewer 라운드:** APPROVE WITH FIXES (Critical 0 / Important 4 / Nits 6). 커밋 전 반영:

- **I1 CI DATABASE_URL 스코핑** — workflow-level env 에서 제거하고 alembic 스텝에만 `${{ github.workspace }}/data/facemetrics.db` 절대경로 주입. pytest 는 `backend/tests/conftest.py:26` 가 임시 파일을 무조건 덮어쓰므로 workflow env 오염 위험 차단.
- **I4 Next standalone output** — `next.config.mjs` 에 `output: 'standalone'` 추가, `frontend/Dockerfile` runner 스테이지를 `.next/standalone` + `.next/static` + `public` 만 복사하도록 축소 (이미지 ~500MB → ~150MB 수준). CMD 도 `node server.js` 로 변경.
- **N2 tini 신호 전파** — `ENTRYPOINT ["tini", "-g", "--"]` (프로세스 그룹에 신호 전달) + CMD 의 uvicorn 앞에 `exec` 추가. `docker stop` 시 SIGTERM 이 uvicorn 까지 즉시 도달.

**이월 (세션 10~11 처리):**

- **I2 bind-mount uid 불일치** — `./data:/app/data` + uid 1000 non-root. Linux 호스트의 실 유저 uid 가 1000 이 아니면 sqlite write EACCES. compose smoke 실행 전 `sudo chown -R 1000 ./data` 또는 `docker compose run --user $(id -u)` 안내 필요. (Wave 4 Track I 에서 적용)
- **I3 APScheduler 싱글톤** — 세션 11 에서 `SCHEDULER_ENABLED` 플래그로 해결 (아래 §세션 11).
- **N1 compose 버전 요구사항** — `env_file.path/required` long-form 은 Compose v2.24+ (Jan 2024). 구버전은 파싱 실패.

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
- A-2/A-3/A-7 해소, A-5/A-6 blocker → nice-to-have 강등.
- BeautifulSoup import 제거, `_fetch_starters` / `KBO_GAME_CENTER` 삭제.

### 세션 4 (2026-04-13)
Phase 4 (API 라우터) + Phase 5 (프론트엔드 초기) 완료. 커밋 `72a5803`, `1ee88ce`, `e846880`.

### 세션 5 (2026-04-13)
Phase 6 sub-task 1 (Alembic) + sub-task 2 (@vercel/og 공유 카드) 완료. 브랜치 `claude/add-alembic-vercel-og-rIYEo`. stop hook 우회 이슈 → 세션 6 사후 리뷰.

### 세션 6 (2026-04-13)
Phase 6 sub-task 3 — commit `98a36f3` 사후 code-reviewer. BLOCK 3건 (R1/R2/R3) 수정 후 `741fc34`.

### 세션 7 (참고)
- PR #4/#5 (`claude/session-7-nits-and-d7`) — N1(matchup model `server_default=text("0")`) + N2(init_db URL 중복 주입 제거) + N3(ScoreBar maxScore 미사용 prop 제거) / D-7(PitcherProfile 통합) / D-8(360px smoke) / alembic.ini cp949 fix.

### 세션 8 (2026-04-14)
Phase 2 실 Claude 검증. B-1/B-2/B-3 (위 §2-8 참조).

### 세션 9 (2026-04-14)
Phase 6 sub-task 4 — 배포 스켈레톤 (위 §6-4 참조).

### 세션 10 (2026-04-14)
PR #7/#8/#9/#10/#11 연속 처리:

- **PR #7 merged** — Phase 6 배포 스켈레톤 main 반영 (CI green, main `6fe541e`).
- **H1 Stop hook 보강 (PR #8 merged)** — `.claude/hooks/code-reviewer-gate.sh` 가 `git diff --name-only origin/main...HEAD` 브랜치-레벨 diff 로 post-commit silent-pass 차단. 마커 포맷 `<contenthash>@<shortsha>`. 3단 fallback (origin/main → HEAD~1 → no-op), deleted-path sentinel 처리. 5 케이스 수동 테스트 통과. H2 는 embedded SHA 로 기능 대체됐다고 판단 — 정식 deferred.
- **D-4 Tailwind 토큰화 (PR #9 merged)** — `tailwind.config.ts` 에 `ink.title: "#0A192F"` 토큰을 **신규 추가** 후 `page.tsx:46` `text-[#0A192F]` → `text-ink-title` 리팩터. `frontend/preview/draft.html` 이 디자인 소스로 동일 색을 쓰고 있어 시각 변화 0.
- **A-5 KBO playerId 매처 (PR #10 merged)** — `pitchers.kbo_player_id` (unique nullable int, indexed) + `daily_schedules.home/away_starter_kbo_id` (nullable int) 컬럼. Alembic `0002_add_kbo_player_id.py` (batch mode, roundtrip clean). `services/crawler.match_pitcher_by_kbo_id()` 헬퍼 (signature `Optional[int]`). `scheduler._resolve_pitcher_id()` 가 id-first → name-fallback + 성공 시 pitcher 로우에 kbo_id write-back ("crawl 에서 학습"). `upsert_schedule` 도 fill-blank 정책으로 kbo_id 저장. 유닛 테스트 9건 → pytest 12/12 통과.
- **A-5 code-reviewer 라운드**: APPROVE WITH FIXES (Critical 1 / Important 1 / Nits 2):
  - **Critical — write-back transaction leak**: `_resolve_pitcher_id` 호출이 `try:` 블록 바깥에 있어서 lazy write-back 이 현재 게임의 원자 트랜잭션 경계에 포함되지 않았음. 수정: 전체 resolve→score→upsert→commit 을 하나의 try 로 묶고 skip 분기도 rollback 선행.
  - **Important — type annotation drift**: `match_pitcher_by_kbo_id(kbo_player_id: int)` 가 body 에서 `None` 을 가드하고 있었음 → `Optional[int]` 로 수정, 직접 None 입력 케이스 테스트 추가.
  - **Coverage gap — upsert fill-blank**: `upsert_schedule` 의 kbo_id fill-blank / no-overwrite 분기가 테스트 0건이었음 → 3개 테스트 추가.
- **외부 리뷰 대응 (PR #11 merged, main `14c7e20`)** — 다른 세션의 code-reviewer 가 A-5 에 대해 Critical 2 / Important 2 / Nit 3 으로 BLOCK 의견을 냈으나, 각 항목을 현재 main 에 대조한 결과 유효한 건 **N3 (로그 레벨) 만 1건**. 나머지는 stale 또는 false positive:
  - **C1 srId 값** (Critical) — `crawler.py:266` `"srId": "0,1,3,4,5,7"` vs CLAUDE.md §5 스펙 `0,9,6` 불일치. 유효하지만 라이브 검증 필요 → 세션 11 로 이월.
  - **C2 write-back rollback** (Critical) — 버그 아닌 의도된 trade-off. `daily_schedules.home_starter_kbo_id` 는 upsert_schedule 에서 별도 commit 되어 DB 에 남아있으므로 다음 스케줄러 런이 같은 row 를 재읽고 재시도 → "학습 지연" 이지 "학습 소실" 이 아님.
  - **I1 인덱스 중복 선언** (Important) — 실측 반증. 모델 `unique=True, index=True` 로 `Base.metadata.create_all` 결과가 alembic 0002 의 `create_index(..., unique=True)` 와 완전히 동일한 DDL 생성.
  - **I2 타입 어노테이션 / N1 existing_owner / N2 dead code guard** — 모두 PR #10 fix commit 에서 이미 해소된 stale.
  - **N3 로그 레벨** (유효) — `scheduler.py:156` `logger.info` → `logger.debug`. PR #11 로 별도 처리.

### 세션 11 (2026-04-15)

브랜치: `claude/session-11-a7-i3`, PR #12 merged (커밋 `74036f8`).

- **A-7 srId 라이브 검증 완료** — `scripts/verify_srid.py` 로 `2026-04-15` 날짜에 세 변종(`0,1,3,4,5,7` / `0,9,6` / `0`)을 실 KBO `POST /ws/Main.asmx/GetKboGameList` 에 병렬 호출. 세 응답 모두 **5경기 동일**, 모든 게임 `SR_ID=0` / `LE_ID=1` (정규시즌 1군). 결론: 정규시즌 기간 `srId` 필터는 실질 no-op. **CLAUDE.md §5 를 코드값(`0,1,3,4,5,7`)에 맞춰 정정** (옵션 B). `srId` 의 series-type 매핑 (0=정규, 1=시범, 3/4/5=포스트, 7=올스타) 주석으로 기록. 포스트시즌/시범경기 기간 차이는 이번 검증에서 관측 불가.

- **I3 APScheduler 싱글톤 가드 완료** — `app/config.py` 에 `scheduler_enabled: bool = True` 필드 추가 (pydantic-settings 가 `SCHEDULER_ENABLED` 환경변수로 자동 매핑). `app/main.py:lifespan` 이 `settings.scheduler_enabled` 가 True 일 때만 `build_scheduler().start()` 를 호출하고, False 면 INFO 로그만 찍고 skip. finally 블록도 `scheduler is not None` 가드 후 shutdown. Admin 라우터는 스케줄러 인스턴스에 의존하지 않고 `app.scheduler` 모듈의 job 콜러블을 직접 import 하므로 (`crawl_schedule_job`, `analyze_and_score_matchups`, `publish_matchups`), 웹 파드가 scheduler 를 끈 상태에서도 `/admin/*` 수동 트리거는 정상 동작. 

  **배포 런북 (Phase 6 Railway/Fly 적용 시 필수)** — 멀티 레플리카에서 크론 중복 실행 방지 원칙:
  - **웹 서비스 (replicas ≥ 1)**: `SCHEDULER_ENABLED=false`. 트래픽을 받는 모든 인스턴스.
  - **워커 프로세스 (replicas=1 고정)**: `SCHEDULER_ENABLED=true`. 크롤/분석/퍼블리시 5 잡 실행 전용. 수평 확장 금지 — 두 개 띄우면 `fortune_scores` 중복 write + Claude 토큰 2배 소모 재발.
  - dev/staging 단일 프로세스 구성은 기본값(`true`) 유지, 명시 설정 불필요.
  - Railway 의 경우 별도 Service 로 워커 분리 권장, Fly 는 `[processes]` 블록으로 `app`/`worker` 분리.

- **세션 11 병렬 중복 작업 (PR #26, #27 closed)** — 같은 시점 다른 세션이 동일 작업을 수행 중인 상황에서 이 세션의 로컬 브랜치가 A-7 반대 방향(옵션 A, 코드→스펙) + I3 `app.state.scheduler` 스타일로 PR 분리 제출(PR #26/27)했으나, main 이 이미 옵션 B + 로컬 변수 스타일로 머지된 상태 → conflict. PR #26, #27 둘 다 close 처리, 원격/로컬 브랜치 삭제. 기능적 중복이라 지장 없음 확인.

### 세션 12 (2026-04-15)

브랜치: `claude/session-12-a6-harvester` (origin/main 95d0873 기반 — 세션 11 PR 미머지 상태에서 병렬 착수), PR #13 merged.

- **A-6 eager KBO 프로필 수확기 완료** — `seed_pitchers.py` 가 시드 직후 koreabaseball.com 을 호출해 신규 시드 투수의 `pitcher.kbo_player_id` (+ 비어있으면 `profile_photo` CDN URL) 를 즉시 채운다. A-5 의 lazy write-back 은 "다음 스케줄러 런에서 학습" 이지만 이건 "시드 즉시 학습" — 새 시드 투수의 freshness 0 구간을 없앤다.

  - **엔드포인트 재발견**: 기존 `scripts/crawl_pitcher_images.py:184` 의 `kbo_search_player` 가 이미 `POST /Player/Search.aspx` (ASP.NET VIEWSTATE 폼) → `PitcherDetail` 링크 parse → 프로필 이미지 URL 추출 전체 체인을 sync 로 검증 완료. 이 모듈은 그 async 쌍둥이.
  - **새 파일**: `backend/app/services/kbo_profile_harvester.py` — `HarvestResult(kbo_player_id, profile_photo_url)` dataclass + `harvest_profile(client, name, team)` 퍼블릭 API + `harvest_profile_standalone(name, team)` 편의 래퍼. `crawler._make_client` / `DEFAULT_HEADERS` / `GET_HEADER_OVERRIDE` / `RATE_LIMIT_S` / `_robots_allows` 전부 재사용. `/Player/Search.aspx` 와 `PitcherDetail` 페이지는 `/ws/` carve-out 바깥이라 표준 robots 체크를 통과.
  - **`seed_pitchers.py` 통합**: argparse 플래그 3개 추가 (`--harvest` opt-in, `--dry-run` 롤백, `--pitcher-id N` 디버그 필터). 기본 실행은 기존 동작 그대로 — 회귀 0. harvest 패스는 JSON upsert 직후 단일 `session.flush()` 뒤에 돌고, 루프 종료 후 단일 `commit()` (dry-run 시 `rollback()`).
  - **유닛 테스트 9건** (`backend/tests/test_profile_harvester.py`): happy path / retired-pitcher fallback / ambiguous multi-hit + warning / no candidates / search GET 에러 / detail GET 에러 (id 는 여전히 수확) / detail 이미지 누락 / __VIEWSTATE 누락 / 빈 이름 (HTTP 0회). autouse fixture 로 `_robots_allows` + `asyncio.sleep` 몽키패치하여 오프라인 실행.
  - **실 KBO smoke (2026-04-15)**: `python scripts/seed_pitchers.py --harvest` → **10/10 hit** (원태인 69446 / 곽빈 68220 / 네일 54640 / 카스타노 54920 / 손주영 67143 / 박세웅 64021 / 임찬규 61101 / 문동주 52701 / 양현종 77637 / 하트 54930). 소요 ≈ 40초 (10 × 4 HTTP 콜 × 1초 rate limit). 2차 실행은 전부 `skipped` — 멱등성 확인. `--dry-run --pitcher-id 1` 로 NULL→수확→롤백 경로도 수동 검증 (post-rollback row 여전히 NULL).
  - **photo_filled=0**: 10명 모두 manifest 로컬 경로 (`data/pitcher_images/kbo/NN_...jpg`) 가 이미 `profile_photo` 에 박혀있어 harvester 가 덮어쓰지 않음 — 세션 8 B-1 이 이 로컬 파일 기반으로 Claude Vision 검증한 상태를 보존.
  - **검증 체크리스트**: `pytest backend/tests -v` → 21/21 통과. import smoke OK. alembic upgrade head clean.
  - **포스트시즌 재검증 여지**: KBO 검색 페이지의 ASP.NET 컨트롤 경로 (`ctl00$ctl00$ctl00$cphContents$...`) 가 시즌 전환 / 페이지 리뉴얼 시 변할 수 있음 — harvester 는 `__VIEWSTATE` / `btnSearch` 필드 누락 시 None 반환하므로 fail-soft 지만 다음 신규 시드 사이클에서 hit rate 모니터링 권장.

---

## ULTRAPLAN — Phase 7: FE↔BE 통합 & 런치

> **작성일:** 2026-04-16 · **기준:** main `981f19a` (세션 11+12 머지 완료)
> **목표:** mock 데이터 제거 → 실 백엔드 연동 → 배포까지 최단 경로.
> 4 Wave 구성. Wave 내 Track 은 완전 병렬, Wave 간만 의존성.

### 시작 시점 GAP 분석 — FE↔BE 스키마 불일치 (Critical)

FE 가 mock 데이터로만 동작해서 실 API 연결 시 **4곳에서 런타임 에러** 발생.

| # | 엔드포인트 | FE 기대 | BE 실제 | 수정 방향 |
|---|-----------|---------|---------|-----------|
| **G1** | `GET /api/today` | `MatchupSummary[]` (flat array) | `TodayResponse { date, day_of_week, matchups[] }` | FE `getTodayMatchups()` 가 `.matchups` 를 unwrap |
| **G2** | `GET /api/matchup/{id}` | `MatchupDetail extends MatchupSummary` → `home_total`, `away_total`, `chemistry_score`, `game_time`, `series_label` 필수 | BE `MatchupDetail` 에 해당 필드 없음 | BE 스키마에 5개 필드 추가 + 라우터 매핑 |
| **G3** | `GET /api/history` | `HistoryMatchup extends MatchupSummary` → `actual_winner`, `prediction_correct`, `game_date` 추가 | BE `HistoryResponse.matchups` 가 `list[MatchupSummary]` (추가 필드 0) | BE 에 `HistoryMatchup` 스키마 신설, 라우터에서 `actual_winner`/`prediction_correct` 매핑 |
| **G4** | `GET /api/accuracy` | `AccuracyStats.recent_7_days?` (optional) | BE `AccuracyResponse.recent_7_days` (required) | BE 를 `Optional` 로 완화 |

### 에이전트 배정표 (병렬 실행 맵)

```
WAVE 1 (병렬 4)
 ├─ [fastapi-backend-dev]  Track A: BE 스키마 G2/G3/G4 + C-2
 ├─ [react-ui-dev]         Track B: FE api.ts G1 + types 정합
 ├─ [kbo-data-crawler]     Track C: 2026-04-16 라이브 크롤 smoke
 └─ [fortune-domain-expert] Track D: 상성 로직 감사

          ↓ (Wave 1 전체 완료)

WAVE 2 (병렬 2)
 ├─ [react-ui-dev]         Track E: FE 실 데이터 연동 + 360px 검증
 └─ [fastapi-backend-dev]  Track F: C-1 review queue (Track C 결과 반영)

          ↓ (Wave 2 전체 완료)

WAVE 3 (병렬 2)
 ├─ [general]              Track G: E2E pipeline 풀 테스트
 └─ [code-reviewer]        Track H: 전체 diff 리뷰

          ↓ (Wave 3 전체 완료)

WAVE 4 (순차)
 └─ [general]              Track I: Docker → Railway → Vercel → 면책 확인
```

### Critical Path
`Track A (BE 스키마) → Track E (FE 연동) → Track G (E2E) → Track I (배포)` — 전체 일정 결정자. B/C/D 는 A 와 병렬이라 추가 시간 0. F 는 비차단.

### Wave 1 실행 결과 (2026-04-16)

| Track | PR | 상태 | 요약 |
|------|----|------|------|
| **A** (BE 스키마) | #16 머지 (`3bc87e2`) | ✅ | `MatchupDetail` 5 필드 + `HistoryMatchup` 신설 + `accuracy.recent_7_days` Optional + `publish_matchups` `is_published.is_(False)` 필터 |
| **B** (FE api.ts) | #15 머지 (`8e687fa`) | ✅ | `getTodayMatchups()` → `TodayResponse.matchups` unwrap (G1) |
| **C** (크롤 smoke) | #17 OPEN | ⚠️ **FAIL (인프라)** | WAF IP-allowlist 블록, 코드 이슈 0건. 아래 상세 참조. |
| **D** (상성 감사) | #18 머지 (`bdff790`) | ✅ | `chemistry_calculator` 엣지 케이스 테스트 추가, README §2~3 정합 확인 |

#### Track C 상세 — 크롤러 smoke FAIL

브랜치: `claude/wave1-track-c-crawl-smoke-U81pk` (코드 수정 0건, PROGRESS.md 기록만).

**판정: FAIL — WAF IP-allowlist 블록, 애플리케이션 레벨 이슈 아님.**

- `scripts/crawl_today.py --date 2026-04-16` dry-run → `fetch_today_schedule` 0 entries 반환.
- 실 HTTP 응답: `POST /ws/Main.asmx/GetKboGameList` → `403 Forbidden`, 21바이트, body `Host not in allowlist`, response header `x-deny-reason: host_not_allowed`. CDN/WAF 엣지에서 샌드박스 아웃바운드 IP 를 드롭.
- httpx DEBUG 트레이스로 확인한 요청 헤더는 전부 스펙 일치. 403 은 헤더 값과 무관하게 IP 기반 거부.
- 로컬 DB 초기화는 정상: `python scripts/init_db.py` (alembic 0001+0002 upgrade head clean), `python scripts/seed_pitchers.py` (10명 시드).
- `crawler.py` 의 `_fetch_kbo` 는 `raise_for_status` 를 잡아서 `[]` 로 fail-soft — 기대 동작. 파서/셀렉터/레이트리밋 이슈 0건.

**매칭률**: 0/0 경기 선발 확정 · 0/0 pitcher_id 매칭 · 0/0 kbo_id 저장 (크롤 자체가 실패해 측정 불가).

**언블록 옵션** (세션 외부 인프라):
1. 한국/미국 잔여 리전 residential/VPS IP 에서 재실행 (PROGRESS.md §세션 3, 세션 11 `verify_srid.py` 는 그 환경에서 200 OK 받은 바 있음).
2. CLAUDE.md §5 가 허용하는 유일한 out-of-band 경로인 **Playwright headless** fallback 활성화. 현재 `crawler.py` 에 스캐폴딩 없음.
3. 경량: 수동 fixture — `backend/tests/fixtures/kbo_20260416.xml` 샘플 응답을 저장해두고 파서 회귀 전용 오프라인 테스트 유지.

#### Track D 상세 — 상성 감사

브랜치: `claude/wave1-track-d-chemistry-audit-HAQ7G`.

- **감사 범위**: `backend/app/services/chemistry_calculator.py` + `data/zodiac_compatibility.json` + `data/constellation_elements.json` 을 README §2-3 표/수식에 한 줄 단위로 대조.
- **Verdict: PASS — 코드 수정 없음.** 모든 테이블/계수/클램프가 스펙과 일치.
  - 삼합(+2) 4 그룹 — 자-진-신, 축-사-유, 인-오-술, 묘-미-해 ✅
  - 육합(+1.5) 6 페어 — 자-축, 인-해, 묘-술, 진-유, 사-신, 오-미 ✅
  - 원진(-1.5) 6 페어 — 자-미, 축-오, 인-사, 묘-진, 신-해, 유-술 ✅
  - 충(-2) 6 페어 — 자-오, 축-미, 인-신, 묘-유, 진-술, 사-해 ✅
  - 별자리 원소 — 동질 +1 / 상생(불-바람·물-흙) +1.5 / 상극(불-물·바람-흙) -1 / 중립 0 ✅
  - 기본 2점 + 합산 → clamp[0, 4] (JSON `_meta.base_score` / `_meta.clamp_range` 에서 로드) ✅
  - 모든 페어가 단일 규칙에만 소속 — 규칙 우선순위 충돌 부재 (수동 검증 완료).
- **엣지 케이스 테스트 추가** (`backend/tests/test_chemistry_calculator.py`, 96 테스트): 12 삼합 × 6 육합 × 6 원진 × 6 충 / 동일 띠 전수 / 원진+상극, 충+상극 clamp 0 / 삼합+상생 clamp 4 / 경계 landing / 알 수 없는 입력 ValueError / 공백 정규화 / swap 대칭성 / JSON 스펙 가드.
- **code-reviewer 라운드** (APPROVE WITH FIXES, Critical 0 / Important 2 / Nit 1) — 전부 반영:
  - **I1 중립 원소 커버리지** — 불-흙 만 검증 중, 바람-물 방향 미커버. `NEUTRAL_ELEMENT_PAIRS` 로 parametrize.
  - **I2 private helper 의존성 문서화** — 모듈 docstring 에 `_load_zodiac_data` / `_load_constellation_data` 가 이름 바뀌면 테스트도 따라가야 함을 명시.
  - **N1 ceiling 코멘트 명확화** — "exact ceiling, not over-clamped" 주석.
- **검증**: `pytest backend/tests -v` → 117 passed (기존 21 + 신규 96).

### Wave 2 실행 결과 (2026-04-16)

#### Track E — FE 실 데이터 연동 (react-ui-dev)

브랜치: `claude/wave2-track-e-fe-live-integration-a4a6a3dc`, 커밋 `d791b5b`.

| 항목 | 결과 |
|------|------|
| `USE_MOCK=false` 전환 | ✅ `.env.local` + `.env.example` 신설 |
| DB init + seed | ✅ `init_db.py` → `seed_pitchers.py` → `create_sample_matchup.py` (2경기 삽입) |
| `/api/today` 응답 | ✅ 2개 matchup 반환 |
| `/api/matchup/1` 응답 | ✅ 5축 점수 + chemistry + game_time="18:30" |
| `/api/pitcher/1` 응답 | ✅ face_scores + today_fortune (hash fallback 정상) |
| `/api/history?date=2026-04-16` | ✅ 2개 matchup 반환 |
| `npm run type-check` / `npm run build` | ✅ clean (각 2회) |
| `/` `/history` `/pitcher/1` 렌더 | ✅ 원태인/곽빈/손주영/양현종 카드 + 적중률 통계 + 레이더 차트 |
| Footer 면책 고지 (3 페이지) | ✅ "엔터테인먼트 목적" 모든 페이지 확인 |
| Empty state (홈/히스토리) | ✅ 메시지 + "과거 매치업 보기" 링크 |
| API 실패 에러 배너 + 재시도 | ✅ `ErrorBanner` 컴포넌트 + "다시 시도" reload |
| Mock 모드 경로 보존 | ✅ `USE_MOCK=true` 기존 동작 그대로 |

**주요 변경 파일:**

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/.env.local`, `frontend/.env.example` | 신설: `NEXT_PUBLIC_USE_MOCK=false` + `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `frontend/src/lib/api.ts` | `fetchJson` 네트워크 오류를 `"fetch failed: ..."` 로 감싸서 throw |
| `frontend/src/components/ErrorBanner.tsx` | 신설: 배너 + reload 버튼, `isApiDown` prop 으로 메시지 분기 |
| `frontend/src/app/page.tsx`, `/pitcher/[id]/page.tsx`, `/history/page.tsx` | `ErrorBanner` 연동, Empty state 추가 |
| `frontend/src/components/MatchupCard.tsx` | `fetchDetail()` 분리 + 에러 시 "다시 시도" 버튼 |
| `scripts/create_sample_matchup.py` | 신설: hash fallback 으로 face/fortune/schedule/matchup row 2쌍 삽입 |

**code-reviewer 라운드**: APPROVE — Critical 0, Important 0, Nits 1 (raw error 메시지 노출 → `isApiDown=true` 시 "데이터 서버에 연결할 수 없습니다." 로 대체).

**미해결 이슈:**
- `game_time null` — `/api/today` summary 에는 무방, 상세에서 정상 노출.
- `chemistry.zodiac_detail/element_detail null` — DB 컬럼 미존재. Wave 3 Track A에서 Matchup 모델 확장 시 추가 가능.
- hash fallback text 가 "(폴백) 해시 기반 근사치" 로 표시 — 실 Claude 연동 후 갱신 필요.
- 360px 모바일 DevTools — 자동화 없어 수동 확인 불가. `ErrorBanner` 에 `min-h-[44px]` 터치 타깃 적용.

#### Track E — `chem_score 이중 가산` False Alarm 판정

Track E 커밋 `d791b5b` 에 대한 parent-session pre-commit code-reviewer 가 `scripts/create_sample_matchup.py:188-193` 의 `home_total`/`away_total` 계산을 "chem_score 이중 가산, 100점 초과 가능" Critical 로 지정. 직접 대조 + `fortune-domain-expert` 독립 검증 결과 **대수적 동등 — false alarm 으로 판정**.

**수식 대조:**

| 경로 | 파일:라인 | 수식 |
|------|----------|------|
| 프로덕션 | `backend/app/services/scoring_engine.py:101, 107, 227` | `home_total = Σ_i (face_i + fortune_i + [chem_final if i=="destiny" else 0])` |
| Track E 스크립트 | `scripts/create_sample_matchup.py:190-193` | `home_total = Σ_i (face_i + fortune_i) + chem_score` |

두 식 모두 grand total 에 chem 이 **정확히 1회** 합산. reviewer 가 `+ chem_score` 를 `sum(...)` **내부** 로 오독한 것으로 추정.

**fortune-domain-expert Verdict**: EQUIVALENT (총점 산출 기준). 반례 없음. 100점 초과 가능성 (destiny 최대 24 + 4축 최대 80 = 104) 은 프로덕션 수식에서도 동일 — spec 이 chemistry 자체만 `[0, 4]` clamp 하고 총점 전체 clamp 를 규정하지 않으므로 Track E 단독 버그 아님.

**같은 브리프에서 발견된 별개 구조적 차이 (Critical 아님, 후속 과제 P-1):**

`predicted_winner` 반환 타입/값 도메인 차이.
- 프로덕션 (`scoring_engine.py:159-172`): `predicted_winner` ∈ `{"home", "away", "tie"}` (3-valued enum).
- Track E (`scripts/create_sample_matchup.py:201-206`): `home.name | away.name | None`. Korean pitcher name 을 그대로 저장.
- 현재 시점 런타임 크래시 없음 (`actual_winner.isnot(None)` 필터 덕분) 이나 스키마 의미 위반. FE 가 `"home"/"away"` 기반 UI 표시용으로 쓴다면 Track E 샘플에서 해당 UI 이상동작 가능.

#### Track F v2 — C-1 Review Queue Harden (fastapi-backend-dev)

브랜치: `claude/wave2-track-f-review-queue-v2`. PR #22 (최초) 는 agent worktree stale base 문제로 close, `v2` 로 재작업.

**저장소 결정: JSON 파일 유지.** DB 테이블 신설 없이 기존 `data/crawler_review_queue.json` 파일 유지.
- 읽기/쓰기 빈도 극저 (크롤러 실패 시만 append, 관리자 조회 시만 read)
- Alembic 마이그레이션 불필요 → 운영 복잡도 최소화
- 동시성 위험 있으나 08:00 crawl_job 이 단일 프로세스 내 순차 실행 — 현재 트래픽 수준에서 허용 가능

**Dedup 키 정의:** `(team, crawled_name, game_date, kbo_player_id)` — `crawled_name` 이 None 일 때만 `kbo_player_id` 포함. 중복 감지 시: 새 row 추가 금지, 기존 row 의 `created_at` 만 갱신.

**TTL 정책:** `resolved=True` + `resolved_at` 이 24시간 이전인 엔트리. `_append_review()` 호출 시 lazy eviction. `resolved=False` 엔트리는 운영자 개입 필요하므로 절대 삭제 금지.

**스키마 확장 (기존 호출자 호환):** `_append_review(entry, *, path=None)` 내부에서 기본값 stamp:
- `created_at`: ISO8601 UTC (최초 진입 시)
- `resolved`: False
- `resolved_at`: None

기존 caller (`match_pitcher_name`) 에서 `queued_at` 필드 제거, `date` → `game_date` 키 이름 통일.

**엔드포인트 사양:**

| 메서드 | 경로 | 쿼리/바디 | 응답 |
|--------|------|-----------|------|
| GET | `/admin/review-queue` | `?unresolved_only=bool&limit=int` | `list[ReviewQueueItem]` |
| POST | `/admin/review-queue/resolve` | `ReviewQueueResolveRequest` (JSON body) | `ReviewQueueItem` (200) or 404 |

인증: 없음 — 기존 admin 라우터 컨벤션 동일 (네트워크/프록시 레이어 위임).

**테스트 커버리지 (22 건):**

- `TestAppendReview`: happy / schema stamp / dedup / dedup refresh / 다른 game_date 분리 / kbo_player_id 키 / TTL 오래된 resolved 제거 / TTL 최근 resolved 유지 / TTL unresolved 절대 유지 (9건)
- `TestReviewEntryKey`: primary key / kbo_player_id 포함 조건 / 이름 있을 때 id 무시 (3건)
- `TestTtlEvict`: 오래된 resolved 제거 / 최근 resolved 유지 / unresolved 유지 (3건)
- `TestAdminGetReviewQueue`: unresolved_only 필터 / 전체 / limit cap (3건)
- `TestAdminResolveEndpoint`: 성공 / 404 / kbo_player_id 경로 / ASGI 통합 smoke (4건)

fixtures 은 `tmp_path` 로 격리, 실 `data/crawler_review_queue.json` 무오염.

**변경 파일 (main 기준 add-only):**
- `.gitignore` — `data/crawler_review_queue.json` 추가
- `backend/app/services/crawler.py` — `_review_entry_key`, `_ttl_evict` 추가 + `_append_review` dedup/TTL/path-override 확장 + caller 엔트리에서 `queued_at` 제거 + `date` → `game_date` 통일
- `backend/app/schemas/response.py` — `ReviewQueueItem`, `ReviewQueueResolveRequest` 신설 (기존 Track A 스키마 유지)
- `backend/app/routers/admin.py` — `/admin/review-queue` GET + `/admin/review-queue/resolve` POST 추가 (기존 Phase 4 admin 라우트 5개 유지)
- `backend/tests/test_review_queue.py` — 22 테스트 신설

**미구현 (의도적 미포함):**
- `_append_review` 동시성 안전 (fcntl lock / DB 승격) — 08:00 cron 단일 프로세스 내 순차라 현재 수용 가능. Postgres 전환 시 재검토.
- Alembic 마이그레이션 — JSON 유지 결정으로 불필요.
- 생산 환경 인증 (auth guard) — 프록시/네트워크 레이어 위임, 기존 admin 컨벤션 유지.

---

## 구조적 개선 현황

- [x] **H1** `.claude/hooks/code-reviewer-gate.sh` 가 `git diff --name-only origin/main...HEAD` 브랜치-레벨 diff 로 post-commit silent-pass 차단. 마커 `<contenthash>@<shortsha>` 포함 (PR #8, 세션 10).
- [ ] **H2** "세션 마지막 턴이 git commit/push 를 포함하면 code-reviewer 호출" — H1 마커에 SHA 가 embed 돼서 같은 커밋이 두 번 리뷰되지 않는 효과를 얻었으므로 정식 deferred (재도입 시 검토).
