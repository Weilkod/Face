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

- [x] **Phase 2** — AI 엔진 ✅ (2026-04-13)  
  관상(Claude Vision) + 운세(Claude Text) + 상성(룰 기반) + scoring_engine  
  ⚠️ Claude API 키 없이는 캐시 미스 경로 미검증 상태 — §B 필수

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

## 현재 상태 (세션 7 기준, 2026-04-14)

세션 6 사후 리뷰 잔여 (N1/N2/N3) + 세션 4/5 BLOCK 잔여 (D-7 `PitcherProfile` 타입 정렬, D-8 360px 모바일 smoke) 모두 완료. N1/N2 는 Korean Windows (cp949) 환경에서 alembic 이 `alembic.ini` 를 읽을 때 `UnicodeDecodeError` 로 터지던 pre-existing 인코딩 버그 (L25 em dash) 까지 제거한 뒤 실기동 검증 완료.

**배포 이전 남은 blocker 는 §B (AI 실검증) 뿐이며, 나머지는 nits/운영 잔여/Phase 6 배포 작업.**

세션 7 산출물:
- PR #4 (`claude/session-7-nits-and-d7`) 5 커밋: N1+N2+N3 / D-7 / PROGRESS / D-8 확정 / alembic.ini cp949 fix.

---

## [WPI] 세션 8 인계 (2026-04-14)

### 시작 상태
- PR #4 머지 여부를 먼저 확인. 머지됐으면 `main` 에서 신규 브랜치 분기, 아직이면 PR 리뷰/수정 이어가기.
- `origin/main` 기준 (PR #4 전): 세션 6 완료 상태 (`d4418bd`).
- `.env` 에 `ANTHROPIC_API_KEY` 여전히 없음 → §B 착수 전 반드시 확인.
- 로컬 venv (`.venv/`) 및 `/tmp/facemetrics_n2_test.db` 는 세션 7 의 일회성 검증 부산물 — 세션 8 시작 시 필요 없으면 정리.

### 첫 턴에 할 일
1. PR #4 상태 확인 후 브랜치 분기 전략 결정.
2. §B 시작 여부 결정 — `.env` 에 `ANTHROPIC_API_KEY` 가 주입됐는지 먼저 확인. 없으면 사용자에게 요청, 주입되면 B-1 부터 순차 진행.
3. §B 가 아직 막혀 있으면 Phase 6 배포 작업의 선행 준비 (Dockerfile, docker-compose, CI 설정 파일 스켈레톤) 로 전환하거나, D-4 partial / H1-H2 stop hook 보강 / A-5-A-6 크롤러 nice-to-have 같은 non-blocker 작업 정리.

### 세션 7 에서 완료된 항목 (참고용)

| ID | 상태 | 비고 |
|---|---|---|
| N1 `models/matchup.py` `server_default=text("0")` | ✅ | 세션 7 PR #4 |
| N2 `scripts/init_db.py` URL 중복 주입 제거 | ✅ | 세션 7 PR #4, Python 3.12 + venv 로 `alembic upgrade head` 5 테이블 생성 실검증 |
| N3 `components/ScoreBar.tsx` `maxScore` prop 제거 | ✅ | 세션 7 PR #4 |
| C5 / D-7 `PitcherProfile` 타입 정렬 | ✅ | 세션 7 PR #4, mock 경로까지 `PitcherDetail` 로 통합, `tsc --noEmit` + `npm run build` clean |
| D-8 360px 모바일 smoke | ✅ | `next dev` + 세 경로 200 + 정적 분석 + 사용자 로컬 DevTools 360×800 육안 검수 통과 |
| alembic.ini cp949 fix | ✅ | L25 em dash → `--` 치환. Korean Windows 환경에서 `init_db.py` 가 돌아가게 됨 (pre-existing 인코딩 버그) |

세션 4/5 BLOCK 잔여 중 아직 열려 있는 항목:

- **I2 Tailwind 토큰화 (D-4 partial)** — `page.tsx:46` 의 arbitrary value `text-[#0A192F]` 를 `tailwind.config.ts` 에 `ink.title` 토큰 추가 후 `text-ink-title` 로 재작업. nit 수준.

### Stop hook 보강 (계속 이월)

`.claude/hooks/code-reviewer-gate.sh` 는 `git diff --name-only HEAD` 로 working tree 만 보기 때문에, commit 직후 stop 턴은 항상 clean → silent pass. 다음 중 하나로 보강:

- [ ] **H1** 현재 브랜치의 `git diff origin/main...HEAD --name-only` 도 함께 보고, 리뷰 마커 (`.claude/.last-reviewed-hash`) 에 커밋 해시도 포함시켜 "해당 커밋이 리뷰된 적 있는지" 판단
- [ ] 또는 **H2** 세션 마지막 턴이 `git commit` / `git push` 를 포함하면 명시적으로 code-reviewer 호출을 요구하는 차단 규칙 추가

세션 7 은 수동으로 `code-reviewer` 서브에이전트를 커밋 전에 호출해서 (CRITICAL/MAJOR 0, Minor 3 → 전부 반영) 보완했지만, 구조적 개선은 여전히 미뤄진 상태.

---

## 진행 중 TODO

### A. 크롤러 마무리 (nice-to-have)

- [ ] **A-5.** `pitchers` 에 `kbo_player_id` 컬럼 추가 + `match_pitcher_by_kbo_id()` 헬퍼  
- [ ] **A-6.** `seed_pitchers.py` 에 KBO 프로필 수확기 추가  

### B. Phase 2 AI 실검증 (blocker — 배포 전 필수)

- [ ] **B-1** `.env` 에 `ANTHROPIC_API_KEY` → 파이프라인 실행 검증 (캐시 미스 경로)
- [ ] **B-2** 고아 score row 문제 — Vision 성공 + Text 실패 시 savepoint
- [ ] **B-3** `analyze_and_score_matchups` except 분기 — Claude mock + rollback 유닛 테스트

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
