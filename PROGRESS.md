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

---

## 현재 상태 (세션 5 기준, 2026-04-13)

Phase 4 라우터 + Phase 5 프론트엔드 구조 + Phase 6 **Alembic** & **@vercel/og** 도입 완성.  
`npm run build` clean (5개 라우트, OG edge route 포함), 백엔드 alembic upgrade/downgrade 라운드트립 OK.  
**세션 4 코드 리뷰어 BLOCK 이슈들 (C1~C5, I1~I6)은 여전히 미수정 상태 — 다음 세션 우선 작업.**

---

## [WPI] 세션 5 인계 (2026-04-13)

### 브랜치
`claude/phase-5-no-api-5jocG`

### 세션 시작 전 커밋 필요 (staged 상태)
```
git commit -m "chore: linter type changes, delete legacy UI stubs, gitignore next-env.d.ts"
git push
```
스테이지된 내용:
- `frontend/src/types/index.ts` — 린터 수정 반영
- `frontend/components/ui/shine-border.tsx`, `timeline.tsx` — 삭제
- `frontend/next-env.d.ts` — Next.js 자동생성 (`.gitignore` 추가됨)
- `.gitignore` — `frontend/next-env.d.ts` 항목 추가

### 코드 리뷰어 BLOCK 이슈 (최우선 수정 대상)

#### 🔴 CRITICAL

**C1 — `frontend/src/lib/api.ts:17`**  
`USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true" || true` → `|| true` 제거  
실제 API가 영구 차단됨

**C2 — `frontend/src/app/page.tsx:22`**  
`getTodayMatchups()` 반환 타입 `MatchupSummary[]`을 `as MatchupDetail[]` 캐스팅  
→ expand 시 `home_scores`/`away_scores`/`chemistry` 런타임 오류  
해결 방법: MatchupCard 열 때 `/api/matchup/{id}` 별도 fetch (권장)

**C3 — `frontend/src/app/page.tsx:27`**  
`formatDateKo("2026-04-13")` 날짜 하드코딩 → `new Date()` 또는 API `date` 필드 사용

**C4 — `frontend/src/types/index.ts:43-44`**  
`MatchupSummary.game_time`, `series_label` — 백엔드 스키마에 없는 필드  
→ 백엔드 `MatchupSummary`에 추가하거나 프론트 타입에서 제거 (백엔드 추가 권장)

**C5 — `frontend/src/types/index.ts:114-119`**  
`PitcherProfile.hand` — 백엔드 없음, `scores: PitcherScores | null` — 백엔드는 `face_scores` + `today_fortune` 분리  
→ `PitcherProfile` 을 `PitcherDetail`과 정렬하거나 삭제

#### 🟡 WARNING

**I1 — `history/page.tsx:21`** — `yesterday()` 내 `new Date("2026-04-13")` 하드코딩 → `new Date()`

**I2 — `page.tsx:47,54`** — `style={{ color: "#0A192F" }}` 등 인라인 스타일 → Tailwind 커스텀 색상 토큰 사용

**I3 — `response.py:87`** — `MatchupSummary.chemistry_score` Field에 `ge=0.0, le=4.0` 누락

**I4 — `matchup.py:123-157`** — face/fortune 점수 4개 개별 쿼리 → `IN` 배치 로드 미적용

**I5 — `api.ts:71`** — `getHistory()` 가 `HistoryResponse` 객체를 배열로 반환 (`.matchups` 언래핑 누락)

**I6 — `history/page.tsx:83`** — `max="2026-04-12"` 하드코딩 → `new Date().toISOString().split("T")[0]`

#### 🟢 NITS
- `ScoreBar.tsx:16` `maxScore` prop 미사용 dead parameter

### 다음 세션 작업 순서

1. staged 파일 커밋 + 푸시
2. `react-ui-dev` 에이전트에 C1~C3, I1~I2, I5~I6 프론트엔드 이슈 수정 위임
3. `fastapi-backend-dev` 에이전트에 C4(백엔드 game_time/series_label 추가), I3, I4 위임 — **병렬 실행 가능**
4. `code-reviewer` 게이트 통과 확인
5. 이후 Phase 5 미구현 항목:
   - 브라우저 실기동 테스트 (360px 모바일 뷰포트)
   - PitcherPage 투수 프로필 완성 (face_scores + today_fortune 분리 구조)
   - 히스토리 페이지 실제 날짜 date picker 동작 확인
   - Share card (PNG 저장) 기능 — Phase 6 범위

---

## 진행 중 TODO

### A. 크롤러 마무리 (nice-to-have)

- [ ] **A-5.** `pitchers` 에 `kbo_player_id` 컬럼 추가 + `match_pitcher_by_kbo_id()` 헬퍼  
- [ ] **A-6.** `seed_pitchers.py` 에 KBO 프로필 수확기 추가  

### B. Phase 2 AI 실검증 (blocker — 배포 전 필수)

- [ ] `.env` 에 `ANTHROPIC_API_KEY` → 파이프라인 실행 검증
- [ ] 고아 score row 문제 — Vision 성공 + Text 실패 시 savepoint
- [ ] `analyze_and_score_matchups` except 분기 — Claude mock + rollback 유닛 테스트

### C. 운영 잔여 (non-blocker)

- [ ] `_append_review` dedup, concurrency
- [ ] `publish_matchups` — `is_published.is_(False)` 필터 추가
- [ ] `analyze_and_score_matchups` — pitcher `IN [...]` 배치 로드
- [x] Alembic 도입 — 세션 5 완료 (`backend/alembic/`, init_db.py 전환)

### D. Phase 5 프론트엔드 잔여

- [ ] **D-1 (CRITICAL)** api.ts `|| true` 제거 (C1)
- [ ] **D-2 (CRITICAL)** page.tsx 타입 캐스팅 수정 + expand 시 matchup detail fetch (C2)
- [ ] **D-3** 하드코딩 날짜 전부 동적으로 교체 (C3, I1, I6)
- [ ] **D-4** 인라인 스타일 → Tailwind 토큰 (I2)
- [ ] **D-5** api.ts getHistory() `.matchups` 언래핑 (I5)
- [ ] **D-6** 백엔드 MatchupSummary에 game_time/series_label 추가 (C4)
- [ ] **D-7** PitcherProfile 타입 PitcherDetail과 정렬 (C5)
- [ ] **D-8** 360px 모바일 뷰포트 실기동 테스트
- [x] **D-9** Share card PNG 생성 — `@vercel/og` Edge route + ShareButton (세션 5)

---

## Phase 6 로드맵

- docker-compose, 면책 고지, Vercel + Railway 배포, GitHub Actions 게이트, 공유 카드 PNG
