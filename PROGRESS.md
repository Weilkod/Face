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

## 현재 상태 (세션 8 기준, 2026-04-14)

§B (Phase 2 AI 실검증) **완료**. 배포 이전 남은 blocker 는 더 이상 없음 — Phase 6 배포 작업, H1/H2 stop hook 보강, D-4 partial 토큰화, A-5/A-6 크롤러 nice-to-have 가 잔여.

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

---

## [WPI] 세션 9 인계 (2026-04-14)

### 시작 상태
- 세션 8 PR 머지 여부 먼저 확인. 머지됐으면 `main` 에서 새 브랜치 분기.
- §B 모두 완료 — `.env` 에 `ANTHROPIC_API_KEY` 가 들어 있는 상태로 `verify_ai_pipeline.py` 와 `pytest backend/tests/` 가 재현 가능.
- 잔여물 정리: `.venv/`, `data/facemetrics.db` (실 Claude 응답이 캐시됨), `/tmp/facemetrics_b3_test.db` 는 일회성 — 세션 9 시작 시 필요 없으면 삭제.

### 첫 턴에 할 일
1. 세션 8 PR 상태 확인 → 분기 전략 결정.
2. 다음 중 하나로 진행:
   - **Phase 6 배포 스켈레톤** (Recommended) — Dockerfile, docker-compose, GitHub Actions CI yml. README §8 / Phase 6 로드맵의 첫 단계.
   - **H1/H2 Stop hook 보강** — 구조적 silent-pass 재발 방지. (세션 6/8 에서 우회 발생, 매번 수동 호출 필요)
   - **D-4 partial Tailwind 토큰화** — `page.tsx:46` 의 `text-[#0A192F]` → `text-ink-title`. 1줄 nit.
   - **A-5/A-6 크롤러 nice-to-have** — `pitchers.kbo_player_id` 컬럼 + matcher + seed 수확기. Alembic 마이그레이션 동반.

### Stop hook 보강 (계속 이월)

`.claude/hooks/code-reviewer-gate.sh` 가 `git diff --name-only HEAD` 만 보기 때문에 commit 직후 stop 턴은 항상 clean → silent pass. 다음 중 하나로 보강:

- [ ] **H1** 현재 브랜치의 `git diff origin/main...HEAD --name-only` 도 함께 보고, 리뷰 마커에 커밋 해시 포함
- [ ] **H2** 세션 마지막 턴이 `git commit/push` 를 포함하면 명시적으로 code-reviewer 호출 요구

세션 8 도 수동으로 `code-reviewer` 서브에이전트를 커밋 전에 호출해서 보완했지만 구조적 개선은 여전히 미뤄진 상태.

세션 4/5 BLOCK 잔여 중 아직 열려 있는 항목:
- **I2 Tailwind 토큰화 (D-4 partial)** — nit 수준.

---

## 진행 중 TODO

### A. 크롤러 마무리 (nice-to-have)

- [ ] **A-5.** `pitchers` 에 `kbo_player_id` 컬럼 추가 + `match_pitcher_by_kbo_id()` 헬퍼  
- [ ] **A-6.** `seed_pitchers.py` 에 KBO 프로필 수확기 추가  

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
- [ ] **D-4 (partial)** I2 Tailwind 토큰화 (arbitrary value → 토큰, nit)
- [x] **D-7** `PitcherProfile` 삭제 → `PitcherDetail` 통합 (세션 7, 프론트 어댑터 레이어)
- [x] **D-8** 360px 모바일 뷰포트 smoke test — dev 서버 + 3 경로 200 + 정적 분석 + 사용자 로컬 DevTools 육안 검수 통과 (세션 7)
- [x] **D-9** Share card PNG 생성 — `@vercel/og` Edge route + ShareButton (세션 5)

### E. 사후 리뷰 Nits (세션 6 → 7 이월)

- [x] **N1** `models/matchup.py` `server_default=text("0")` (세션 7)
- [x] **N2** `scripts/init_db.py` URL 중복 주입 제거 (세션 7)
- [x] **N3** `components/ScoreBar.tsx` 미사용 `maxScore` prop 제거 (세션 7)

---

## Phase 6 로드맵

- docker-compose, 면책 고지, Vercel + Railway 배포, GitHub Actions 게이트, 공유 카드 PNG
