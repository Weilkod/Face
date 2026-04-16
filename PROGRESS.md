# FACEMETRICS — Implementation Progress

> **자동 아카이브 지침:**
> 완료된 Phase 섹션이 **다음 Phase 착수 후** 또는 **2주 이상 경과** 했을 때,
> 세부 구현 내역은 `ARCHIVE.md` 로 이동하고 이 파일에는 핵심 결과만 체크리스트로 남긴다.
> 세션 요약 로그, 파일 맵 스냅샷, 코드 리뷰 라운드트립 내역도 아카이브 대상.

- **Spec:** `README.md` + `CLAUDE.md`
- **DB URL (dev):** `sqlite+aiosqlite:///data/facemetrics.db`
- **Stop hook:** `.claude/hooks/code-reviewer-gate.sh` — 코드 변경 시 자동 code-reviewer 호출
- **main:** `1b5cae5` (2026-04-16 기준, Phase 7 Wave 3 완료)
- **⚠️ 새 세션 시작 시:** 첫 턴에 반드시 `git fetch origin main && git log --oneline HEAD..origin/main` 실행. 다른 병렬 세션이 머지한 커밋이 있으면 `git pull --ff-only` 로 최신화 후 착수 — 과거에 중복 작업으로 PR 이 obsolete 된 선례 있음 (ARCHIVE.md §세션 11 참조).

---

## 완료 이력 (상세 → `ARCHIVE.md`)

- [x] **Phase 1** — 기반 구축 (2026-04-13). FastAPI 스캐폴딩, 5 테이블 DB, 투수 10명 시드.
- [x] **Phase 2** — AI 엔진 (2026-04-13, 실검증 2026-04-14 세션 8). 관상/운세/상성/scoring_engine + B-1/B-2/B-3 실 Claude 검증.
- [x] **Phase 3 sub-task 1** — 크롤러 read-only (2026-04-13). KBO `GetKboGameList` 단일 소스, `/ws/` robots carve-out.
- [x] **Phase 3 sub-task 2** — DB write + Scheduler (2026-04-13). `upsert_schedule`, 5개 KST 잡.
- [x] **Phase 4** — API 라우터 (2026-04-13, 세션 4). 5 GET + 5 POST admin 엔드포인트.
- [x] **Phase 5** — 프론트엔드 초기 구축 (2026-04-13, 세션 4). Next.js 14 App Router, 3 페이지, Recharts 5축 레이더, `@vercel/og` Edge 공유카드 (세션 5).
- [x] **Phase 6** — 배포 인프라 준비. Alembic (세션 5) + @vercel/og (세션 5) + 사후 리뷰 fix (세션 6) + Docker/CI 스켈레톤 (세션 9) + APScheduler 싱글톤 가드 `SCHEDULER_ENABLED` (세션 11, PR #12).

### A. 크롤러 마무리
- [x] **A-5** `pitchers.kbo_player_id` + 매처 + lazy write-back (세션 10, PR #10).
- [x] **A-6** `seed_pitchers.py --harvest` eager KBO 프로필 수확기 (세션 12, PR #13). 2026-04-15 실 smoke 10/10 hit, 멱등.
- [x] **A-7** `srId` 라이브 검증 (세션 11, PR #12). 세 변종 동일 응답 → CLAUDE.md §5 를 코드값(`0,1,3,4,5,7`)으로 정정.

### B. Phase 2 AI 실검증 (세션 8)
- [x] **B-1** `.env` `ANTHROPIC_API_KEY` → 캐시 미스/히트 + score_matchup 통합 검증
- [x] **B-2** caller-managed transaction — face/fortune 내부 commit 제거, 호출자 원자 경계
- [x] **B-3** `analyze_and_score_matchups` rollback 테스트 3건 (happy/fortune-fail/face-fail)

### C. 운영 잔여
- [x] **C-1** `_append_review` dedup + 24h TTL + admin `/admin/review-queue` GET/resolve (Wave 2 Track F v2, PR #24)
- [x] **C-2** `publish_matchups` — `.where(Matchup.is_published.is_(False))` 필터 (Wave 1 Track A, PR #16)
- [x] **C-3** `analyze_and_score_matchups` — pitcher 배치 로드 (`f4fba33`)

### D. Phase 5 프론트엔드 잔여
- [x] **D-1~D-6** C1/C2/C3/I1/I6/C4/I3/I4/I5 (PR #1 + 후속)
- [x] **D-4** I2 Tailwind 토큰화 `ink.title` (세션 10, PR #9)
- [x] **D-7** `PitcherProfile` → `PitcherDetail` 통합 (세션 7)
- [x] **D-8** 360px 모바일 뷰포트 smoke (세션 7)
- [x] **D-9** Share card PNG — `@vercel/og` Edge route (세션 5)

### E. Phase 7 ULTRAPLAN — FE↔BE 통합 & 런치 (2026-04-16 진행 중)

Wave 내 Track 병렬, Wave 간 의존. Critical Path: Track A → Track E → Track G → Track I.

- [x] **Wave 1 Track A** BE 스키마 G2/G3/G4 + C-2 (PR #16)
- [x] **Wave 1 Track B** FE api.ts G1 + types 정합 (PR #15)
- [x] **Wave 1 Track D** 상성 로직 감사 + 96 테스트 (PR #18). PASS — 코드 수정 0.
- [x] **Wave 2 Track E** FE 실 데이터 연동 (USE_MOCK=false, ErrorBanner, Empty state) — PR #21
- [x] **Wave 2 Track F** review queue dedup/TTL + admin endpoints + 22 테스트 (PR #24 v2)
- [x] **Wave 3 Track H** Wave 1–2 전체 code review + Critical 3 / Important 4 fix (`9a55715`, `02d5b10`). predicted_winner enum→name at response boundary, XOR validator on ReviewQueueResolveRequest, `threading.Lock` on review-queue I/O, re-resolve TTL guard, 5xx→isApiDown, ErrorBanner no-leak, sample script sqlite guard + KST. 141 → 151 tests.
- [x] **Wave 3 Track G** E2E pipeline smoke (2026-04-16). DB clean-rebuild → `seed_pitchers.py` → `create_sample_matchup.py` → uvicorn + `npm run dev`. `/api/today`, `/api/matchup/1`, `/api/history`, `/` home page, `/history`, `/pitcher/1`, OG route `/api/og/matchup/1` 모두 정상. **`predicted_winner` boundary resolve 실검증**: DB `"away"` → response `"곽빈"/"양현종"`. FE HTML 에 enum 유출 0건 (`⭐ <!-- -->곽빈<!-- --> 승` 렌더). 5축 순서 + disclaimer 유지. WAF 로 실 크롤 불가 → 샘플 스크립트 경로로 완료.

---

## 진행 중 TODO

### Phase 7 Wave 4 — Deploy (진행 중)

- [x] **Track I-4 면책 고지 copy review** (2026-04-16). 3 유저 페이지 (`/`, `/history`, `/pitcher/[id]`) 의 `<Footer />` + OG route 인라인 + `layout.tsx` 메타데이터 모두 disclaimer 유지. 베팅/배당 affirmative 언급 0건. PASS.

- [ ] **Track I-1 Docker Compose 로컬 smoke** (코드 패치 완료, daemon 이슈로 smoke 미실행)
  - **적용 패치 (커밋됨)**:
    1. `docker-compose.yml` — FE env 변수명 오타 수정 (`NEXT_PUBLIC_API_BASE` → `NEXT_PUBLIC_API_URL`), `INTERNAL_API_URL=http://backend:8000` 추가, build args 연결
    2. `frontend/Dockerfile` — `ARG NEXT_PUBLIC_API_URL` + `ENV` 바인딩 (NEXT_PUBLIC_* 은 build time inline 필요)
    3. `frontend/src/lib/api.ts` — SSR (`typeof window === 'undefined'`) 시 `INTERNAL_API_URL` 우선, browser 는 `NEXT_PUBLIC_API_URL`. Vercel+Railway prod 환경에서는 INTERNAL 미설정이라 fallthrough → NEXT_PUBLIC 사용 (호환).
  - **남은 액션**: Docker Desktop daemon 재시작 후 `docker compose build && docker compose up -d` → :8000/api/today + :3000 응답 확인. 새 세션에서 진행.
  - **uid 가이드 (I2 이월)**: `sudo chown -R 1000 ./data` 또는 `docker compose run --user $(id -u)`

- [ ] **Track I-2 Railway BE 배포** (CLI 설치 완료: railway 4.37.4)
  - `railway login` → `railway init` → `railway add postgres`
  - 환경변수: `DATABASE_URL=postgresql+asyncpg://...` (Railway Postgres URL), `ANTHROPIC_API_KEY` (로컬 `backend/.env` 에서 이관), `FRONTEND_ORIGIN=<vercel-url>`, **웹 서비스 `SCHEDULER_ENABLED=false`**
  - **워커 서비스 분리** (replicas=1 고정, `SCHEDULER_ENABLED=true`) — 수평 확장 금지
  - Railway 가 `backend/Dockerfile` 자체 빌드 (CMD 가 `init_db.py && uvicorn` 이라 `alembic upgrade head` 자동)

- [ ] **Track I-3 Vercel FE 배포** (CLI 설치 완료: vercel 51.4.0)
  - `vercel login` → `vercel link` → `vercel deploy`
  - 환경변수: `NEXT_PUBLIC_API_URL=<railway-be-url>`, `NEXT_PUBLIC_USE_MOCK=false`
  - Vercel 은 Next.js 직접 빌드 (Dockerfile 무관). OG route edge runtime 실 PNG 반환 검증.

### 후속 과제 (non-blocker)

- [ ] **Track I-2 prep: `/admin/*` 인증 gate**: 현재 dev-only로 열려 있음. Railway 배포 시 `Depends(require_admin_token)` + `APP_ENV==prod` 조건부 적용 필요. Wave 3 Track H 에서 Important 로 플래그됨.
- [ ] **I-G1 `create_sample_matchup.py` chemistry placement**: 프로덕션 `scoring_engine._build_axis_totals` 는 chem 을 destiny axis total 에 베이크하지만 샘플 스크립트는 `home_total` 에만 더함 (각 axis.total 엔 0 만큼만 영향). grand total 합은 일치하지만 destiny.total 이 chem_final 만큼 낮게 나와 radar chart / score bar 가 프로덕션과 미묘히 다름. Wave 3 Track G 실검증 중 발견. P-1 계열 sample-vs-prod 불일치.
- [ ] **I-G2 DATABASE_URL 상대경로 취약성**: `sqlite+aiosqlite:///./data/facemetrics.db` 가 cwd 의존. `cd backend && uvicorn` 으로 기동하면 `backend/data/` 에 빈 DB 자동 생성되고 API 가 empty matchups 반환. **반드시 프로젝트 루트에서 `PYTHONPATH=backend python -m uvicorn app.main:app` 형태로 기동**. Track I-1 Dockerfile 에서 WORKDIR 가 루트로 고정되는지 확인 + README 기동 가이드 업데이트 필요.
- [ ] **Wave 1 Track C 언블록**:
  - 옵션 1: 한국/미국 residential/VPS IP 에서 재실행
  - 옵션 2: Playwright headless fallback (`_fetch_kbo_playwright()` 별도 모듈)
  - 옵션 3: `backend/tests/fixtures/kbo_20260416.xml` 같은 파서 회귀 전용 오프라인 fixture
- [ ] **포스트시즌 srId 재검증**: A-7 은 2026-04-15 정규시즌 날짜에서만 검증됨. 시범/포스트시즌/더블헤더/우천취소 날짜에서 `srId` 필터가 유의미할 수 있음. 가을 도달 시 `scripts/verify_srid.py` 재실행 권장.
- [ ] **A-6 harvester ASP.NET 컨트롤 경로 모니터링**: 시즌 전환 / 페이지 리뉴얼 시 `__VIEWSTATE` / `btnSearch` 깨짐 가능. fail-soft 지만 신규 시드 사이클에서 hit rate 모니터링.
- [ ] **CI 게이트 강화**: PR 에서 `alembic downgrade base → upgrade head` 라운드트립 추가 검토.
- [ ] **H2 Stop hook 재도입 검토**: "세션 마지막 턴이 git commit/push 를 포함하면 code-reviewer 호출" — H1 의 embedded SHA 마커로 기능 대체되어 현재 deferred. 필요 시 재도입.

---

## 참고

- 과거 세션 상세 로그 (세션 1~12) → `ARCHIVE.md`
- Phase 1~6 세부 구현 내역 → `ARCHIVE.md`
- Phase 7 ULTRAPLAN 전체 + Wave 1/2 실행 결과 + false alarm 판정 → `ARCHIVE.md`
- Wave 1 Track C WAF FAIL 분석 + 언블록 옵션 → `ARCHIVE.md`
- I3 APScheduler 싱글톤 배포 런북 → `ARCHIVE.md` §세션 11
- 구조적 개선 H1/H2 → `ARCHIVE.md`
