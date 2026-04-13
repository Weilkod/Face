# FACEMETRICS — Implementation Progress

> **자동 아카이브 지침:**  
> 완료된 Phase 섹션이 **다음 Phase 착수 후** 또는 **2주 이상 경과** 했을 때,  
> 세부 구현 내역은 `ARCHIVE.md` 로 이동하고 이 파일에는 핵심 결과만 체크리스트로 남긴다.

- **Spec:** `README.md` + `CLAUDE.md`
- **DB URL (dev):** `sqlite+aiosqlite:///data/facemetrics.db`
- **Stop hook:** `.claude/hooks/code-reviewer-gate.sh` — 코드 변경 시 자동 code-reviewer 호출

---

## 완료 이력 (상세 → `ARCHIVE.md`)

- [x] **Phase 1** — 기반 구축 ✅ (2026-04-13)  
  FastAPI 스캐폴딩, 5 테이블 DB, 투수 10명 시드, init/seed 스크립트

- [x] **Phase 2** — AI 엔진 ✅ (2026-04-13)  
  관상(Claude Vision) + 운세(Claude Text) + 상성(룰 기반) + scoring_engine  
  ⚠️ Claude API 키 없이는 캐시 미스 경로 미검증 — §B 필수

- [x] **Phase 3** — 크롤러 + 스케줄러 ✅ (2026-04-13)  
  KBO `GetKboGameList` 단일 소스, `/ws/` robots carve-out, DB write, 5개 KST 잡

- [x] **Phase 4** — API 라우터 ✅ (2026-04-13)  
  커밋: `72a5803` → 코드리뷰 수정 `1ee88ce` → 백엔드 추가 수정 `e31c3c1`, `f4fba33`  
  - **클라이언트:** GET `/api/today`, `/api/matchup/{id}`, `/api/pitcher/{id}`, `/api/history`, `/api/accuracy`
  - **어드민:** POST `/admin/crawl-schedule`, `/admin/analyze-face/{id}`, `/admin/generate-fortune`, `/admin/calculate-matchups`, `/admin/update-result/{id}`
  - `app/schemas/response.py` — Pydantic v2 응답 스키마 (chemistry_score ge/le, game_time/series_label)
  - `app/routers/_helpers.py` — 공유 `pitcher_summary()` 헬퍼
  - `matchup.py` — face/fortune 점수 배치 IN 쿼리 (4 SELECT → 2)

- [x] **Phase 5** — 프론트엔드 ✅ (2026-04-13)  
  커밋: `1d38c0c` → 수정 `726a3ea`  
  - **Next.js 14** App Router, TypeScript, Tailwind (draft.html 픽셀 매칭)  
  - **Pages:** `/` (히어로 + 아코디언 매치업 리스트), `/history` (날짜 선택 + 적중률), `/pitcher/[id]` (투수 프로필)
  - **Components:** `MatchupCard` (expand 시 lazy detail fetch), `RadarChart` (SVG 5축), `ScoreBar`, `AxisDetail`, `Footer`
  - **api.ts:** USE_MOCK env var, getHistory `.matchups` 언래핑, `getMatchupDetail` lazy fetch
  - **Mock data:** 3개 매치업 (엔스/곽빈, 김광현/쿠에바스, 네일/페디)
  - `npm run build` clean ✅, 레거시 shine-border/timeline 삭제 ✅

---

## 현재 상태 (세션 4 완료, 2026-04-13)

Phase 1~5 코드 구현 완료. 브랜치 `claude/phase-5-no-api-5jocG`, 워킹 트리 클린.  
**미완료 항목은 아래 §잔여 작업 참조.**

---

## 잔여 작업 (우선순위 순)

### 🔴 Blocker — 배포 전 필수

#### B. Phase 2 AI 실검증
- [ ] `backend/.env` 에 `ANTHROPIC_API_KEY` 입력 후 파이프라인 수동 실행
  ```bash
  python -c "import asyncio; from app.scheduler import analyze_and_score_matchups; asyncio.run(analyze_and_score_matchups())"
  ```
  - [ ] Claude Vision 첫 호출 → `face_scores` row 로그 확인
  - [ ] Claude Text 첫 호출 → `fortune_scores` row 로그 확인
  - [ ] 동일 `(pitcher_id, date)` 재실행 → DB 캐시 히트, Claude 호출 0회 확인
- [ ] Vision 성공 + Text 실패 시 고아 row 방지 — savepoint 또는 문서화
- [ ] `analyze_and_score_matchups` except 분기 — Claude mock + rollback 유닛 테스트

#### E. 브라우저 실기동 테스트 (Phase 5 완료 기준)
- [ ] `npm run dev` + 360px 모바일 뷰포트에서 전체 플로우 확인
  - 메인 페이지 히어로 → 매치업 카드 렌더링
  - `FACEMETRICS 상세` 클릭 → 아코디언 확장 + 레이더 차트
  - `/pitcher/[id]` 투수 프로필 페이지
  - `/history` 날짜 선택 + 적중률 카드
- [ ] TypeScript 타입 체크: `npm run type-check`

### 🟡 Important — 품질/정합

#### D. 프론트엔드 잔여
- [ ] **D-1** `api.ts:73` `as HistoryMatchup[]` 캐스팅 제거 (no-op, 가독성)
- [ ] **D-2** `/pitcher/[id]/page.tsx` — 백엔드 `PitcherDetail` 스키마와 정렬  
  (현재 `face_scores` + `today_fortune` 분리 구조 미반영 가능성)
- [ ] **D-3** `PitcherProfile` 타입 → `PitcherDetail`로 정렬 또는 제거  
  (`hand` 필드, `scores` 합산 구조 백엔드 불일치)
- [ ] **D-4** Share card PNG 생성 (`html-to-image`) — Phase 6 범위

#### F. 백엔드 잔여
- [ ] **F-1** `Matchup` 모델에 `chemistry_comment` 컬럼 추가  
  (현재 `matchup.py`에서 `chemistry_comment=None` 하드코딩)
- [ ] **F-2** `MatchupSummary`의 `game_time`/`series_label` 실제 값 채우기  
  (`daily_schedules` JOIN 또는 `Matchup` 컬럼 추가)
- [ ] **F-3** `/api/history` 응답에 `actual_winner`/`prediction_correct` 포함  
  (현재 `MatchupSummary` 기반이므로 이 필드 없음 — `HistoryMatchup` 확장 필요)
- [ ] **F-4** `AccuracyResponse` 메모리 풀스캔 → SQL COUNT/SUM 쿼리로 교체

### 🟢 Nice-to-have

#### A. 크롤러 마무리
- [ ] **A-5** `pitchers.kbo_player_id` 컬럼 + ID 기반 매처 (동명이인 안전망)
- [ ] **A-6** `seed_pitchers.py` KBO 프로필 수확기 (생년월일/사진 자동 시드)

#### C. 운영 잔여
- [ ] `_append_review` dedup/concurrency
- [ ] `publish_matchups` `is_published.is_(False)` 필터
- [ ] Alembic 도입 여부 결정 (prod Postgres 전환 전)

---

## Phase 6 로드맵

- docker-compose, Vercel + Railway 배포, GitHub Actions CI 게이트
- 면책 고지 전 페이지 노출 확인
- Share card PNG (`html-to-image`)
- SNS 자동 포스팅 (확장)
