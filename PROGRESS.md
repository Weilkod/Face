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

- [x] `_append_review` dedup — 동일 `(team, crawled_name, game_date[, kbo_player_id])` 중복 큐 방지 ✅ (Wave 2 Track F)
- [x] `_append_review` TTL — resolved 24 h 이상 된 엔트리 lazy eviction ✅ (Wave 2 Track F)
- [ ] `_append_review` concurrency — fcntl lock 또는 `review_queue` DB 테이블 승격 (미구현)
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

---

### Wave 2 Track F 실행 결과 (2026-04-16)

#### 저장소 결정: JSON 파일 유지

DB 테이블 신설 없이 기존 `data/crawler_review_queue.json` 파일 유지.
근거:
- 읽기/쓰기 빈도 극저 (크롤러 실패 시만 append, 관리자 조회 시만 read)
- Alembic 마이그레이션 불필요 → 운영 복잡도 최소화
- Track C 인프라 복구(Postgres 전환) 전까지도 독립 동작 가능
- 동시성 위험 있으나 08:00 crawl_job 이 단일 프로세스 내 순차 실행 — 현재 트래픽 수준에서 허용 가능

#### Dedup 키 정의

```
(team, crawled_name, game_date, kbo_player_id)
```

- `crawled_name` 이 None 이 아닐 때: `kbo_player_id` 는 항상 None (key에서 제외)
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

#### 엔드포인트 사양

| 메서드 | 경로 | 쿼리/바디 | 응답 |
|--------|------|-----------|------|
| GET | `/admin/review-queue` | `?unresolved_only=bool&limit=int` | `list[ReviewQueueItem]` |
| POST | `/admin/review-queue/resolve` | `ReviewQueueResolveRequest` (JSON body) | `ReviewQueueItem` (200) or 404 |

인증: 없음 — 기존 admin 라우터 컨벤션 동일 (네트워크/프록시 레이어 위임).

#### 테스트 결과

```
23 passed in 2.57s
```

커버 항목:
- happy path 3건 append → JSON 파일 3개 엔트리
- dedup: 동일 키 2번 → 1건 유지, created_at 갱신 확인
- dedup: 다른 game_date → 별도 엔트리 생성 확인
- dedup: crawled_name=None + 다른 kbo_player_id → 별도 엔트리
- TTL: 25시간 전 resolved → 제거 확인
- TTL: 1시간 전 resolved → 유지 확인
- TTL: unresolved는 400시간 경과해도 유지
- `_review_entry_key` 키 구성 검증 (3개 케이스)
- `_ttl_evict` 단독 유닛 테스트 (3개 케이스)
- GET /admin/review-queue: empty file, unresolved_only=True, False, limit 캡
- POST /admin/review-queue/resolve: 성공, 404, kbo_player_id 키
- ASGI httpx 통합 테스트 1건 (monkeypatch REVIEW_QUEUE_PATH)

#### 미구현 (의도적 미포함)

- `_append_review` 동시성 안전 (fcntl lock / DB 승격) — Track C 인프라 블록 이후 별도 Wave 과제
- Alembic 마이그레이션 — JSON 유지 결정으로 불필요
- `GET /admin/review-queue` 의 path injection 을 Query param 이 아닌 DI 로 교체 — 현재 함수 직접 호출 테스트로 충분

#### 변경 파일

- `.gitignore` — `data/crawler_review_queue.json` 추가
- `backend/app/schemas/response.py` — `ReviewQueueItem`, `ReviewQueueResolveRequest` 신설
- `backend/app/routers/__init__.py` — 신설
- `backend/app/routers/admin.py` — `GET /admin/review-queue`, `POST /admin/review-queue/resolve` 신설
- `backend/app/main.py` — admin router include 추가
- `backend/tests/__init__.py` — 신설
- `backend/tests/test_review_queue.py` — 23개 테스트 신설
- `backend/pytest.ini` — asyncio_mode=auto 설정
- `PROGRESS.md` — §C dedup/TTL 항목 완료 체크, 본 섹션 추가
