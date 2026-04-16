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

ULTRAPLAN Phase 7 · Wave 1 Track D — 상성 calculator 감사 (2026-04-16, 브랜치 `claude/wave1-track-d-chemistry-audit-HAQ7G`):
- **감사 범위**: `backend/app/services/chemistry_calculator.py` + `data/zodiac_compatibility.json` + `data/constellation_elements.json` 을 README §2-3 표/수식에 한 줄 단위로 대조.
- **Verdict: PASS — 코드 수정 없음.** 모든 테이블/계수/클램프가 스펙과 일치.
  · 삼합(+2) 4 그룹 — 자-진-신, 축-사-유, 인-오-술, 묘-미-해 ✅
  · 육합(+1.5) 6 페어 — 자-축, 인-해, 묘-술, 진-유, 사-신, 오-미 ✅
  · 원진(-1.5) 6 페어 — 자-미, 축-오, 인-사, 묘-진, 신-해, 유-술 ✅
  · 충(-2) 6 페어 — 자-오, 축-미, 인-신, 묘-유, 진-술, 사-해 ✅
  · 별자리 원소 — 동질 +1 / 상생(불-바람·물-흙) +1.5 / 상극(불-물·바람-흙) -1 / 중립 0 ✅
  · 기본 2점 + 합산 → clamp[0, 4] (JSON `_meta.base_score` / `_meta.clamp_range` 에서 로드) ✅
  · 모든 페어가 단일 규칙에만 소속 — 규칙 우선순위 충돌 부재 (수동 검증 완료).
- **엣지 케이스 테스트 추가** (`backend/tests/test_chemistry_calculator.py`, 96 테스트):
  · 12 삼합 페어 × 6 육합 × 6 원진 × 6 충 전체 열거.
  · 동일 띠 (12지신 전수) → "자기(동일 띠)" 라벨 + delta 0 검증 (동일 구단 맞대결 시나리오 포함).
  · 원진+상극 (자-미 / 불-물) → raw -0.5 → clamp 0. 충+상극 (자-오 / 불-물) → raw -1 → clamp 0.
  · 삼합+상생 → raw 5.5 → clamp 4. 삼합+동질 → raw 5 → clamp 4.
  · 충+상생 (경계 교차, clamp 없음). 충+중립, 삼합+중립 (정확히 경계에 랜딩, clamp 트리거 안 됨).
  · 알 수 없는 띠/원소/빈 문자열 → ValueError.
  · 공백 정규화 (`strip()`).
  · home/away 스왑 대칭성 (24 비동일 띠 페어 전수 + full breakdown 스왑).
  · `chemistry_for_pitchers` 덕타입 래퍼.
  · JSON 스펙 가드 — 데이터 파일이 README 값에서 드리프트하면 즉시 fail.
- **code-reviewer 라운드** (Verdict APPROVE WITH FIXES, Critical 0 / Important 2 / Nit 1) — 전부 반영 후 재실행:
  · **I1 중립 원소 커버리지** — 불-흙 만 검증 중, 바람-물 방향 미커버. `NEUTRAL_ELEMENT_PAIRS = [("불","흙"), ("흙","불"), ("바람","물"), ("물","바람")]` 로 parametrize.
  · **I2 private helper 의존성 문서화** — 모듈 docstring 에 `_load_zodiac_data` / `_load_constellation_data` 가 이름 바뀌면 테스트도 따라가야 함을 명시.
  · **N1 ceiling 코멘트 명확화** — `test_samhap_pair_gives_plus_two` 주석에 "exact ceiling, not over-clamped" 추가 (독자가 clamp edge 와 헷갈리지 않도록).
- **검증**: `pytest backend/tests -v` → 117 passed (기존 21 + 신규 96). `chemistry_calculator.py` / JSON 데이터 둘 다 무변경.

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

---

## [WPI] 세션 12 인계 (2026-04-15)

### 시작 상태
- main=`95d0873` + 세션 11 브랜치(`claude/session-11-a7-i3`, 예정 PR). 세션 11 에서 A-7(srId 라이브 검증) + I3(APScheduler 싱글톤 가드) 두 건 resolve. code-reviewer 라운드 APPROVE WITH FIXES (Important 3 모두 반영 후 커밋).
- 세션 8 키 로테이션 이후 `backend/.env` 유지.
- 로컬 `docker` CLI 아직 없음 — compose 실 smoke 여전히 미검증.
- 세션 11 환경에 `fastapi` 글로벌 미설치로 `from app.main import app` 풀 import smoke 는 미실행. AST parse + config 라운드트립만 로컬 검증. PR CI(`.github/workflows/ci.yml`) 가 풀 backend import + pytest 커버.

### 첫 턴에 할 일 (권장 순서)

**1. 세션 11 PR 머지 확인 + main rebase** — `claude/session-11-a7-i3` 가 CI green 이면 squash merge. `git pull origin main` 으로 시작.

**2. Phase 6 실 배포** (Vercel FE + Railway/Fly BE) — I3 가드는 준비됐으므로 이제 실 배포 가능:
   - **Railway/Fly 서비스 분리**: 웹 서비스에 `SCHEDULER_ENABLED=false`, 워커 프로세스(replicas=1 고정) 에 `SCHEDULER_ENABLED=true`. PROGRESS.md §세션 11 I3 배포 런북 참조.
   - Postgres 프로비저닝 + `DATABASE_URL` asyncpg 전환 + `ANTHROPIC_API_KEY` secret 주입.
   - Alembic upgrade head 가 startup script 에 포함됐는지 확인 (`backend/Dockerfile` 엔트리).
   - Vercel 배포(FE): `NEXT_PUBLIC_API_BASE` 환경변수 + OG route edge runtime 실제 PNG 반환 검증.

**3. Docker 실 smoke** — 로컬 `docker` CLI 설치 후 `docker compose up` 엔드투엔드. I2 uid 가이드 (`sudo chown -R 1000 ./data` 또는 `--user $(id -u)`) 준수 필요. 배포 전 마지막 안전망.

**4. A-6** — 세션 12 (PR #13) 에서 eager KBO 수확기 완료. `seed_pitchers.py --harvest` 로 신규 시드 freshness 즉시 해소 경로 확보.

**5. 포스트시즌 재검증 여지** — A-7 은 2026-04-15 (정규시즌 5경기 날짜) 에서만 검증됨. 시범/포스트시즌/더블헤더/우천취소 날짜에서는 `srId` 필터가 유의미할 수 있음. 가을 도달 시 `scripts/verify_srid.py` 재실행하여 응답 차이 확인 권장.

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

- [ ] **C-1** `_append_review` dedup, concurrency
- [ ] **C-2** `publish_matchups` — `is_published.is_(False)` 필터 추가
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
- [ ] CI 게이트 강화 — PR 에서 alembic downgrade base → upgrade head 라운드트립 추가 검토

---

## ULTRAPLAN — Phase 7: FE↔BE 통합 & 런치

> **작성일:** 2026-04-16 · **기준:** main `981f19a` (세션 11+12 머지 완료)
> **목표:** mock 데이터 제거 → 실 백엔드 연동 → 배포까지 최단 경로.
> 4 Wave 구성. Wave 내 Track 은 완전 병렬, Wave 간만 의존성.

### 현재 상태 요약

| 영역 | 상태 | 핵심 근거 |
|------|------|-----------|
| **Backend** | ✅ 완성 | 5 라우터 + 5 서비스 + 5 스케줄러 잡 + Alembic 2 마이그레이션. pytest 21/21. |
| **Frontend** | ⚠️ Mock only | `USE_MOCK=true` 로 3개 하드코딩 매치업 표시. 실 API 미연결. |
| **FE↔BE 스키마** | ❌ 불일치 4건 | 아래 GAP 분석 참조. Mock 모드에서만 테스트돼서 발견 안 됨. |
| **배포** | ❌ 미착수 | Dockerfile/compose/CI 스켈레톤만 존재. 실 인프라 0. |
| **운영 잔여** | ⚠️ C-1, C-2 미완 | `publish_matchups` 멱등성 + review queue 미구현. |

### GAP 분석 — FE↔BE 스키마 불일치 (Critical)

> FE 가 mock 데이터로만 동작해서 실 API 연결 시 **4곳에서 런타임 에러** 발생.

| # | 엔드포인트 | FE 기대 | BE 실제 | 수정 방향 |
|---|-----------|---------|---------|-----------|
| **G1** | `GET /api/today` | `MatchupSummary[]` (flat array) | `TodayResponse { date, day_of_week, matchups[] }` | FE `getTodayMatchups()` 가 `.matchups` 를 unwrap |
| **G2** | `GET /api/matchup/{id}` | `MatchupDetail extends MatchupSummary` → `home_total`, `away_total`, `chemistry_score`, `game_time`, `series_label` 필수 | BE `MatchupDetail` 에 해당 필드 없음 | BE 스키마에 5개 필드 추가 + 라우터 매핑 |
| **G3** | `GET /api/history` | `HistoryMatchup extends MatchupSummary` → `actual_winner`, `prediction_correct`, `game_date` 추가 | BE `HistoryResponse.matchups` 가 `list[MatchupSummary]` (추가 필드 0) | BE 에 `HistoryMatchup` 스키마 신설, 라우터에서 `actual_winner`/`prediction_correct` 매핑 |
| **G4** | `GET /api/accuracy` | `AccuracyStats.recent_7_days?` (optional) | BE `AccuracyResponse.recent_7_days` (required) | BE 를 `Optional` 로 완화 (데이터 부족 시 None) |

### GAP 분석 — 운영 잔여

| # | 항목 | 현재 | 수정 |
|---|------|------|------|
| **C-2** | `publish_matchups` 멱등성 | 날짜 전체 SELECT → 이미 published 된 row 도 다시 True 세팅 | `.where(Matchup.is_published.is_(False))` 필터 추가 |
| **C-1** | 미지 투수 review queue | `_append_review` 미구현. 크롤러가 매칭 실패 시 WARNING 로그만 | `review_queue` 테이블 or JSON 파일 + admin 조회 엔드포인트 |

---

### WAVE 1 — Foundation Fixes (완전 병렬, 의존성 0)

> 4 Track 동시 실행. 각 Track 은 독립 에이전트가 처리.

#### Track A: BE 스키마 정합 (fastapi-backend-dev)

**파일:** `backend/app/schemas/response.py`, `backend/app/routers/matchup.py`, `backend/app/routers/history.py`, `backend/app/routers/accuracy.py`

1. **G2** `MatchupDetail` 에 누락 필드 추가
   - `home_total: int`, `away_total: int`, `chemistry_score: float` 추가
   - `game_time: Optional[str]`, `series_label: Optional[str]` 추가
   - `matchup.py` 라우터에서 해당 값을 Matchup + DailySchedule 에서 매핑
2. **G3** `HistoryMatchup` 스키마 신설
   - `class HistoryMatchup(MatchupSummary)` + `game_date`, `actual_winner`, `prediction_correct` 필드
   - `HistoryResponse.matchups` 타입을 `list[HistoryMatchup]` 으로 변경
   - `history.py` 라우터에서 `actual_winner` + `prediction_correct` 계산 로직 추가
3. **G4** `AccuracyResponse.recent_7_days` → `Optional[PeriodAccuracy]`
4. **C-2** `scheduler.py:344` 에 `.where(Matchup.is_published.is_(False))` 추가
5. 검증: `pytest backend/tests -v` + `from app.main import app` import smoke

#### Track B: FE API 클라이언트 정합 (react-ui-dev)

**파일:** `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`

1. **G1** `getTodayMatchups()` — `fetchJson<TodayResponse>("/api/today")` 후 `.matchups` unwrap
   - `TodayResponse` 인터페이스 FE 에 추가 (`{ date: string; day_of_week: string; matchups: MatchupSummary[] }`)
2. **G4** `AccuracyStats.recent_7_days` — 이미 optional (`?`) 이므로 FE 는 OK. BE 쪽 수정(Track A) 만으로 해소.
3. Mock 데이터 경로 유지 — `USE_MOCK=true` 일 때 기존 mock 반환 그대로 보존 (개발 편의)
4. 검증: `npm run type-check` + `npm run build` clean

#### Track C: Live 크롤 Smoke (kbo-data-crawler)

**목표:** 2026-04-16 실 KBO 일정 크롤 → DB 적재 → 선발투수 매칭까지 검증.

1. `scripts/crawl_today.py` 실행 (또는 `POST /admin/crawl-schedule` 수동 트리거)
2. 반환된 경기 수 / 선발투수 매칭률 확인
3. 크롤 결과 → `daily_schedules` 테이블 적재 검증
4. 실패 시 `crawler.py` 파서 패치 (KBO 사이트 변경 대응)

#### Track D: 상성 로직 감사 (fortune-domain-expert)

**목표:** `chemistry_calculator.py` 가 README §2-3 명세와 정확히 일치하는지 검증.

1. 삼합/육합/원진/충 테이블 — 코드 vs README 대조
2. 별자리 원소 궁합 (불-바람 상생, 불-물 상극 등) — 코드 vs README 대조
3. 기본 2점 + 궁합 합산 → clamp [0, 4] 로직 확인
4. 엣지 케이스: 동일 띠 vs 동일, 같은 팀 매치업 시 상성

---

### WAVE 2 — Integration Wiring (Wave 1 완료 후, 병렬 2 Track)

#### Track E: FE 실 데이터 연동 + UI 검증 (react-ui-dev)

**의존:** Track A (BE 스키마 확정) + Track B (FE 클라이언트 수정)

1. `.env.local` 에 `NEXT_PUBLIC_USE_MOCK=false` + `NEXT_PUBLIC_API_URL=http://localhost:8000` 설정
2. `npm run dev` + 백엔드 `uvicorn app.main:app` 동시 기동
3. 페이지별 검증:
   - `/` (TodayMatchups) — 매치업 카드 렌더, 아코디언 확장, 레이더 차트
   - `/history?date=2026-04-15` — 과거 매치업 표시
   - `/pitcher/1` — 투수 프로필 + 관상/운세 점수
4. 360px 모바일 뷰포트 체크 (DevTools)
5. 면책 고지 Footer 모든 페이지 노출 확인

#### Track F: C-1 Review Queue (fastapi-backend-dev)

**의존:** Track C (크롤러 동작 확인 — 어떤 형태의 미매칭이 실제 발생하는지 파악)

1. `backend/app/models/` 에 `review_item.py` 추가 (또는 경량 JSON 파일 접근)
   - 필드: `name`, `team`, `game_date`, `source`, `created_at`, `resolved`
2. `crawler.py` 의 미매칭 경로에서 `_append_review()` 호출
3. `GET /admin/review-queue` 조회 엔드포인트
4. 유닛 테스트 추가
5. **대안 판단:** 실 크롤 결과(Track C) 에서 미매칭 0건이면 → 우선순위 하향, 로깅만으로 충분할 수 있음

---

### WAVE 3 — Validation (Wave 2 완료 후, 병렬 2 Track)

#### Track G: E2E Pipeline Test

1. Clean DB (`init_db.py`) → `seed_pitchers.py --harvest` → `crawl_today.py` → `/admin/generate-fortune` → `/admin/calculate-matchups` → `publish_matchups()`
2. `GET /api/today` → 실 매치업 데이터 반환 확인
3. `GET /api/matchup/{id}` → 5축 점수 + 상성 + 승자 판정 확인
4. 프론트엔드에서 해당 데이터 렌더 확인

#### Track H: Code Review (code-reviewer)

1. Wave 1–2 전체 diff 대상 리뷰
2. CLAUDE.md §2 scoring invariants 준수 확인
3. CLAUDE.md §4 coding conventions 준수 확인
4. 보안: CORS origin 하드코딩, API key 노출, SQL injection 등

---

### WAVE 4 — Deploy (Wave 3 완료 후)

#### Track I: 배포 실행

1. **Docker Compose 로컬 smoke** (docker CLI 필요)
   - `docker compose up --build` → `http://localhost:3000` 에서 FE, `:8000/api/today` 에서 BE 확인
   - uid 가이드: `sudo chown -R 1000 ./data`

2. **Railway BE 배포**
   - Postgres 프로비저닝 → `DATABASE_URL=postgresql+asyncpg://...`
   - 환경변수: `ANTHROPIC_API_KEY`, `FRONTEND_ORIGIN`, `SCHEDULER_ENABLED=false`
   - 워커 서비스 분리 (replicas=1, `SCHEDULER_ENABLED=true`)
   - `alembic upgrade head` startup 확인

3. **Vercel FE 배포**
   - `NEXT_PUBLIC_API_URL` → Railway BE URL
   - `NEXT_PUBLIC_USE_MOCK=false`
   - OG route edge runtime 실 PNG 반환 검증

4. **면책 고지 최종 copy** — 모든 페이지 + OG 카드에 "엔터테인먼트 목적" 노출 확인

---

### 에이전트 배정표 (병렬 실행 맵)

```
시간 →
────────────────────────────────────────────────────────────────

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

```
Track A (BE 스키마) → Track E (FE 연동) → Track G (E2E) → Track I (배포)
```

이 경로가 전체 일정을 결정. Track B/C/D 는 A 와 병렬이라 추가 시간 0.
Track F 는 C-1 이 non-blocker 이므로 E2E 와 병렬 가능 (배포 블로커 아님).

---

### Wave 1 실행 결과 (2026-04-16)

| Track | PR | 상태 | 요약 |
|------|----|------|------|
| **A** (BE 스키마) | #16 머지 (`3bc87e2`) | ✅ | `MatchupDetail` 5 필드 + `HistoryMatchup` 신설 + `accuracy.recent_7_days` Optional + `publish_matchups` `is_published.is_(False)` 필터 |
| **B** (FE api.ts) | #15 머지 (`8e687fa`) | ✅ | `getTodayMatchups()` → `TodayResponse.matchups` unwrap (G1) |
| **C** (크롤 smoke) | #17 OPEN | ⚠️ **FAIL (인프라)** | WAF IP-allowlist 블록, 코드 이슈 0건. 아래 상세 참조. |
| **D** (상성 감사) | #18 머지 (`bdff790`) | ✅ | `chemistry_calculator` 엣지 케이스 테스트 추가, README §2~3 정합 확인 |

#### Track C 상세 — 크롤러 smoke

브랜치: `claude/wave1-track-c-crawl-smoke-U81pk` (코드 수정 0건, 본 PROGRESS.md 기록만).

**판정: FAIL — WAF IP-allowlist 블록, 애플리케이션 레벨 이슈 아님.**

- `scripts/crawl_today.py --date 2026-04-16` dry-run → `fetch_today_schedule` 0 entries 반환.
- 실 HTTP 응답: `POST /ws/Main.asmx/GetKboGameList` → `403 Forbidden`, 21바이트, body `Host not in allowlist`, response header `x-deny-reason: host_not_allowed`. CDN/WAF 엣지에서 샌드박스 아웃바운드 IP 를 드롭.
- httpx DEBUG 트레이스로 확인한 요청 헤더는 전부 스펙 일치 — UA `FACEMETRICS/0.1 (+research)`, Referer `https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx`, `X-Requested-With: XMLHttpRequest`, Content-Type form-urlencoded, form body `date=20260416&leId=1&srId=0,1,3,4,5,7`. 403 은 헤더 값과 무관하게 IP 기반 거부.
- 로컬 DB 초기화는 정상: `python scripts/init_db.py` (alembic 0001+0002 upgrade head clean), `python scripts/seed_pitchers.py` (10명 시드). `daily_schedules` 에 2026-04-16 행 0건 (크롤이 0을 반환했으므로 `--write` 실행 무의미해서 skip).
- `crawler.py` 의 `_fetch_kbo` 는 `raise_for_status` 를 잡아서 `[]` 로 fail-soft — 기대 동작. 파서/셀렉터/레이트리밋 이슈 0건.

**매칭률**: 0/0 경기 선발 확정 · 0/0 pitcher_id 매칭 · 0/0 kbo_id 저장 (크롤 자체가 실패해 측정 불가).

**Track F C-1 참고용 unmatched queue**: 이번 런에서는 적재된 이름 자체가 없으므로 `data/crawler_review_queue.json` = `[]`. 다만 `data/pitchers_2026.json` 이 `teams_pending` (KT/KW) 때문에 8팀 × 1-2명 수준의 얕은 시드라, 실제 크롤 성공 시에도 다수 unmatched 예상됨 — C-1 review queue 구현 시 dedup + 최소 24h TTL + 수동 resolve UX 염두.

**코드 수정**: 없음. code-reviewer 라운드 불필요.

**언블록 옵션** (세션 외부 인프라):
1. 한국/미국 잔여 리전 residential/VPS IP 에서 재실행 (PROGRESS.md §세션 3, 세션 11 `verify_srid.py` 는 그 환경에서 200 OK 받은 바 있음).
2. CLAUDE.md §5 가 허용하는 유일한 out-of-band 경로인 **Playwright headless** fallback 활성화. 현재 `crawler.py` 에 스캐폴딩 없음 — 도입 시 Track C 후속 Wave 에서 `_fetch_kbo_playwright()` 별도 모듈로 추가.
3. 경량: 수동 fixture — `backend/tests/fixtures/kbo_20260416.xml` 같은 샌플 응답을 저장해두고 파서 회귀 전용 오프라인 테스트 유지. smoke 는 아니지만 파서 drift 조기 탐지에 유용.

**Wave 2 에 대한 함의**:
- **Track E (FE 실 데이터 연동)**: Track C 가 daily_schedules 를 채우지 못해도, 이미 시드된 pitcher + 수동으로 만든 matchup row 로 `/api/today` 가 동작하면 UI 연동 진행 가능. 단 실 크롤 파이프 end-to-end 검증은 Wave 3 Track G 로 이월.
- **Track F (C-1 review queue)**: 실 크롤 미매칭 샘플이 없으므로 "데이터 기반 우선순위 조정"이 불가. 스펙은 ULTRAPLAN 정의대로 진행하되 테스트는 합성 fixture(e.g., 의도적으로 오타낸 이름) 로 커버.

---

## Wave 2 — Ready-to-Dispatch Prompts

> 새 세션에서 바로 Agent 툴에 복사/붙여넣기 가능. Wave 1 전체 머지 완료(main=`11b72fc`) 를 전제로 함. 두 트랙은 완전 병렬 — 한 메시지에 두 Agent 호출을 담아 동시 실행.

### Wave 2 Track E — FE 실 데이터 연동 (react-ui-dev)

**브랜치 convention**: `claude/wave2-track-e-fe-live-integration-<short-id>`
**의존성**: Track A (#16) + Track B (#15) 머지 완료. Track C 는 FAIL 상태로 무시 가능(아래 Manual seed 경로 사용).
**목표**: `USE_MOCK=false` 로 전환 후 3개 페이지(/, /history, /pitcher/:id) 가 실 백엔드 API 로부터 데이터를 받아 정상 렌더되는지 검증 + 360px 모바일 QA.

**Prompt 본문** (Agent 에 그대로 전달):

```
Wave 2 Track E — FE 실 데이터 연동. 의존 Track A/B 는 main 에 머지 완료
(main=11b72fc). 이 작업은 FE 프론트엔드를 mock 모드에서 실 백엔드 API
모드로 전환하고 3 페이지 모두 실제 렌더링까지 확인하는 게 목표입니다.

사전 조건 셋업:
1. 새 브랜치 `claude/wave2-track-e-fe-live-integration-<본인id>` 생성.
2. 백엔드 DB 가 비어있으므로 아래 순서로 seed (Track C 크롤 실패 보완용
   manual path):
     cd backend
     python scripts/init_db.py
     python scripts/seed_pitchers.py  # --harvest 옵션은 실패해도 무시
   이 상태에서 `daily_schedules` 는 비어있어도 OK. `/api/today` 는
   빈 배열(matchups=[]) 을 반환해야 정상.
3. 매치업이 있는 시나리오를 보려면 `python scripts/create_sample_matchup.py`
   같은 새 스크립트(backend/scripts/) 를 만들어 (a) 시드된 투수 중 2명 선택
   (b) today 날짜로 `daily_schedules` + `matchups` row 1-2건을
   직접 INSERT. 점수는 face_scores/fortune_scores 도 채워야 레이더가 렌더됨.
   face_scores 는 season-fixed 이므로 `analyze-face/{id}` admin 호출로
   실 Claude 없이 hash fallback 이 동작하는지 확인.

FE 작업:
4. `frontend/.env.local` 에 다음 작성 (또는 `.env.example` 신설):
     NEXT_PUBLIC_USE_MOCK=false
     NEXT_PUBLIC_API_URL=http://localhost:8000
5. `npm run type-check` clean, `npm run build` clean.
6. `npm run dev` + backend `uvicorn app.main:app --reload` 동시 기동.
7. 페이지별 브라우저 smoke (CDP/headless 가능하면 자동화, 불가능하면
   수동 확인 후 스크린샷 요약):
     /                       : TodayMatchups hero + 매치업 카드 렌더
     /history?date=<today>  : 히스토리 테이블 (비어있어도 Empty state OK)
     /pitcher/1              : 투수 프로필 + 관상/운세 점수
8. DevTools 360px viewport 에서 카드/레이더/점수바 깨짐 여부 확인.
9. 모든 페이지에 Footer 의 "엔터테인먼트 목적" 면책 고지 노출 확인
   (CLAUDE.md §6 준수).

엣지 케이스:
10. `/api/today` 가 빈 배열일 때 Empty state UI (메시지 + 다음
    경기 안내) 가 제대로 뜨는지 확인. 없으면 `page.tsx` 또는
    `TodayMatchups` 컴포넌트에 추가.
11. API 실패 (예: 백엔드 꺼짐) 시 에러 배너/재시도 UI 동작 확인.
    현재 `fetchJson` 가 throw 하는지 조용히 빈 배열 반환하는지 확인 후
    필요시 보강 (단, 기존 mock 경로는 절대 깨지 말 것).

검증 · 산출물:
12. `npm run type-check` + `npm run build` 두 번 모두 clean.
13. PROGRESS.md 하단에 "### Wave 2 Track E 실행 결과" 섹션 추가 —
    실제 렌더 스크린샷/로그 + 수정한 파일 + Empty state 핸들링 결정.
14. code-reviewer 서브에이전트 라운드 1회 (CLAUDE.md §7).
15. 커밋 메시지 prefix: `feat(fe): Wave 2 Track E — …`.

건드리지 말 것: Track A/B 머지된 BE 스키마, 레거시 shine-border/timeline
stubs (지울 거면 지워도 되지만 새 의존 추가 금지).
```

**완료 판정**: `npm run build` clean + 3 페이지 수동 확인 + Empty state UI 결정 + PROGRESS.md 업데이트 + code-reviewer 통과 + PR open.

---

### Wave 2 Track F — C-1 Review Queue Harden (fastapi-backend-dev)

**브랜치 convention**: `claude/wave2-track-f-review-queue-<short-id>`
**의존성**: 없음(Track E 와 완전 병렬). Track C 인프라 FAIL 로 실 미매칭 샘플은 불가 → 합성 fixture 기반 개발.
**목표**: 이미 존재하는 `_append_review()` 쓰기 경로(`backend/app/services/crawler.py:157`) 를 하드닝하고 admin 읽기 엔드포인트 + dedup + TTL + 유닛 테스트를 추가.

**Prompt 본문** (Agent 에 그대로 전달):

```
Wave 2 Track F — C-1 review queue 하드닝. 이 트랙은 "from scratch" 가
아닙니다. `backend/app/services/crawler.py:157` 의 `_append_review()`
함수가 이미 `data/crawler_review_queue.json` 에 미매칭 투수 엔트리를
append-only 로 쓰고 있습니다. 누락된 건 (1) dedup (2) TTL (3) 관리자용
조회 엔드포인트 (4) 테스트 입니다. 목표는 Track C 인프라 복구 이전에도
합성 fixture 로 동작을 보증하는 것.

저장소 결정: JSON 파일 유지 (테이블 신설 금지).
 · 근거: 세션 3 convention (CLAUDE.md §5 근처), 운영 복잡도 최소화,
   Alembic 마이그레이션 불필요, 읽기 빈도 극저.
 · 위치는 기존 `REVIEW_QUEUE_PATH` 그대로 재사용.

사전 조건:
1. 새 브랜치 `claude/wave2-track-f-review-queue-<본인id>` 생성.
2. 기존 `_append_review` 시그니처와 현재 호출자 조사
   (`match_pitcher_name` 안에서 호출됨 — 라인 468 부근).

구현 항목:
3. Dedup: `_append_review(entry)` 가 동일 키로 이미 존재하면 skip.
   키 정의 = `(entry["team"], entry["crawled_name"], entry["game_date"])`.
   `crawled_name` 이 None 이고 `kbo_player_id` 가 있으면 kbo_player_id 도
   키에 포함. 중복이면 `created_at` 은 갱신하되 새 row append 금지.
4. TTL: `resolved=True` 인 엔트리 중 `resolved_at` 이 24h 이전인 것은
   append 시점에 정리 (lazy eviction). unresolved 는 삭제 금지 — 운영
   개입이 필요하기 때문.
5. Schema 확장 — 엔트리에 `created_at`(ISO8601 UTC), `resolved`(bool,
   기본 False), `resolved_at`(Optional) 추가. 기존 호출자 break 없도록
   `_append_review` 내부에서 기본값 채우기.
6. 신규 admin 엔드포인트: `GET /admin/review-queue`
     · `backend/app/routers/admin.py` 에 추가
     · 쿼리: `?unresolved_only=bool&limit=int`
     · 응답: `list[ReviewQueueItem]` (Pydantic v2, `app/schemas/response.py`)
     · 인증은 기존 admin 라우터 컨벤션 따름 (없으면 추가하지 말고
       기존 그대로).
7. 옵션 (포함 권장): `POST /admin/review-queue/resolve` 로 수동 resolve 토글.
   body: `{ team, crawled_name or kbo_player_id, game_date }`. 존재
   안 하면 404.

테스트 — 합성 fixture 로 커버:
8. `backend/tests/test_review_queue.py` 신설:
     · happy path: 3건 append → JSON 파일 3개 엔트리 확인
     · dedup: 동일 키로 같은 payload 2번 append → 1건만 유지
     · TTL: 25시간 전 resolved 엔트리 + 신규 append → 오래된 건 제거 확인
     · admin 엔드포인트: httpx AsyncClient 로 GET, unresolved_only 필터 확인
     · resolve 엔드포인트: 기존 엔트리 True 로 전환, 없는 엔트리 404
   fixture 예시: 의도적으로 오타낸 KBO 이름 ("원트성" 대신 "원정성",
   "쿠에바스" 대신 "쿠어바스"), 테스트 전용 임시 파일 경로 사용
   (tmp_path fixture — 실 `data/crawler_review_queue.json` 오염 금지).
9. `REVIEW_QUEUE_PATH` 가 함수 내부에서 매번 재계산되도록 monkeypatch
   가능하게 정리 (전역 상수는 유지하되 테스트 훅 용 override 경로 제공
   — 가장 깔끔한 건 `_append_review(entry, *, path: Path | None = None)`
   선택 인자).

비기능 요구사항:
10. Async everywhere. 라우터는 `async def`. JSON I/O 는 `aiofiles` 도입
    검토하되 동기 open 으로도 OK (small file, low freq).
11. 로그: 기존 WARNING 는 유지, dedup skip 은 DEBUG, resolve 는 INFO.
12. `.gitignore` 에 `data/crawler_review_queue.json` 이 이미 포함돼 있는지
    확인. 없으면 추가 — 테스트로 커밋될 위험 방지.

검증 · 산출물:
13. `cd backend && pytest -v` 전체 통과. 새 테스트 최소 5건 이상.
14. `python -c "from app.main import app; print(app.routes)"` import smoke.
15. PROGRESS.md 하단에 "### Wave 2 Track F 실행 결과" 섹션 추가 —
    JSON vs DB 선택 근거, dedup 키 정의, TTL 정책, 엔드포인트 사양,
    미구현 남은 것(있다면).
16. code-reviewer 서브에이전트 라운드 1회.
17. 커밋 메시지 prefix: `feat(backend): Wave 2 Track F — …`.

건드리지 말 것: `crawler.py` 의 HTTP/robots/파서 로직, Track C 인프라
언블록 옵션 (Playwright 도입 등은 별도 Wave 과제).
```

**완료 판정**: pytest 신규 5건+ green + admin 라우터 import smoke + PROGRESS.md 업데이트 + code-reviewer 통과 + PR open.

---

### 새 세션 시작 절차 (3 step)

1. `git pull origin main` → PROGRESS.md 이 섹션 확인.
2. 단일 메시지에 **두 Agent 를 병렬 호출** (react-ui-dev + fastapi-backend-dev). 각각 위 Prompt 본문을 통째로 전달.
3. 두 트랙 완료 후 Wave 3 (Track G E2E + Track H code-review) 프롬프트를 별도로 준비.

---

### Wave 2 Track F 실행 결과 (2026-04-16, v2 재작업)

> **주의**: 최초 Track F 브랜치 (`claude/wave2-track-f-review-queue-fastapi-backend-dev`, PR #22) 는 agent worktree 가 stale base (`9281df3`, 세션 3) 에서 생성됐음이 PR 오픈 후 발견돼 DIRTY 머지 불가 판정. 해당 브랜치가 그대로 머지되면 Phase 4 admin 라우터 5개 + Track A BE 스키마 전체를 덮어써서 삭제됨. PR #22 는 close 후 main 기준 `claude/wave2-track-f-review-queue-v2` 브랜치에서 add-only 전략으로 재작업 (본 PR).

#### 저장소 결정: JSON 파일 유지

DB 테이블 신설 없이 기존 `data/crawler_review_queue.json` 파일 유지.
근거:
- 읽기/쓰기 빈도 극저 (크롤러 실패 시만 append, 관리자 조회 시만 read)
- Alembic 마이그레이션 불필요 → 운영 복잡도 최소화
- 동시성 위험 있으나 08:00 crawl_job 이 단일 프로세스 내 순차 실행 — 현재 트래픽 수준에서 허용 가능

#### Dedup 키 정의

```
(team, crawled_name, game_date, kbo_player_id)
```

- `crawled_name` 이 None 이 아닐 때: `kbo_player_id` 는 None (key에서 제외)
- `crawled_name` 이 None 일 때: `kbo_player_id` 포함 (동명이인 없는 ID 구분)
- 중복 감지 시: 새 row 추가 금지, 기존 row 의 `created_at` 만 갱신 (lazy refresh)

#### TTL 정책

- **대상:** `resolved=True` + `resolved_at` 이 24시간 이전인 엔트리
- **발동:** `_append_review()` 호출 시 (lazy eviction) — 읽기 경로에서는 미발동
- **비대상:** `resolved=False` 엔트리는 운영자 개입이 필요하므로 절대 삭제 금지

#### 스키마 확장 (기존 호출자 호환)

`_append_review(entry, *, path=None)` 내부에서 기본값 stamp:
- `created_at`: ISO8601 UTC (최초 진입 시)
- `resolved`: False
- `resolved_at`: None

기존 caller (`match_pitcher_name`) 에서 `queued_at` 필드 제거, `date` → `game_date` 키 이름 통일.

#### 엔드포인트 사양

| 메서드 | 경로 | 쿼리/바디 | 응답 |
|--------|------|-----------|------|
| GET | `/admin/review-queue` | `?unresolved_only=bool&limit=int` | `list[ReviewQueueItem]` |
| POST | `/admin/review-queue/resolve` | `ReviewQueueResolveRequest` (JSON body) | `ReviewQueueItem` (200) or 404 |

인증: 없음 — 기존 admin 라우터 컨벤션 동일 (네트워크/프록시 레이어 위임).

#### 테스트 커버리지 (22 건)

- `TestAppendReview`: happy / schema stamp / dedup / dedup refresh / 다른 game_date 분리 / kbo_player_id 키 / TTL 오래된 resolved 제거 / TTL 최근 resolved 유지 / TTL unresolved 절대 유지 (9건)
- `TestReviewEntryKey`: primary key / kbo_player_id 포함 조건 / 이름 있을 때 id 무시 (3건)
- `TestTtlEvict`: 오래된 resolved 제거 / 최근 resolved 유지 / unresolved 유지 (3건)
- `TestAdminGetReviewQueue`: unresolved_only 필터 / 전체 / limit cap (3건)
- `TestAdminResolveEndpoint`: 성공 / 404 / kbo_player_id 경로 / ASGI 통합 smoke (4건)

fixtures 은 `tmp_path` 로 격리, 실 `data/crawler_review_queue.json` 무오염.

#### 변경 파일 (main 기준 add-only)

- `.gitignore` — `data/crawler_review_queue.json` 추가
- `backend/app/services/crawler.py` — `_review_entry_key`, `_ttl_evict` 추가 + `_append_review` dedup/TTL/path-override 확장 + caller 엔트리에서 `queued_at` 제거 + `date` → `game_date` 통일
- `backend/app/schemas/response.py` — `ReviewQueueItem`, `ReviewQueueResolveRequest` 신설 (기존 Track A 스키마 유지)
- `backend/app/routers/admin.py` — `/admin/review-queue` GET + `/admin/review-queue/resolve` POST 추가 (기존 Phase 4 admin 라우트 5개 유지)
- `backend/tests/test_review_queue.py` — 22 테스트 신설

#### 미구현 (의도적 미포함)

- `_append_review` 동시성 안전 (fcntl lock / DB 승격) — 08:00 cron 단일 프로세스 내 순차라 현재 수용 가능. Postgres 전환 시 재검토
- Alembic 마이그레이션 — JSON 유지 결정으로 불필요
- 생산 환경 인증 (auth guard) — 프록시/네트워크 레이어 위임, 기존 admin 컨벤션 유지
