# FACEMETRICS — Implementation Progress

> **자동 아카이브 지침:**  
> 완료된 Phase 섹션이 **다음 Phase 착수 후** 또는 **2주 이상 경과** 했을 때,  
> 세부 구현 내역은 `ARCHIVE.md` 로 이동하고 이 파일에는 핵심 결과만 체크리스트로 남긴다.  
> 세션 요약 로그, 파일 맵 스냅샷, 코드 리뷰 라운드트립 내역도 아카이브 대상.

- **Spec:** `README.md` + `CLAUDE.md`
- **DB URL (dev):** `sqlite+aiosqlite:///data/facemetrics.db`
- **Stop hook:** `.claude/hooks/code-reviewer-gate.sh` — 코드 변경 시 자동 code-reviewer 호출

---

## 완료 이력 (상세 → `ARCHIVE.md`)

- [x] **Phase 1** — 기반 구축 ✅ (2026-04-13)  
  FastAPI 스캐폴딩, 5 테이블 DB, 투수 10명 시드, init/seed 스크립트  
  ⚠️ Python 3.14 + SQLAlchemy ≥ 2.0.49 필수 (`Mapped[Optional[str]]`, `__future__` 없음)

- [x] **Phase 2** — AI 엔진 ✅ (2026-04-13, 실검증 2026-04-14 세션 8)  
  관상(Claude Vision) + 운세(Claude Text) + 상성(룰 기반) + scoring_engine  
  세션 8 §B 에서 실 Claude API 캐시 미스/히트 경로 + atomic rollback 모두 검증 완료

- [x] **Phase 3 sub-task 1** — 크롤러 read-only ✅ (2026-04-13)  
  KBO `GetKboGameList` 단일 소스, `/ws/` robots carve-out, 이름 매처

- [x] **Phase 3 sub-task 2** — DB write + Scheduler ✅ (2026-04-13)  
  `upsert_schedule`, 5개 KST 잡(08:00/09:00/10:00/10:30/11:00), FastAPI lifespan wiring  
  실 데이터 smoke: `date(2026,4,14)` → 5경기 5/5 선발 확정 수신

- [x] **Phase 4** — API 라우터 ✅ (2026-04-13, 세션 4)  
  커밋: `72a5803` + 코드리뷰 수정 `1ee88ce`  
  - GET `/api/today`, `/api/matchup/{id}`, `/api/pitcher/{id}`, `/api/history`, `/api/accuracy`  
  - POST `/admin/crawl-schedule`, `/admin/analyze-face/{id}`, `/admin/generate-fortune`, `/admin/calculate-matchups`, `/admin/update-result/{id}`  
  - `app/schemas/response.py` Pydantic v2 응답 스키마  
  - `app/routers/_helpers.py` 공유 `pitcher_summary()` 헬퍼  
  - `python -c "from app.main import app"` import OK 확인

- [x] **Phase 5** — 프론트엔드 초기 구축 ✅ (2026-04-13, 세션 4)  
  커밋: `1ee88ce`, `e846880`  
  - Next.js 14 App Router (`frontend/`) — `npm run build` clean  
  - Pages: `/` (TodayMatchups hero + accordion), `/history`, `/pitcher/[id]`  
  - Components: `MatchupCard`(아코디언), `RadarChart`(SVG 5축), `ScoreBar`, `AxisDetail`, `Footer`  
  - Mock data: 3개 매치업 (엔스/곽빈, 김광현/쿠에바스, 네일/페디)  
  - `src/lib/api.ts` USE_MOCK 플래그, `src/types/index.ts`  
  - Tailwind 커스텀 색상 draft.html 픽셀 매칭, bar-fill 애니메이션  
  - 레거시 `shine-border.tsx`, `timeline.tsx` 삭제

- [x] **Phase 6 sub-task 1** — Alembic 마이그레이션 도입 ✅ (2026-04-13, 세션 5)  
  브랜치: `claude/add-alembic-vercel-og-rIYEo`  
  - `backend/alembic.ini`, `backend/alembic/env.py` (async `aiosqlite`/`asyncpg` 모두 지원)  
  - `backend/alembic/versions/0001_initial_schema.py` — Phase 4 스키마 그대로 5 테이블  
  - `requirements.txt` 에 `alembic==1.13.3` 추가  
  - `scripts/init_db.py` 가 `Base.metadata.create_all` → `command.upgrade(cfg, 'head')` 로 교체  
  - 검증: 신규 SQLite 에 `upgrade head` → `downgrade base` 라운드트립 OK,  
    SQLAlchemy `Base.metadata` ↔ alembic 실제 컬럼 drift 0건  
  - SQLite 는 `render_as_batch=True` 로 향후 ALTER 안전, env.py 는 런타임에 `app.config.get_settings().database_url` 주입

- [x] **Phase 6 sub-task 2** — 공유 카드 (@vercel/og) ✅ (2026-04-13, 세션 5)  
  브랜치: `claude/add-alembic-vercel-og-rIYEo`  
  - `@vercel/og` ^0.11.1 추가 (`frontend/package.json`)  
  - `frontend/src/app/api/og/matchup/[id]/route.tsx` — Edge Runtime, 1200×630 PNG  
    · 쿼리스트링 only (`home/away/homeTotal/awayTotal/winner/...`)로 백엔드 round-trip 없이 edge 캐싱  
    · `s-maxage=3600 stale-while-revalidate=86400` — 11:00 KST publish job 이후 점수가 frozen 이라 안전  
    · 면책 푸터 ("엔터테인먼트 목적 · 베팅과 무관") CLAUDE.md §6 준수  
  - `frontend/src/components/ShareButton.tsx` — `buildShareUrl()` + 다운로드 핸들러  
  - `MatchupCard.tsx` 에 ShareButton 마운트, "공유 이미지 저장" 버튼  
  - 검증: `npm run build` clean — 새 라우트 `ƒ /api/og/matchup/[id]` Edge 로 등록

- [x] **Phase 6 sub-task 3** — commit 98a36f3 사후 code-reviewer 리뷰 및 수정 ✅ (2026-04-13, 세션 6)  
  브랜치: `claude/fix-post-hoc-review-98a36f3` · 커밋: `741fc34`  
  세션 5 가 `code-reviewer-gate.sh` stop hook 을 우회한 채로 commit/push 했기 때문에 (post-commit 이라 `git diff HEAD` clean → silent pass) 사후로 리뷰 게이트를 집행.  
  리뷰어 Verdict: **BLOCK** (Critical 1 / Important 2 / Nits 3) → 3건 수정:
  - **R1 (Critical)** `scripts/seed_pitchers.py` — `Base.metadata.create_all` 제거. Alembic 단일 진실 원칙 복원, 선행 요구사항 (`init_db.py` 먼저) docstring 에 명시, 미사용 `Base` import 삭제.
  - **R2 (Important)** `backend/alembic/versions/0001_initial_schema.py` — pitchers `updated_at` 에 `onupdate=sa.func.now()` 추가. `app/models/pitcher.py:28` 와 metadata drift 해소 (ORM hook 이라 DDL 변화 0, autogenerate 재실행 시 잡음 제거).
  - **R3 (Important)** `frontend/src/app/api/og/matchup/[id]/route.tsx` — `paramInt(req, key, fallback, {min, max})` 로 시그니처 확장 후 `homeTotal`/`awayTotal` 에 `{min: 0, max: 100}` 적용. `?homeTotal=99999999` 같은 악의적 URL 이 OG 카드에 7자리 숫자 분사하는 브랜드 오염 차단.  
  검증: `ast.parse` OK (Python 2개), `npx tsc --noEmit` clean (frontend, `npm install` 후), `paramInt` 호출자 2건 모두 신 시그니처로 업데이트됨 확인.  
  Nits 3건 (matchup model `server_default=text("0")`, init_db URL 중복 주입, `ScoreBar.maxScore` 미사용 prop) 은 세션 7 로 이월.

---

## 현재 상태 (세션 11 기준, 2026-04-15)

main=`95d0873`. 세션 11 첫 턴 A-7 srId 라이브 검증 resolve. **배포 이전 blocker 없음** — Phase 6 실 배포(Vercel/Railway) + I3 APScheduler 싱글톤 가드가 남은 잔여. C1 srId 는 A-7 결과로 false alarm 판정 (아래 세션 11 산출물 참조). H1 stop hook 보강은 PR #8, D-4 tailwind 토큰화는 PR #9 완료.

세션 11 산출물:
- **A-7 srId 라이브 검증 완료** — `scripts/verify_srid.py` 로 `2026-04-15` 날짜에 세 변종(`0,1,3,4,5,7` / `0,9,6` / `0`)을 실 KBO `POST /ws/Main.asmx/GetKboGameList` 에 병렬 호출. 세 응답 모두 **5경기 동일**, 모든 게임 `SR_ID=0` / `LE_ID=1` (정규시즌 1군). 결론: 정규시즌 기간 `srId` 필터는 실질 no-op 이며 코드 값(`0,1,3,4,5,7`)과 스펙 값(`0,9,6`) 어느 쪽이든 매처 동작 동일. CLAUDE.md §5 를 코드값(더 보수적으로 시범/포스트시즌/올스타까지 덮는 allowlist)에 맞춰 정정. `srId` 의 series-type 매핑 (0=정규, 1=시범, 3/4/5=포스트, 7=올스타) 주석으로 기록. 포스트시즌/시범경기 기간 차이는 이번 검증에서 관측 불가 (날짜 제약), 나중에 해당 시즌 도달 시 재검증 여지.
- **I3 APScheduler 싱글톤 가드 완료** — `app/config.py` 에 `scheduler_enabled: bool = True` 필드 추가 (pydantic-settings 가 `SCHEDULER_ENABLED` 환경변수로 자동 매핑). `app/main.py:lifespan` 이 `settings.scheduler_enabled` 가 True 일 때만 `build_scheduler().start()` 를 호출하고, False 면 INFO 로그만 찍고 skip. finally 블록도 `scheduler is not None` 가드 후 shutdown. Admin 라우터는 스케줄러 인스턴스에 의존하지 않고 `app.scheduler` 모듈의 job 콜러블을 직접 import 하므로 (`crawl_schedule_job`, `analyze_and_score_matchups`, `publish_matchups`), 웹 파드가 scheduler 를 끈 상태에서도 `/admin/*` 수동 트리거는 정상 동작. 검증: pydantic Settings 직접 주입 (`default=True`, `false`/`0` → False, `true` → True) + `main.py` AST parse clean. 참고: 이번 환경에 `fastapi` 글로벌 미설치로 `from app.main import app` 전체 import smoke 는 미실행, AST 및 config 라운드트립만 검증. CI(PR) 에서 풀 smoke 커버.
  - **배포 런북 (Phase 6 Railway/Fly 적용 시 필수)** — 멀티 레플리카에서 크론 중복 실행 방지 원칙:
    · **웹 서비스 (replicas ≥ 1)**: `SCHEDULER_ENABLED=false`. 트래픽을 받는 모든 인스턴스.
    · **워커 프로세스 (replicas=1 고정)**: `SCHEDULER_ENABLED=true`. 크롤/분석/퍼블리시 5 잡 실행 전용. 수평 확장 금지 — 두 개 띄우면 `fortune_scores` 중복 write + Claude 토큰 2배 소모 재발.
    · dev/staging 단일 프로세스 구성은 기본값(`true`) 유지, 명시 설정 불필요.
    · Railway 의 경우 별도 Service 로 워커 분리 권장, Fly 는 `[processes]` 블록으로 `app`/`worker` 분리.

세션 8 산출물 (브랜치 `claude/session-8-ai-validation`):
- **B-1** 캐시 미스→히트 경로 실검증. `scripts/verify_ai_pipeline.py` 가 `pitcher_id=1,2` 의 profile_photo 를 manifest KBO URL 로 override 한 뒤 face/fortune 을 1회씩 실호출, 두번째 호출에서 캐시 히트(Claude 호출 0회)를 row count assertion 으로 검증. 4번의 실 Claude 호출(Vision×2 + Text×2) 모두 200 OK, 토큰 사용 로그 적재됨. score_matchup() 통합도 정상.
- **B-2** caller-managed transaction 으로 전환. `face_analyzer.get_or_create_face_scores` / `fortune_generator.get_or_create_fortune_scores` 의 내부 `commit/refresh` → `flush` 로 교체. 호출자가 트랜잭션 경계 책임. 후속 영향:
  · `scheduler.analyze_and_score_matchups` 의 외층 try/commit/rollback 이 매치업 1건을 진짜 atomic 하게 묶음 — face × 2 + fortune × 2 + matchup × 1 이 한 트랜잭션.
  · `admin.analyze_face` 와 `admin.generate_fortune` 에 명시적 `await session.commit()` / `rollback()` 추가 (generate_fortune 은 부분 성공 의미 보존 위해 per-iteration commit).
- **B-3** rollback 유닛 테스트 — `backend/tests/test_analyze_rollback.py` 3건:
  · `test_happy_path_persists_all_rows` — mock 으로 face/fortune 모두 성공 → face×2 + fortune×2 + matchup×1 검증.
  · `test_fortune_failure_rolls_back_face_rows` — face 성공 + Claude Text + hash fallback 모두 raise → 모든 행 0 (B-2 회귀 가드).
  · `test_face_failure_rolls_back_cleanly` — Claude Vision + hash fallback 모두 raise → 모든 행 0.
  실행: `pytest backend/tests/ -v` → 3 passed, 2.36s.
- **부수 산출물** `backend/tests/conftest.py` (DATABASE_URL 임시 파일 주입), `scripts/verify_ai_pipeline.py` (재현 가능한 실 API 검증).

세션 7 산출물 (참고):
- PR #4/#5 (`claude/session-7-nits-and-d7`) — N1+N2+N3 / D-7 / D-8 / alembic.ini cp949 fix.

세션 10 산출물 (2026-04-14, 연속 PR 처리):
- **세션 9 PR #7 merged** — Phase 6 배포 스켈레톤 main 반영 (CI green, main 6fe541e).
- **H1 Stop hook 보강 (PR #8 merged)** — `.claude/hooks/code-reviewer-gate.sh` 가 `git diff --name-only origin/main...HEAD` 브랜치-레벨 diff 로 post-commit silent-pass 차단. 마커 포맷 `<contenthash>@<shortsha>`. 3단 fallback (origin/main → HEAD~1 → no-op), deleted-path sentinel 처리. 5 케이스 수동 테스트 통과. H2 는 embedded SHA 로 기능 대체됐다고 판단 — 정식 deferred.
- **D-4 Tailwind 토큰화 (PR #9 merged)** — 조사 결과 D-4 원 전제(토큰 이미 존재)가 거짓이었음. `tailwind.config.ts` 에 `ink.title: "#0A192F"` 토큰을 **신규 추가** 후 `page.tsx:46` `text-[#0A192F]` → `text-ink-title` 리팩터. `frontend/preview/draft.html` 이 디자인 소스로 동일 색을 쓰고 있어 시각 변화 0. `.next/static/css` 에서 `.text-ink-title{color:rgb(10 25 47/...)}` 확인.
- **A-5 KBO playerId 매처 (브랜치 `claude/session-10-a5-kbo-player-id`, 본 PR)** — `pitchers.kbo_player_id` (unique nullable int, indexed) + `daily_schedules.home/away_starter_kbo_id` (nullable int) 컬럼. Alembic `0002_add_kbo_player_id.py` (batch mode, roundtrip clean). `services/crawler.match_pitcher_by_kbo_id()` 헬퍼 (signature `Optional[int]`). `scheduler._resolve_pitcher_id()` 가 id-first → name-fallback + 성공 시 pitcher 로우에 kbo_id write-back ("crawl 에서 학습"). `upsert_schedule` 도 fill-blank 정책으로 kbo_id 저장. 유닛 테스트 9건 (id hit/miss/None, id preference, lazy learn, upsert insert/update/no-overwrite, write-back skip when already filled). pytest 12/12 통과, import smoke OK, Alembic upgrade→downgrade→upgrade roundtrip clean.
- **A-5 code-reviewer 라운드** (pre-PR, PR #8 의 보강된 훅 동작을 실제 적용): Verdict APPROVE WITH FIXES (Critical 1 / Important 1 / Nits 2). 커밋 전 수정 반영:
  · **Critical — write-back transaction leak**: `_resolve_pitcher_id` 호출이 `try:` 블록 바깥에 있어서 lazy write-back 이 현재 게임의 원자 트랜잭션 경계에 포함되지 않았음. 게임 A 의 write-back 이 dirty 상태로 세션에 남다가 게임 B 의 `session.commit()` / `session.rollback()` 에 휘말리는 구조. 수정: 전체 resolve→score→upsert→commit 을 하나의 try 로 묶고 skip 분기도 rollback 선행. 이제 해소/스코어링 어느 단계든 실패 시 write-back 이 깨끗이 롤백됨.
  · **Important — type annotation drift**: `match_pitcher_by_kbo_id(kbo_player_id: int)` 가 body 에서 `None` 을 가드하고 있었음 → `Optional[int]` 로 수정, 직접 None 입력 케이스 테스트 추가.
  · **Coverage gap — upsert fill-blank**: `upsert_schedule` 의 kbo_id fill-blank / no-overwrite 분기가 테스트 0건이었음 → 3개 테스트 추가 (insert 시 저장, update 시 NULL 슬롯 채우기, 확정된 id 덮어쓰지 않음).
  · **Nit — match_pitcher_by_kbo_id(None) 명시 테스트**: 추가 완료 (위 카운트 포함). A-6 eager harvester 는 lazy write-back 이 기존 시드 풀을 커버하므로 우선순위 낮아져 deferred.
- **외부 리뷰 대응 (PR #11 merged, main 14c7e20)** — 다른 세션의 code-reviewer 가 A-5 에 대해 Critical 2 / Important 2 / Nit 3 으로 BLOCK 의견을 냈으나, 각 항목을 현재 main 에 대조한 결과 유효한 건 **N3 (로그 레벨) 만 1건**. 나머지는 stale 또는 false positive:
  · **C1 srId 값** (Critical) — `crawler.py:266` `"srId": "0,1,3,4,5,7"` vs CLAUDE.md §5 스펙 `0,9,6` 불일치. 유효하지만 어느 값이 실제 KBO 응답과 맞는지 라이브 검증 필수 → 세션 11 로 이월 (`kbo-data-crawler` 사용).
  · **C2 write-back rollback** (Critical) — "per-game try 안에 있어서 실패 시 write-back 이 사라진다" 는 지적은 버그 아닌 의도된 trade-off. `daily_schedules.home_starter_kbo_id` 는 upsert_schedule 에서 별도 commit 되어 DB 에 남아있으므로 다음 스케줄러 런이 같은 row 를 재읽고 재시도 → "학습 지연" 이지 "학습 소실" 이 아님. 또 "충돌 시 WARNING 로그 only, review queue 누락" 부분은 038aaa2 에서 해당 conflict 경로 자체가 삭제됐으므로 stale.
  · **I1 인덱스 중복 선언** (Important) — **실측 반증.** 모델 `unique=True, index=True` 로 `Base.metadata.create_all` 결과가 `CREATE UNIQUE INDEX ix_pitchers_kbo_player_id ON pitchers(kbo_player_id)` 로 alembic 0002 의 `create_index(..., unique=True)` 와 완전히 동일한 DDL 생성. 테스트로 확인 완료 (`scratch /tmp/drift_check.db`). Dual declaration 은 의도된 패턴이며, 모델에서 제거 시 오히려 `create_all` 이 인덱스를 안 만들어 **역방향 drift** 발생.
  · **I2 타입 어노테이션 / N1 existing_owner / N2 dead code guard** — 모두 038aaa2 (PR #10 의 fix commit) 에서 이미 해소된 stale 지적.
  · **N3 로그 레벨** (유효) — `scheduler.py:156` `logger.info` → `logger.debug`. 콜드 스타트 ~10회 후 idempotent 이므로 DEBUG 가 적절. 1줄 수정, PR #11 로 별도 처리.

세션 9 산출물 (브랜치 `claude/session-9-phase6-deploy`):
- **Phase 6 sub-task 4** — 배포 스켈레톤 도입. 로드맵 §Phase 6 의 첫 빌딩블록.
  · `backend/Dockerfile` — `python:3.12-slim` + tini, non-root(uid 1000), `PYTHONPATH=/app/backend`, 엔트리가 `scripts/init_db.py`(alembic upgrade head) 후 uvicorn 기동. 이미지에 `.env` 미포함(런타임 env vars 만 의존).
  · `frontend/Dockerfile` — node 20-alpine 멀티스테이지(deps → builder → runner), non-root, `next start -H 0.0.0.0`. 주 배포 타깃은 Vercel(CLAUDE.md §1) 이라 이 파일은 로컬 compose 용.
  · `docker-compose.yml` — backend(8000) + frontend(3000), `./data:/app/data` 바인드 마운트로 sqlite 퍼시스트, `DATABASE_URL` 절대경로 주입(`sqlite+aiosqlite:////app/data/facemetrics.db`), `env_file.required=false` 로 `.env` 미존재 허용. 향후 Postgres 추가 여지 있음.
  · `.dockerignore` — 루트 단일 파일. `.venv`/`node_modules`/`.next`/`data/*.db`/`**/.env`/docs 제외.
  · `.github/workflows/ci.yml` — PR + main push 트리거, concurrency cancel-in-progress. backend job: py 3.12, pip cache, `scripts/init_db.py`(alembic head), import smoke, `pytest backend/tests -v`. frontend job: node 20, npm cache, `npm run type-check`, `npm run build`.
- **검증**: `python -m pytest backend/tests -v` → 3 passed, `PYTHONPATH=backend python -c "from app.main import app"` OK, `python scripts/init_db.py`(임시 sqlite) alembic upgrade head 성공, `npm run type-check` clean, `npm run build` clean (5 routes, standalone output 생성 확인). docker-compose/ci.yml YAML parse OK. 실제 `docker build` 는 로컬에 docker CLI 없어 미검증 — PR CI 에서 실행 예정.
- **code-reviewer 라운드**: Verdict APPROVE WITH FIXES (Critical 0 / Important 4 / Nits 6). 커밋 전 다음 수정 반영:
  · **I1 CI DATABASE_URL 스코핑** — workflow-level env 에서 제거하고 alembic 스텝에만 `${{ github.workspace }}/data/facemetrics.db` 절대경로 주입. pytest 는 `backend/tests/conftest.py:26` 가 `os.environ["DATABASE_URL"]` 로 임시 파일을 무조건 덮어쓰므로 workflow env 오염 위험 차단.
  · **I4 Next standalone output** — `next.config.mjs` 에 `output: 'standalone'` 추가, `frontend/Dockerfile` runner 스테이지를 `.next/standalone` + `.next/static` + `public` 만 복사하도록 축소(이미지 ~500MB → ~150MB 수준). CMD 도 `node server.js` 로 변경. 재빌드 검증 `npm run build` clean.
  · **N2 tini 신호 전파** — `ENTRYPOINT ["tini", "-g", "--"]` (프로세스 그룹에 신호 전달) + CMD 의 uvicorn 앞에 `exec` 추가. `docker stop` 시 SIGTERM 이 uvicorn 까지 즉시 도달.
- **이월 (세션 10 처리)**:
  · **I2 bind-mount uid 불일치** — `./data:/app/data` + uid 1000 non-root. Linux 호스트의 실 유저 uid 가 1000 이 아니면 sqlite write EACCES. compose smoke 실행 전 `sudo chown -R 1000 ./data` 또는 `docker compose run --user $(id -u)` 안내 필요.
  · **I3 APScheduler 싱글톤** — `backend/app/main.py:17-18` lifespan 이 무조건 scheduler 기동. Railway/Fly 에서 replicas ≥ 2 이면 크롤/분석/퍼블리시 잡이 두 번 실행되어 `fortune_scores` 중복 write + Claude 토큰 2배 소모. 실 배포(세션 10) 전 `SCHEDULER_ENABLED` 플래그 또는 "scheduler 전용 워커 프로세스" 분리 필요.
  · **N1 compose 버전 요구사항** — `env_file.path/required` long-form 은 Compose v2.24+ (Jan 2024). 구버전은 파싱 실패.

세션 12 산출물 (브랜치 `claude/session-12-a6-harvester`, origin/main 95d0873 기반 — 세션 11 PR 미머지 상태에서 병렬 착수):
- **A-6 eager KBO 프로필 수확기 완료** — `seed_pitchers.py` 가 시드 직후 koreabaseball.com 을 호출해 신규 시드 투수의 `pitcher.kbo_player_id` (+ 비어있으면 `profile_photo` CDN URL) 를 즉시 채운다. A-5 의 lazy write-back 은 "다음 스케줄러 런에서 학습" 이지만 이건 "시드 즉시 학습" — 새 시드 투수의 freshness 0 구간을 없앤다.
  · **엔드포인트 재발견**: 디스커버리 스크립트 불필요. 기존 `scripts/crawl_pitcher_images.py:184` 의 `kbo_search_player` 가 이미 `POST /Player/Search.aspx` (ASP.NET VIEWSTATE 폼) → `PitcherDetail` 링크 parse → 프로필 이미지 URL 추출 전체 체인을 sync 로 검증 완료. 이 모듈은 그 async 쌍둥이.
  · **새 파일**: `backend/app/services/kbo_profile_harvester.py` — `HarvestResult(kbo_player_id, profile_photo_url)` dataclass + `harvest_profile(client, name, team)` 퍼블릭 API + `harvest_profile_standalone(name, team)` 편의 래퍼. `crawler._make_client` / `DEFAULT_HEADERS` / `GET_HEADER_OVERRIDE` / `RATE_LIMIT_S` / `_robots_allows` 전부 재사용. `/Player/Search.aspx` 와 `PitcherDetail` 페이지는 `/ws/` carve-out 바깥이라 표준 robots 체크를 통과.
  · **`seed_pitchers.py` 통합**: argparse 플래그 3개 추가 (`--harvest` opt-in, `--dry-run` 롤백, `--pitcher-id N` 디버그 필터). 기본 실행은 기존 동작 그대로 — 회귀 0. harvest 패스는 JSON upsert 직후 단일 `session.flush()` 뒤에 돌고, 루프 종료 후 단일 `commit()` (dry-run 시 `rollback()`).
  · **유닛 테스트 9건** (`backend/tests/test_profile_harvester.py`): happy path / retired-pitcher fallback / ambiguous multi-hit + warning / no candidates / search GET 에러 / detail GET 에러 (id 는 여전히 수확) / detail 이미지 누락 / __VIEWSTATE 누락 / 빈 이름 (HTTP 0회). autouse fixture 로 `_robots_allows` + `asyncio.sleep` 몽키패치하여 오프라인 실행.
  · **실 KBO smoke (2026-04-15)**: `python scripts/seed_pitchers.py --harvest` → **10/10 hit** (원태인 69446 / 곽빈 68220 / 네일 54640 / 카스타노 54920 / 손주영 67143 / 박세웅 64021 / 임찬규 61101 / 문동주 52701 / 양현종 77637 / 하트 54930). 소요 ≈ 40초 (10 × 4 HTTP 콜 × 1초 rate limit). 2차 실행은 전부 `skipped` — 멱등성 확인. `--dry-run --pitcher-id 1` 로 NULL→수확→롤백 경로도 수동 검증 (post-rollback row 여전히 NULL).
  · **photo_filled=0**: 10명 모두 manifest 로컬 경로 (`data/pitcher_images/kbo/NN_...jpg`) 가 이미 `profile_photo` 에 박혀있어 harvester 가 덮어쓰지 않음 — 세션 8 B-1 이 이 로컬 파일 기반으로 Claude Vision 검증한 상태를 보존. CDN URL 마이그레이션이 필요하면 별도 작업.
  · **검증 체크리스트**: `pytest backend/tests -v` → 21/21 통과 (test_analyze_rollback 3 + test_kbo_id_matcher 9 + test_profile_harvester 9). import smoke OK. alembic upgrade head clean.
  · **포스트시즌 재검증 여지**: KBO 검색 페이지의 ASP.NET 컨트롤 경로 (`ctl00$ctl00$ctl00$cphContents$...`) 가 시즌 전환 / 페이지 리뉴얼 시 변할 수 있음 — harvester 는 `__VIEWSTATE` / `btnSearch` 필드 누락 시 None 반환하므로 fail-soft 지만 다음 신규 시드 사이클에서 hit rate 모니터링 권장.

세션 13 산출물 (브랜치 `claude/session-11-a7-i3`, 코드 HEAD `588504b` + docs HEAD `684737d`, origin/main `ed958a1` 기반 — A-6/A-7 머지 직후 이어서 API-free TODO 소화):
- **C-2 publish_matchups 필터 버그** (`fce8117`) — `backend/app/scheduler.py` `publish_matchups` SELECT 에 `Matchup.is_published.is_(False)` 필터 누락되어 있어 11:00 KST 잡이 재실행되면 이미 발행된 매치업도 다시 flip 하던 이슈. 필터 추가 + `backend/tests/test_publish_matchups.py` 신규 (published/unpublished 혼합 시드 → unpublished 만 flip 검증).
- **C-1 `_append_review` dedup + concurrency** (`62e14cb`) — `backend/app/services/crawler.py` `_append_review` 를 async 로 전환하고 모듈 스코프 `asyncio.Lock` 으로 read-modify-write 전체 구간 직렬화. 중복 append 방지 키 `(date, team, crawled_name)`. 파일 I/O 는 `asyncio.to_thread` 로 off-loop. 3개 호출자 전부 `await` 로 업데이트. `backend/tests/test_review_queue.py` 신규 (dedup 테스트 + 20-way `asyncio.gather` concurrent 스모크 + `match_pitcher_name` 통합 테스트 w/ `tmp_path` monkeypatch).
- **CI alembic roundtrip 게이트** (`588504b`) — `.github/workflows/ci.yml` backend job 에 `alembic upgrade head → downgrade base → upgrade head` 라운드트립 스텝 추가. `working-directory: backend`, `DATABASE_URL` 은 해당 스텝에만 스코프 — 기존 pytest 스텝의 `conftest.py:26` 임시 파일 오버라이드와 충돌 없음.
- **A-6/A-7 리뷰 피드백 일괄 수정** (`a453fab`) — 세션 13 시작 시 code-reviewer 가 APPROVE WITH FIXES 로 Critical 1 / Important 2 / Nit 2 flag:
  · `crawler.py:266` srId paper-trail 3줄 인라인 주석 추가 (session 11 A-7 결정, 2026-04-15 테스트 범위, 포스트시즌 divergence open risk 명시).
  · `scripts/verify_srid.py` `_one` 최상단에 `await asyncio.sleep(1.0)` 추가 + 스테일 docstring 정정.
  · `scripts/seed_pitchers.py` `_harvest_missing_kbo_ids` per-pitcher `try/except Exception: logger.warning; continue` 로 mid-run abort 차단.
  · `backend/app/services/kbo_profile_harvester.py:41` `DEFAULT_HEADERS` doc-by-import (`# noqa: F401`) 삭제.
- **검증**: `pytest backend/tests -v` → **25 passed** (22 → 25, 신규 +3: publish 1 + review dedup/concurrent/match 3 중 일부). `ast.parse` scripts OK, `from app.services.crawler import _fetch_kbo` / `from app.services.kbo_profile_harvester import harvest_profile` import OK. YAML parse OK. `PYTHONPATH=backend python -c "from app.main import app"` 은 로컬 샌드박스 `fastapi` 미설치로 skip — CI runner 가 커버.
- **사후 code-reviewer 라운드 (세션 13 말)**: Verdict APPROVE WITH FIXES (Critical 0 / Important 2 / Nit 3) — 전부 non-blocker, 세션 14 로 이월:
  · **I1 `verify_srid.py` SR_VARIANTS 라벨** — `"claude_md_spec (0,9,6)"` 라벨이 `0,9,6` 를 현 스펙처럼 보이게 함. `"pre-session11 (0,9,6)"` 등으로 리네임 필요.
  · **I2 CI alembic roundtrip sanity assertion** — `alembic upgrade head` 가 `script_location` 을 못 찾아도 no-op 으로 silent pass 할 위험. "Running upgrade" 로그 grep 또는 revision 출력 assert 로 실제 실행 증명 필요.
  · **N1** `publish_matchups` 를 bulk `UPDATE` 로 전환 (현재는 ORM row 로드 후 loop set — ≤10 rows 라 실용 문제 없음).
  · **N2** `verify_srid.py` 의 `_one` 입장 sleep 과 `main` 뒤 sleep 이 중복 (각 variant 당 2초) — 약간 리던던트.
  · **N3** `test_publish_matchups` 에서 이미 published row 의 `updated_at` (있다면) 불변 assertion 추가.

---

## [WPI] 세션 14 산출물 (2026-04-15)

세션 14 첫 턴에 Step 1 (세션 13 리뷰 잔재 I1/I2/N2) 완료. PR 생성은 사용자 홈 환경에서 처리 예정 — 세션 14 로컬 환경에도 `gh` CLI 미설치.

### 완료
- **Step 1 (commit `01c62aa`)** — 세션 13 리뷰 잔재 3건 단일 커밋 처리, origin 푸시, code-reviewer APPROVE (Critical 0 / Important 0 / Nit 1).
  · **I1** `scripts/verify_srid.py:45` — `SR_VARIANTS` 키 `"claude_md_spec (0,9,6)"` → `"pre_session11_guess (0,9,6)"`. 실제 스펙값은 `0,1,3,4,5,7` (세션 11 A-7 결정) 이고 `0,9,6` 은 검증 전 추측값이었음을 라벨만 봐도 명확하게.
  · **I2** `.github/workflows/ci.yml:54-66` — alembic roundtrip 스텝에 `set -euo pipefail` + `2>&1 | tee /tmp/alembic_{down,up}.log` + `grep -q "Running downgrade"` / `grep -q "Running upgrade"` assertion 추가. `script_location` 미스컨피그 등 silent no-op 차단. **중요**: 첫 `alembic upgrade head` 제거 — 직전 스텝 `Alembic upgrade head (sqlite)` 가 이미 `python scripts/init_db.py` 로 DB 를 head 에 올려놨기 때문에 재실행 시 "Running upgrade" 로그 0 줄 → grep assertion 실패. 현재는 `downgrade base → assert → upgrade head → assert` 2단 구성. alembic INFO 로거 + stderr StreamHandler 동작은 `backend/alembic.ini:55` 확인.
  · **N2** `scripts/verify_srid.py:134` — `main` 루프 뒤 `await asyncio.sleep(1.0)` 제거. `_one:67` 입장 sleep 이 이미 첫 호출 포함 모든 요청 직전 실행되므로 변종별 2초 → 1초, rate limit ≤1 req/s 보존.

- **code-reviewer 라운드 결과**: APPROVE. I2 로그 경로 위험 (`set -euo pipefail` + pipefail 덕에 `tee` 가 alembic 실패 마스킹 못 함 / `/tmp/` 는 runner 격리 OK / 첫 upgrade 제거는 gate 강도 저하 없음) 전부 체크. secrets/`.env`/`*.db` 누출 0건.

### 이월 / 미완
- **Step 0 (PR 생성)** — 여전히 `gh` CLI 미설치. 집 환경에서 `gh pr create --base main --head claude/session-11-a7-i3 --title "session 13+14: C-1/C-2/CI roundtrip + A-6/A-7 reviewer fix-ups + I1/I2/N2"` 또는 GitHub 웹 UI. PR 본문은 세션 13 산출물 5개 커밋 + Step 1 의 `01c62aa` 설명을 쓰면 됨. 현재 브랜치 `claude/session-11-a7-i3` HEAD = `01c62aa` (코드 5 + docs 2 = 7 커밋).
- **Nit (비차단, PROGRESS.md 만의 이슈)** — `PROGRESS.md:166`, `:192` 가 기록 시점 그대로 `"claude_md_spec (0,9,6)"` 라벨을 언급. 동작 영향 0 이라 changelog 로 존치 결정, 다음 세션에서 1줄 주석 달거나 그대로 둘 것.
- **N1 (`publish_matchups` bulk UPDATE)** — 진짜 문제 생길 때까지 defer 유지.
- **N3 (`Matchup.updated_at` 불변 assertion)** — `Matchup` 모델에 `updated_at` 실존 확인 후 결정. 확인 자체가 10초라 세션 15 첫 턴 여유 아이템.

## [WPI] 세션 15 인계 (2026-04-15)

### 시작 상태
- main=`ed958a1` (세션 13 PR 아직 머지 전). 브랜치 `claude/session-11-a7-i3` HEAD=`01c62aa` (Step 1 포함), origin 푸시 완료.
- **PR 미생성** — 집 환경에서 `gh` 설치 후 수동 생성 필요.
- 세션 8 키 로테이션 이후 `backend/.env` 유지.
- 로컬 `docker` CLI 없음 — compose 실 smoke 여전히 미검증.
- `fastapi` 글로벌 미설치 제약 동일.
- pytest 25 green (세션 13 기준 그대로, Step 1 은 CI 설정 + 스크립트 라벨/sleep 변경 뿐이라 테스트 수 변동 없음).

### 첫 턴에 할 일 (권장 순서)

**0. PR 생성 + 머지** — 집 환경에서 `gh pr create ...` 실행 후 CI green 확인 → squash merge → `git checkout main && git pull origin main`. 새 브랜치에서 세션 15 작업 시작.

**1. Step 4 면책 copy review** (API-free, 10분) — 가장 저위험/고정산 아이템. `frontend/src/components/Footer.tsx` + `frontend/src/app/api/og/matchup/[id]/route.tsx` + about 영역에 "엔터테인먼트 목적 · 베팅과 무관" 고지 톤 일관성 확인. CLAUDE.md §6 준수.

**2. Step 2 Phase 6 실배포** (Vercel FE + Railway/Fly BE) — I3 가드 / I2 uid 가이드 / C-1·C-2 필터 fix / I1·I2·N2 잔재 전부 준비됨. 이제 진짜 배포 가능:
   - Railway/Fly 서비스 분리: 웹 `SCHEDULER_ENABLED=false`, 워커 `SCHEDULER_ENABLED=true` (replicas=1).
   - Postgres 프로비저닝 + `DATABASE_URL` asyncpg 전환 + `ANTHROPIC_API_KEY` secret 주입.
   - Vercel 배포(FE): `NEXT_PUBLIC_API_BASE` + OG route edge runtime 실제 PNG 반환 검증.

**3. Step 3 Docker 실 smoke** — 로컬 `docker` CLI 설치 후 `docker compose up` 엔드투엔드. I2 uid 가이드 준수 (`sudo chown -R 1000 ./data`).

**4. 포스트시즌 재검증 여지** — 변동 없음. 가을 도달 시 `scripts/verify_srid.py` 재실행.

**5. 선택적 — N3 확인** — `Matchup` 모델에 `updated_at` 있으면 `test_publish_matchups` 에 이미 published row 의 `updated_at` 불변 assertion 추가.

### 구조적 개선 현황
- [x] **H1** `.claude/hooks/code-reviewer-gate.sh` 가 `git diff --name-only origin/main...HEAD` 브랜치-레벨 diff 로 post-commit silent-pass 차단. 마커 `<contenthash>@<shortsha>` 포함 (PR #8, 세션 10).
- [ ] **H2** "세션 마지막 턴이 git commit/push 를 포함하면 code-reviewer 호출" — H1 마커에 SHA 가 embed 돼서 같은 커밋이 두 번 리뷰되지 않는 효과를 얻었으므로 정식 deferred (재도입 시 검토).

---

## 진행 중 TODO

### A. 크롤러 마무리

- [x] **A-5.** `pitchers.kbo_player_id` + `daily_schedules.home/away_starter_kbo_id` 컬럼, `match_pitcher_by_kbo_id()` 헬퍼, 스케줄러 ID-first 분기 + lazy write-back (세션 10, PR #10). Alembic 0002 roundtrip clean, pytest 12/12. Write-back 로그는 PR #11 에서 DEBUG 로 하향.
- [x] **A-6.** `seed_pitchers.py` KBO 프로필 수확기 (세션 12, PR #13). `backend/app/services/kbo_profile_harvester.py` + `--harvest`/`--dry-run`/`--pitcher-id` 플래그 + 유닛 테스트 9건. 2026-04-15 실 smoke 10/10 hit, 멱등.
- [x] **A-7.** `crawler._fetch_kbo` `srId` 라이브 검증 완료 (세션 11, 2026-04-15). `scripts/verify_srid.py` 로 세 변종 모두 동일 응답 확인 → 정규시즌 기간 실질 no-op. CLAUDE.md §5 스펙을 코드값(`0,1,3,4,5,7`)으로 정정. 포스트시즌 도달 시 재검증 여지 있음.

### B. Phase 2 AI 실검증 ✅ (세션 8 완료)

- [x] **B-1** `.env` 에 `ANTHROPIC_API_KEY` → 파이프라인 실행 검증 — `scripts/verify_ai_pipeline.py` 로 캐시 미스/히트 경로 + score_matchup 통합 모두 실 Claude API 검증
- [x] **B-2** 고아 score row 문제 — caller-managed transaction 으로 전환 (face/fortune `commit/refresh` → `flush`, 호출자 `commit/rollback`). `analyze_and_score_matchups` 가 매치업 1건을 atomic 하게 묶음
- [x] **B-3** `analyze_and_score_matchups` rollback 테스트 — `backend/tests/test_analyze_rollback.py` 3건 (happy / fortune-fail / face-fail) → `pytest` 통과

### C. 운영 잔여 (non-blocker)

- [x] **C-1** `_append_review` dedup, concurrency — 세션 13 (`62e14cb`). async 전환 + 모듈 스코프 `asyncio.Lock` + `(date, team, crawled_name)` dedup + `asyncio.to_thread` file I/O + 3개 호출자 await. 테스트 3건.
- [x] **C-2** `publish_matchups` — `is_published.is_(False)` 필터 추가 — 세션 13 (`fce8117`). 회귀 테스트 포함.
- [x] **C-3** `analyze_and_score_matchups` — pitcher `IN [...]` 배치 로드 (matchup 라우터 경로는 `f4fba33` 에서 이미 완료, 서비스 레이어에도 동일 패턴 적용 필요 시 다시 열기)
- [x] Alembic 도입 — 세션 5 완료 (`backend/alembic/`, init_db.py 전환)

### D. Phase 5 프론트엔드 잔여 (세션 4/5 BLOCK 후속)

- [x] **D-1~D-6** C1/C2/C3/I1/I6/C4/I3/I4/I5 — PR #1 + 후속 커밋으로 해소
- [x] **D-4 (partial)** I2 Tailwind 토큰화 — `tailwind.config.ts` 에 `ink.title: "#0A192F"` 토큰 신규 추가 후 `page.tsx:46` 리팩터 (세션 10, PR #9)
- [x] **D-7** `PitcherProfile` 삭제 → `PitcherDetail` 통합 (세션 7, 프론트 어댑터 레이어)
- [x] **D-8** 360px 모바일 뷰포트 smoke test — dev 서버 + 3 경로 200 + 정적 분석 + 사용자 로컬 DevTools 육안 검수 통과 (세션 7)
- [x] **D-9** Share card PNG 생성 — `@vercel/og` Edge route + ShareButton (세션 5)

### E. 사후 리뷰 Nits (세션 6 → 7 이월)

- [x] **N1** `models/matchup.py` `server_default=text("0")` (세션 7)
- [x] **N2** `scripts/init_db.py` URL 중복 주입 제거 (세션 7)
- [x] **N3** `components/ScoreBar.tsx` 미사용 `maxScore` prop 제거 (세션 7)

---

## Phase 6 로드맵

- [x] 공유 카드 PNG — 세션 5 `@vercel/og` Edge route
- [x] Alembic 도입 — 세션 5
- [x] Dockerfile × 2 + docker-compose + GitHub Actions CI 스켈레톤 — 세션 9
- [ ] 실 `docker build` 및 compose up 엔드투엔드 smoke (로컬 docker CLI 필요)
- [ ] Vercel 배포(FE) — 환경변수 `NEXT_PUBLIC_API_BASE` 설정, OG route edge runtime 검증
- [ ] Railway/Fly 배포(BE) — Postgres 프로비저닝 + `DATABASE_URL` 주입, `ANTHROPIC_API_KEY` secret. APScheduler 싱글톤 가드는 세션 11 에서 `SCHEDULER_ENABLED` 플래그로 해결됨 (웹 레플리카 false / 워커 파드 true).
- [ ] 면책 고지 최종 copy review (엔터테인먼트 목적, 베팅 무관)
- [x] CI 게이트 강화 — PR 에서 alembic upgrade head → downgrade base → upgrade head 라운드트립 스텝 추가 (세션 13, `588504b`). 세션 14 에서 "Running upgrade" 로그 assertion 으로 silent-pass 차단 예정 (I2 리뷰 잔재).
