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
  ⚠️ Python 3.11+ + SQLAlchemy ≥ 2.0 필수

- [x] **Phase 2** — AI 엔진 ✅ (2026-04-13)  
  관상(Claude Vision) + 운세(Claude Text) + 상성(룰 기반) + scoring_engine  
  ⚠️ Claude API 키 없이는 캐시 미스 경로 미검증 — §B 필수

- [x] **Phase 3** — 크롤러 + 스케줄러 ✅ (2026-04-13)  
  `GetKboGameList` 단일 소스, `/ws/` robots carve-out, 5개 KST 잡, FastAPI lifespan  
  smoke: `date(2026,4,14)` → 5경기 5/5 선발 확정 수신

- [x] **§A-5/A-6** — kbo_player_id + seed 지원 ✅ (2026-04-13)  
  `pitchers.kbo_player_id`, `daily_schedules.home/away_starter_kbo_id`, `match_pitcher_by_kbo_id()`,  
  ID 우선→name 폴백 매칭, idempotent SQLite ALTER, `seed_pitchers.py` kbo_id 필드 지원  
  ⚠️ 프로필 페이지 수확기(자동 시드)는 미구현 — nice-to-have

- [x] **§C-1/C-2** — 운영 개선 ✅ (2026-04-13)  
  `publish_matchups` `is_published.is_(False)` 필터, `_append_review` dedup

- [x] **Phase 4** — API 라우터 ✅ (2026-04-13)  
  `/api/today`, `/api/matchup/{id}`, `/api/pitcher/{id}`, `/api/history`, `/api/accuracy`,  
  `/admin/crawl-schedule`, `/admin/analyze-face/{id}`, `/admin/generate-fortune`,  
  `/admin/calculate-matchups`, `/admin/update-result/{id}`  
  Pydantic v2 응답 스키마, `_helpers.py` 공유 헬퍼, disclaimer 전 응답 포함

---

## 현재 상태 (세션 4 기준, 2026-04-13)

백엔드 거의 완성. `uvicorn app.main:app` 기동 시 15개 라우트 등록, DB/스케줄러 정상 작동.  
**남은 blocker:** §B (Claude API 키 꽂고 Vision/Text 파이프 실검증) — API 키 없어서 이월.  
**다음 큰 작업:** Phase 5 (React 프론트엔드). API 키 없어도 진행 가능.

---

## 진행 중 TODO

### B. Phase 2 AI 실검증 (blocker — 배포 전 필수)

- [ ] `backend/.env` 생성 (`backend/.env.example` 복사 후 `ANTHROPIC_API_KEY=sk-ant-...` 입력, 커밋 금지)
- [ ] `python -c "import asyncio; from app.scheduler import analyze_and_score_matchups; asyncio.run(analyze_and_score_matchups())"` 수동 실행
  - [ ] Claude Vision 첫 호출 → `face_scores` row 기록 로그 확인
  - [ ] Claude Text 첫 호출 → `fortune_scores` row 기록 로그 확인
  - [ ] 동일 `(pitcher_id, date)` 재실행 → DB 캐시 히트, Claude 호출 0회 확인
- [ ] 고아 score row — Vision 성공 + Text 실패 시 savepoint 도입 (`claude-ai-integrator` 위임)
- [ ] `analyze_and_score_matchups` except 분기 — Claude mock + rollback 유닛 테스트

### C. 운영 잔여 (non-blocker)

- [x] `_append_review` dedup ✅
- [x] `publish_matchups` is_published 필터 ✅
- [ ] `_append_review` concurrency — fcntl lock 또는 `review_queue` DB 테이블 승격
- [ ] `analyze_and_score_matchups` — pitcher `IN [...]` 배치 로드 (현재 게임당 SELECT 2회)
- [ ] Alembic 도입 여부 결정 (prod Postgres 전환 전. dev SQLite 는 수동 ALTER 허용)

### A. 크롤러 잔여 (nice-to-have)

- [x] A-5 `kbo_player_id` 컬럼 + ID 우선 매칭 ✅
- [ ] A-6 프로필 수확기 — `/ws/Player.asmx` ASMX 엔드포인트 검증 후 `seed_pitchers.py --harvest` 구현  
  → 콜업·트레이드·외국인 영입 신인 자동 대응 (`kbo-data-crawler` 위임)

---

## 다음 세션 시작 명령

```
세션 4 완료. Phase 4 백엔드 API 라우터 완성, §A-5 kbo_player_id, §C 운영 개선.
앱 기동 확인됨 (15개 라우트).

옵션 1 — API 키 있을 때 (§B 우선):
  backend/.env 에 ANTHROPIC_API_KEY 주입 후
  PYTHONPATH=backend python -c "
    import asyncio
    from app.scheduler import analyze_and_score_matchups
    asyncio.run(analyze_and_score_matchups())
  "
  → Vision/Text 첫 호출 로그 + 두 번째 호출 캐시 히트 확인
  담당: claude-ai-integrator 에이전트

옵션 2 — API 키 없을 때 (Phase 5):
  React 프론트엔드 시작 — TodayMatchups 페이지, MatchupCard 컴포넌트, 레이더 차트
  frontend/preview/draft.html 의 디자인 토큰 (오프화이트+흰카드+coral #F26B4E+mint #059669) 기준
  담당: react-ui-dev 에이전트

세션 전 확인사항:
- CLAUDE.md §2 scoring invariants (관상 시즌 고정, 운세 결정론적 캐시, 상성 clamp [0,4])
- CLAUDE.md §5 단일 소스 (koreabaseball.com, /ws/ carve-out만)
- CLAUDE.md §6 disclaimer 전 페이지 필수
```

---

## Phase 5~6 로드맵

- **Phase 5:** `frontend/` — React 18 + TypeScript + Tailwind, Recharts 레이더 차트  
  Pages: `TodayMatchups` → `MatchupDetail` → `PitcherPage` + `HistoryPage`  
  Mobile-first (360px), share-card PNG 내보내기
- **Phase 6:** docker-compose, Vercel(FE) + Railway(BE) 배포, GitHub Actions CI 게이트, 공유 카드
