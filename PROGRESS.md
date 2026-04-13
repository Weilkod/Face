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

---

## 현재 상태 (세션 3 기준, 2026-04-13)

크롤러 `GetKboGameList` 단일 소스로 재작성 완료. §A carry-over 의 A-2/A-3/A-4/A-7 전부 해소.  
A-5/A-6 는 blocker 에서 nice-to-have 로 강등.  
**다음 우선 작업:** §B (Claude API 키 꽂고 10:30 파이프 실검증)

---

## [WPI] 세션 4 인계 (2026-04-13, 작업 장소 이동)

**결정된 다음 경로:** §B 먼저 진행.

**재개 시 첫 번째로 확인할 블로커:**
- `backend/.env` 가 현재 **없음** (`.env.example` 만 존재). `ANTHROPIC_API_KEY` 주입이 §B 실검증의 전제조건.

**집 환경에서 재개 순서:**
1. `backend/.env` 생성 → `backend/.env.example` 복사 후 `ANTHROPIC_API_KEY=sk-ant-...` 입력
   - 절대 커밋 금지 (`.gitignore` 확인)
2. `claude-ai-integrator` 에이전트에 §B 위임:
   ```
   python -c "import asyncio; from app.scheduler import analyze_and_score_matchups; asyncio.run(analyze_and_score_matchups())"
   ```
   - Vision 첫 호출 → `face_scores` row 기록 로그 확인
   - Text 첫 호출 → `fortune_scores` row 기록 로그 확인
   - 재실행 → 캐시 히트, Claude 호출 0회 확인
3. 병렬로 `fastapi-backend-dev` 에 아래 코드 작업 위임 (키 없어도 진행 가능):
   - Vision 성공 + Text 실패 시 **고아 `face_scores` row 방지** (savepoint/rollback)
   - `analyze_and_score_matchups` except 분기 **Claude mock + rollback 유닛 테스트**
4. 완료 시 `code-reviewer` 게이트 (CLAUDE.md §7)

**세션 3 에서 미커밋 상태로 남긴 변경:**
- `CLAUDE.md`, `PROGRESS.md` 수정
- `backend/app/schemas/crawler.py`, `backend/app/services/crawler.py` 재작성
- 신규: `ARCHIVE.md`, `KBO_CRAWLING_GUIDE.md`, `scripts/test_crawl.py`
- (본 WPI 커밋에 모두 포함됨)

**기억해둘 가드레일 (CLAUDE.md 에서):**
- 크롤러는 koreabaseball.com 단일 소스 — Naver/Statiz 폴백 금지
- `/ws/` robots carve-out 는 koreabaseball.com/ws/* 에만 적용
- 관상 점수는 시즌 고정, 운세는 `(pitcher_id, date)` 결정적 캐시
- 상성 clamp `[0, 4]`, 운명력 axis 에만 적용

---

## 진행 중 TODO

### A. 크롤러 마무리 (nice-to-have)

- [ ] **A-5.** `pitchers` 에 `kbo_player_id` 컬럼 추가 + `match_pitcher_by_kbo_id()` 헬퍼  
  → `pitcher.py` 컬럼 추가 → `init_db.py` idempotent ALTER → `scheduler` 매칭 로직을 ID 우선/name 폴백으로 교체  
  → 동명이인 안전망 (두 명의 "박정훈" 등), 트레이드 직후 매칭 실패 복구
- [ ] **A-6.** `seed_pitchers.py` 에 KBO 프로필 수확기 추가  
  → `/Record/Player/PitcherDetail/Basic.aspx?playerId=...` 파싱 → 이름/생년월일/사진/kbo_player_id 자동 시드  
  → 콜업·트레이드·외국인 영입 신인 자동 대응

### B. Phase 2 AI 실검증 (blocker — 배포 전 필수)

- [ ] `.env` 에 `ANTHROPIC_API_KEY` → `python -c "import asyncio; from app.scheduler import analyze_and_score_matchups; asyncio.run(analyze_and_score_matchups())"` 수동 실행
  - [ ] Claude Vision 첫 호출 → `face_scores` row 기록 로그 확인
  - [ ] Claude Text 첫 호출 → `fortune_scores` row 기록 로그 확인
  - [ ] 동일 `(pitcher_id, date)` 재실행 → DB 캐시 히트, Claude 호출 0회 확인
- [ ] 고아 score row 문제 — Vision 성공 + Text 실패 시 savepoint 도입 또는 문서화 (`claude-ai-integrator` 위임)
- [ ] `analyze_and_score_matchups` except 분기 — Claude mock + rollback 유닛 테스트

### C. 운영 잔여 (non-blocker)

- [ ] `_append_review` dedup — 동일 `(date, team, side, name)` 중복 큐 방지
- [ ] `_append_review` concurrency — fcntl lock 또는 `review_queue` DB 테이블 승격
- [ ] `publish_matchups` — `is_published.is_(False)` 필터 추가
- [ ] `analyze_and_score_matchups` — pitcher `IN [...]` 배치 로드 (현재 게임당 SELECT 2회)
- [ ] Alembic 도입 여부 결정 (prod Postgres 전환 전. dev SQLite 는 수동 ALTER 허용)

---

## 다음 세션 시작 명령

```
세션 3 완료. GetKboGameList 단일 소스 작동, 실 데이터 검증됨.
§A-2/A-3/A-4/A-7 완료, §A-5/A-6 nice-to-have 강등.

- 옵션 1 (권장): §B — .env 에 ANTHROPIC_API_KEY 꽂고
  python -c "import asyncio; from app.scheduler import analyze_and_score_matchups; asyncio.run(analyze_and_score_matchups())"
  → Vision/Text 첫 호출 로그 + 두 번째 호출 캐시 히트 확인

- 옵션 2: §A-5/A-6 마무리 → 그 다음 §B

세션 전 확인: CLAUDE.md §5 /ws/ carve-out 조항, memory feedback_crawler_source.md
```

---

## Phase 4~6 로드맵

- **Phase 4:** `app/routers/{today,matchup,pitcher,admin}.py`, Pydantic response schemas, pytest
- **Phase 5:** `frontend/` — Next.js 14 App Router, shadcn/ui, Pretendard Variable, Recharts 레이더
- **Phase 6:** docker-compose, 면책 고지, Vercel + Railway 배포, GitHub Actions 게이트, 공유 카드 PNG
