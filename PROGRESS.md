# FACEMETRICS — Implementation Progress

> **자동 아카이브 지침:**
> 완료된 Phase 섹션이 **다음 Phase 착수 후** 또는 **2주 이상 경과** 했을 때,
> 세부 구현 내역은 `ARCHIVE.md` 로 이동하고 이 파일에는 핵심 결과만 체크리스트로 남긴다.
> 세션 요약 로그, 파일 맵 스냅샷, 코드 리뷰 라운드트립 내역도 아카이브 대상.

- **Spec:** `README.md` + `CLAUDE.md`
- **DB URL (dev):** `sqlite+aiosqlite:///data/facemetrics.db`
- **Stop hook:** `.claude/hooks/code-reviewer-gate.sh` — 코드 변경 시 자동 code-reviewer 호출
- **main:** `c3f380d` (2026-04-16 기준, Wave 3 완료 + Wave 4 Track I-1/I-2/I-3/I-4 전부 PASS — 프로덕션 런치 완료). Track I-5 (2026-04-19) 는 브랜치 `claude/review-progress-plan-E6hN5` tip `ae8cc60` 에 보류 — 로컬 실행 대기.
- **Prod URLs:** BE `https://face-production-0f00.up.railway.app` (Railway + Supabase Postgres session pooler), FE `https://frontend-weilkods-projects.vercel.app` (Vercel).
- **⚠️ 새 세션 시작 시:** 첫 턴에 반드시 `git fetch origin main && git log --oneline HEAD..origin/main` 실행. 다른 병렬 세션이 머지한 커밋이 있으면 `git pull --ff-only` 로 최신화 후 착수 — 과거에 중복 작업으로 PR 이 obsolete 된 선례 있음 (ARCHIVE.md §세션 11 참조).

---

## 🔥 다음 세션 우선 순위 — 프로덕션 DB 시딩 (사용자 deferred, 나중에 로컬 실행)

프로덕션 배포는 완료됐지만 Supabase Postgres 가 비어있어 FE 가 empty-state 만 렌더함. **Track I-5 (2026-04-19)** 로 수동 5-step 을 한 번에 돌리는 래퍼 `scripts/seed_production.py` 를 올려뒀으니 로컬 한국 IP 머신에서 한 번만 실행하면 됨.

> **상태 (2026-04-19):** 래퍼 + 런북 + 코드리뷰 2라운드 완료, 브랜치 `claude/review-progress-plan-E6hN5` tip `c6afccf` 에 푸시됨. 사용자가 2026-04-19 세션에서 "지금 바쁘고 머리 아프다 → 나중에" 로 **의식적으로 실행 연기**. 블로커 없음, 대기 시간 제약 없음. 다음 세션/시간 여유 생길 때 아래 명령 1회 실행하면 끝.

**실행 (로컬):**
```bash
git checkout claude/review-progress-plan-E6hN5 && git pull
pip install -r backend/requirements.txt   # 최초 1회

export DATABASE_URL='postgresql+asyncpg://postgres.czhnskoroaxuvczyngrr:<PASS>@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres'
export ANTHROPIC_API_KEY='sk-ant-...'
python scripts/seed_production.py                    # 오늘 KST
python scripts/seed_production.py --date 2026-04-18  # 날짜 명시
```

래퍼가 내부적으로 [1] pre-flight (Supabase 연결 + 6 테이블 카운트) → [2] `seed_pitchers --harvest` (A-6 로직, 10/10 hit 기대) → [3] `fetch_today_schedule` + `upsert_schedule` (pitcher_id 해소는 step 4 에서 함) → [4] `analyze_and_score_matchups` (Claude Vision + Text 실호출 ~$1) → [5] `publish_matchups` → [6] before/after delta 요약 까지 한 번에 수행. 기반 엔트리포인트 (seed_pitchers, upsert_schedule, analyze_and_score_matchups, publish_matchups) 는 모두 멱등이라 부분 실패 후 재실행 안전 — wrapper end-to-end 자체는 아직 성공 실행 이력 없음, 로컬 1회 성공 후에 "검증됨" 으로 확정. 옵션: `--skip-harvest` (pitchers 이미 시딩), `--skip-crawl` (일정 이미 적재).

성공 시 `matchups.is_published=true` 로우가 N 개 생기고, FE SSR `revalidate: 300` 경계로 최대 5분 안에 카드 렌더. 즉시 무효화는 Vercel Redeploy.

**주의:**
- Railway BE 미국 리전이라 KBO 크롤 WAF 차단 → 래퍼 실행은 **반드시 로컬 한국 IP 머신**.
- 스케줄러 `SCHEDULER_ENABLED=false` 고정. 시딩 후 09:00/10:00/11:00 KST 재시도는 다시 수동 실행 또는 cron 으로 래퍼 호출.
- `/admin/*` 무인증 노출 중 (후속 과제 2번째). 시딩 끝나면 인증 gate 우선 추가.
- **Claude Code sandbox 에서는 실행 불가** — egress allowlist (`api.anthropic.com:443`, `www.koreabaseball.com:443`) 때문에 Supabase:5432 로 나가는 TCP 가 timeout 됨. 2026-04-19 실측 확인. 이후 세션에서도 동일 제약, 사용자 로컬 실행 전제.

시드 완료 후 다음 단계: FE 실매치업 렌더 확인 → Wave 4 Track I-5 DONE 로 이관 → `/admin/*` 인증 gate (후속 과제 2) 착수.

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

- [x] **Track I-1 Docker Compose 로컬 smoke** (2026-04-16). `docker compose build` 성공 (FE build 43s, BE alembic upgrade head 자동), `docker compose up -d` 후 7개 엔드포인트 검증: BE `/api/today` (2 matchup, predicted_winner name resolve — `곽빈`/`양현종`, enum leak 0), BE `/api/matchup/1`, BE `/api/history?date=2026-04-14`, FE `/`, `/history`, `/pitcher/1` 모두 200 + 엔터테인먼트 disclaimer 유지, OG `/api/og/matchup/1` 200 `image/png` edge runtime. SSR→INTERNAL_API_URL + browser→NEXT_PUBLIC_API_URL split 정상 동작 확인.

- [x] **Track I-2 Railway BE 배포** (2026-04-16). 기존 `perpetual-passion/Face` 서비스 재사용 (c3f380d 배포됨). DB 는 Supabase 무료 플랜 Postgres 로 연결 — Direct connection (`db.XXX.supabase.co`) 은 free-tier IPv6-only 라 Railway 에서 `[Errno 101] Network is unreachable` 실패, **Session pooler** (`aws-1-ap-southeast-1.pooler.supabase.com:5432`) 로 전환해 성공. 배포 시 `scripts/init_db.py` 가 alembic 0001→0002 자동 적용. 환경변수: `DATABASE_URL=postgresql+asyncpg://postgres.<ref>:PASS@<pooler>/postgres`, `ANTHROPIC_API_KEY` (기존), `APP_ENV=prod`, `SCHEDULER_ENABLED=false`, `FRONTEND_ORIGIN=https://frontend-weilkods-projects.vercel.app`. 공개 URL: `https://face-production-0f00.up.railway.app`. `/api/today`/`/health`/`/docs` 전부 200.

- [x] **Track I-3 Vercel FE 배포** (2026-04-16). `weilkods-projects/frontend` 프로젝트 신규 생성. 환경변수 `NEXT_PUBLIC_API_URL=https://face-production-0f00.up.railway.app`, `NEXT_PUBLIC_USE_MOCK=false` production 타깃에 추가 후 `vercel deploy --prod`. **Vercel Authentication (Standard Protection) 기본 ON → 401 반환, 대시보드 Deployment Protection 에서 Disabled 로 수동 토글 필요**. Production URL: `https://frontend-weilkods-projects.vercel.app`. `/`, `/history`, `/api/og/matchup/1` (edge runtime, `image/png`) 전부 200. SSR 이 `NEXT_PUBLIC_API_URL` 로 Railway BE 직접 페치 (INTERNAL_API_URL 미설정 → public fallthrough 경로), empty-state 렌더 확인 ("경기가 없는 날이거나 선발투수 발표 전일 수 있습니다"), enum-leak 0.

### Phase 7 Wave 5 — Oracle Cloud Seoul 크롤 워커 (플랜, 미착수)

**배경.** Railway BE 는 US 리전이라 KBO `/ws/*` 가 WAF 로 블록됨 (Wave 1 Track C FAIL). 매일 새 선발투수 자동 크롤 + 운세 재생성 파이프라인을 자동화하려면 **한국 IP 엔드포인트가 구조적으로 필요**. 다만 서비스 전체가 한국 IP 를 필요로 하는 건 아니고 `/ws/*` 호출 + `seed_pitchers.py --harvest` 두 경로만 해당. 따라서 BE 전체를 옮기는 대신 **스케줄러 전용 워커** 만 Oracle Seoul 에 띄우고, 기존 Railway 는 API 서빙 그대로 유지하는 **split 토폴로지** 로 간다.

**채택 토폴로지 (Pattern 2 — split, Railway 유지).**
- **Railway BE (변경 없음).** API 서빙 전담. `SCHEDULER_ENABLED=false` 유지. FE 가 이 주소를 계속 봄.
- **Oracle Seoul VM (신규).** 동일 레포 + 동일 Docker 이미지. `SCHEDULER_ENABLED=true` + `SCHEDULER_TIMEZONE=Asia/Seoul`. **HTTP 포트 외부 노출 X** — VM 은 scheduler 잡이 fire 될 때만 KBO `/ws/*` 와 Supabase 에 outbound 하는 "쓰기 전용 워커".
- **Supabase DB (변경 없음).** 두 워커가 같은 DB 공유. Oracle 이 크롤 데이터 write → Railway 가 그걸 read 해서 FE 서빙.
- **Vercel FE (변경 없음).** `NEXT_PUBLIC_API_URL` 그대로.
- **Claude API 호출.** Oracle 스케줄러 잡 안에서 face_analyzer / fortune_generator 가 Anthropic 으로 outbound. 레이턴시 무영향(배치).

**왜 Pattern 3 (풀 이전) 이 아닌지.**
- 한국 IP 가 필요한 코드 경로는 `/ws/*` 크롤 하나 뿐. API 서빙/Claude/DB/이미지 CDN 전부 US IP 에서도 정상 동작 (이미 Railway 에서 검증됨, 프로필 사진 FE 렌더링이 증거).
- Railway 는 이미 관리형 TLS / 자동 재배포 / 롤백 / zero-downtime 제공. Oracle Free Tier 는 이 전부를 손수 구성해야 함 (Caddy/fail2ban/모니터링/ARM 품절 대응).
- Pattern 3 은 DNS 컷오버 + Vercel env 교체 + Railway decommission 까지 창구를 흔드는 대공사. Pattern 2 는 "Docker 한 개 상시 구동" 으로 범위 축소.
- Oracle VM 이 다운되어도 FE/API 는 멀쩡. 단지 그날 새 크롤만 건너뜀 (기존 DB 캐시는 계속 서빙). **장애 격리 관점에서도 Pattern 2 가 안전**.
- Pattern 3 을 Wave 6+ 통합 옵션으로 보류.

**선결 조건.**
1. Oracle Cloud 계정 + Seoul 홈리전. Always Free ARM Ampere A1 4 OCPU / 24GB 는 capacity 부족 빈번 (`Out of host capacity` 리트라이 필요). 실패 시 x86 Always Free (1/8 OCPU / 1GB) 도 크롤 워커 용도로 충분.
2. Supabase session pooler URL + `ANTHROPIC_API_KEY` — Railway Variables 에서 복사.
3. `docker-compose.yml` 에 scheduler 전용 프로필 or 호스트에서 `docker compose up -d backend` 로 backend 만 띄우는 경로.

**Track J 실행 순서.**

- [ ] **J-1 VM 프로비저닝** — Oracle Cloud Console → Compute → Instance 생성. Shape `VM.Standard.A1.Flex` / OCPU 4 / RAM 24GB / Ubuntu 22.04 ARM. Boot Volume 50GB 면 충분 (Always Free 한도 200GB). SSH 키 페어 생성. **ARM capacity 부족 시 `oci-capacity-retry.sh` 루프 or x86 으로 다운그레이드.**
- [ ] **J-2 네트워킹 (SSH 만)** — VCN Security List ingress: tcp 22 (관리 IP 로 좁힐 것). **80/443 열지 않음** — 외부에서 워커에 접근할 일 없음. Ubuntu iptables 도 동일: `sudo iptables -I INPUT -p tcp --dport 22 -s <관리 IP>/32 -j ACCEPT` + `netfilter-persistent save`. Outbound 는 기본 허용이라 KBO/Anthropic/Supabase 호출에는 추가 설정 불필요.
- [ ] **J-3 시스템 부트스트랩** — `apt update && apt install -y docker.io docker-compose-v2 git ufw fail2ban`, `usermod -aG docker ubuntu`, `ufw default deny incoming && ufw default allow outgoing && ufw allow 22/tcp && ufw enable`, `fail2ban-client status sshd` 확인. `timedatectl set-timezone Asia/Seoul`.
- [ ] **J-4 레포 clone + .env** — `git clone https://github.com/Weilkod/Face.git /opt/facemetrics`. `/opt/facemetrics/backend/.env` 에:
  ```
  APP_ENV=prod
  ANTHROPIC_API_KEY=<Railway 와 동일>
  DATABASE_URL=postgresql+asyncpg://postgres.czhnskoroaxuvczyngrr:<pw>@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
  SCHEDULER_ENABLED=true            # ← Railway 는 false, Oracle 만 true
  SCHEDULER_TIMEZONE=Asia/Seoul
  FRONTEND_ORIGIN=https://frontend-weilkods-projects.vercel.app
  ```
  **`.env` 권한 600, root 소유**. **`SCHEDULER_ENABLED` 이중 실행 방지 룰 — Railway 와 Oracle 중 정확히 한 곳만 true** (CLAUDE.md 에 규칙 한 줄 추가 예정).
- [ ] **J-5 워커 기동 (포트 외부 미노출)** — `docker compose up -d backend` 만 실행 (frontend 는 무시). Docker 기본 포트 매핑을 제거하려면 `docker-compose.yml` 의 `ports: - "8000:8000"` 를 **오라클 VM 에서만 주석 처리**하거나 `docker compose` 대신 `docker run --network host` 안 쓰고 그냥 container 내부 8000 만 열어두면 됨 (호스트 포트 미매핑). `docker logs -f facemetrics-backend` 로 `scheduler started` 로그 + alembic head 확인.
- [ ] **J-6 수동 크롤 스모크 (관리자 엔드포인트를 VM 내부에서 호출)** — 워커 포트를 외부에 안 열었으니 `docker exec -it facemetrics-backend curl -X POST http://localhost:8000/admin/crawl-schedule?date=<today>` 로 컨테이너 안에서 호출. 200 + Supabase `daily_schedules` 에 오늘 row 들어오는지 확인. **Wave 1 Track C 언블록 판정 여기서 결정**.
- [ ] **J-7 스케줄러 자동 fire 검증** — 익일 08:00 / 10:30 / 11:00 KST 에 `docker logs facemetrics-backend | grep -E 'crawl_schedule|analyze_pitchers|publish_matchups'` 로 세 잡 모두 fire 됐는지 확인. 실패 시 `crawler_review_queue.json` + 에러 로그 분석. Railway 쪽에서 `SCHEDULER_ENABLED=false` 재확인 (이중 fire 방지).
- [ ] **J-8 초기 시드** — J-6 크롤 성공 뒤, `docker exec facemetrics-backend python scripts/seed_pitchers.py --harvest` 실행해 KBO 프로필 10 팀 긁기. 이어서 컨테이너 내부에서 `/admin/generate-fortune?date=<today>` → `/admin/calculate-matchups?date=<today>` 호출. **기존 Supabase 의 "(폴백) 해시 기반 근사치" face_scores / fortune_scores 는 선행 `DELETE` 로 정리**. Vercel FE 새로고침해 진짜 Claude 분석 문구가 매치업 상세에 뜨는지 확인.

**관측 (간이).**
- 워커는 외부 엔드포인트가 없으므로 UptimeRobot 같은 pull-ping 불가. **Push-based heartbeat**: 각 스케줄러 잡 성공 시 `healthchecks.io` 나 `cronitor.io` 의 unique URL 로 GET 요청 보내는 hook 을 `app/scheduler.py` 에 1줄 추가. 48h fire 없으면 이메일. (Wave 5 에서는 옵션 항목, 실운영 전 필수.)
- Supabase 대시보드에서 매일 `daily_schedules` / `face_scores` / `fortune_scores` row 증가 수동 스팟체크.

**리스크 / 주의.**
- **Env var 이중 관리.** Railway + Oracle 두 곳에 동일한 `ANTHROPIC_API_KEY`, `DATABASE_URL` 복사. 한쪽에서 갱신 시 다른 쪽도 반드시 동기화. `SCHEDULER_ENABLED` 만 서로 달라야 함 (Oracle=true, Railway=false).
- **스케줄러 중복 실행.** 실수로 양쪽 다 true 되면 APScheduler 가 같은 잡을 병렬로 돌려 중복 크롤 + race condition. 현재 코드의 싱글톤 가드 (세션 11, PR #12) 는 프로세스 내부 가드일 뿐 교차 호스트 레벨은 아님. **CLAUDE.md 운영 규칙에 "Oracle 만 true" 명문화 필요**.
- **Oracle Always Free 90일 dormancy.** 계정 로그인 장기간 없으면 리소스 회수. 매월 1회 콘솔 로그인 + VM 재시작 모니터링.
- **Supabase Seoul ↔ Singapore RTT 70-90ms.** 배치 잡이라 영향 미미하나 대량 INSERT 쿼리 시 체감. 필요 시 유료 플랜 Seoul 이관.
- **Playwright fallback 시 ARM64 chromium 필요.** 현재 경로에는 Playwright 미탑재. 도입 시 `ARM64` 바이너리 확인 필요.

**롤백 트리거.**
- J-1 ARM capacity 1주 이상 확보 실패 → x86 Always Free 인스턴스로 다운그레이드 (크롤 워커 용도엔 충분). 그래도 안 되면 Naver Cloud Micro / Vultr Seoul 유료(~월 1만원) 로 교체.
- J-6 에서 `/ws/*` 가 Oracle Seoul IP 에서도 블록 (클라우드 대역 기반 차단) → Playwright headless fallback 착수 (Wave 1 Track C 후속옵션 2). 이 경우엔 Oracle VM 을 띄워둔 의미가 줄어드니 재검토.
- J-7 스케줄러 fire 실패 연속 3일 → 원인 (timezone / Supabase 연결 / APScheduler 설정) 해결, 불가 시 Railway 쪽을 `SCHEDULER_ENABLED=true` 로 되돌려 수동 파이프라인으로 회귀.

**완료 기준.**
1. Oracle VM 에서 `docker exec ... POST /admin/crawl-schedule` 성공 → Supabase `daily_schedules` 에 신규 row
2. 08:00 KST 자동 크롤 잡 1회 이상 fire 확인
3. `seed_pitchers.py --harvest` 로 pitchers 10명 이상 프로필 수확
4. 매치업 상세에서 "(폴백) 해시 기반 근사치" → 실 Claude 분석 문구로 교체됨 (FE 확인)
5. Railway BE 변경 없이 API 서빙 유지 (`/api/today` 200)

**향후 (Wave 6+) 고려.** Pattern 3 (BE 풀 이전) 을 다시 검토할 시점은 (a) Railway 비용 급증 또는 (b) Oracle 운영이 충분히 안정화되어 전체 이전의 관리 부담이 오히려 낮아질 때. 현재는 Pattern 2 유지.

### 후속 과제 (non-blocker)

- [ ] **프로덕션 DB 시딩 — 로컬 실행 대기**: Track I-5 래퍼 (`scripts/seed_production.py`, `ae8cc60`) 로 경로는 확보됨. 사용자 로컬 한국 IP 머신에서 `python scripts/seed_production.py` 한 번 돌리면 pitchers + daily_schedules + face_scores + fortune_scores + matchups 전부 채워지고 `is_published=true` 까지 플립. 실행 + FE 카드 렌더 검증이 끝나면 Track I-5 를 DONE 으로 이관하고 이 bullet 클로즈. sandbox 실행 불가 (egress allowlist, §🔥 참조).
- [ ] **프로덕션 `/admin/*` 인증 gate**: 현재 dev-only로 열려 있고 prod 에도 그대로 노출됨. `Depends(require_admin_token)` + `APP_ENV==prod` 조건부 적용 필요. Wave 3 Track H 에서 Important 로 플래그된 사항이 prod 에서도 미해결. 특히 `/admin/review-queue/resolve` 가 무인증 상태라 조기 차단 권장.
- [ ] **Supabase DB 패스워드 로테이션 (옵션)**: 초기 세팅 시 패스워드가 세션 로그에 평문 노출됨. 보안 우선시 Supabase 대시보드에서 리셋 후 Railway `DATABASE_URL` 업데이트 권장.
- [ ] **Vercel 프로젝트명 rename (옵션)**: 현재 "frontend" 로 생성됨. Vercel 대시보드에서 `facemetrics` 로 rename 가능 (도메인도 `facemetrics-weilkods-projects.vercel.app` 로 변경되니 Railway `FRONTEND_ORIGIN` 동시 업데이트 필요).
- [ ] **I-G1 `create_sample_matchup.py` chemistry placement**: 프로덕션 `scoring_engine._build_axis_totals` 는 chem 을 destiny axis total 에 베이크하지만 샘플 스크립트는 `home_total` 에만 더함 (각 axis.total 엔 0 만큼만 영향). grand total 합은 일치하지만 destiny.total 이 chem_final 만큼 낮게 나와 radar chart / score bar 가 프로덕션과 미묘히 다름. Wave 3 Track G 실검증 중 발견. P-1 계열 sample-vs-prod 불일치.
- [ ] **MatchupCard `zodiac_sign`/`chinese_zodiac` null guard**: `frontend/src/components/MatchupCard.tsx:170-175,196-204` 가 두 필드를 무가드 렌더 (`♟ {zodiac_sign}`, `{chinese_zodiac}띠`). 타입은 `string` 이지만 신규 크롤된 투수에 fortune 메타데이터가 미채워졌을 경우 `♟ undefined` / `undefined띠` 노출 위험. 조건부 렌더 가드 추가. PR `claude/fix-mobile-text-truncation-kFVb7` (5770381) code-reviewer 가 Important 로 플래그.
- [ ] **MatchupCard 360px 실측 smoke**: 동 PR 에서 5자 이름 (`text-base` 14px) × 138px 컬럼 폭 width 계산상 통과하지만 실 디바이스/Playwright 측정 미수행. 360px 뷰포트에서 `에르난데스` 등 5자 이름이 한 줄에 들어가는지 + VS 가 사진 중심에 정렬되는지 스크린샷 확인 필요. CLAUDE.md §7 mobile-viewport 검증 항목.
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
