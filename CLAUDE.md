# CLAUDE.md — FACEMETRICS (KBO Fortune × Physiognomy) Project Guide

Entertainment-only service that predicts KBO starting-pitcher matchups by mapping **physiognomy (관상)** and **fortune (사주/별자리/띠)** onto 5 baseball performance axes. Product name is **FACEMETRICS** (subtitle: "관상과 운세로 보는 오늘의 승리투수"). See `README.md` for the full spec — treat it as the source of truth.

**Design tone:** light SaaS (오프화이트 배경 + 흰 카드 + coral `#F26B4E` / mint `#059669` 액센트 + ink 3단 텍스트), Pretendard Variable 단일 폰트. 이전 obsidian/gold/crimson/jade 다크 오리엔탈 톤과 ShineBorder/Aurora 모션은 전면 폐기됨. 현재 톤앤매너 기준은 `frontend/preview/draft.html`.

## 1. Project shape

- **Frontend:** React 18 + TypeScript + Tailwind, Recharts for radar/bar charts. Pages: `TodayMatchups`, `MatchupDetail`, `PitcherPage`, `HistoryPage`.
- **Backend:** FastAPI (Python 3.11+) + SQLAlchemy 2.0 async, APScheduler, BeautifulSoup + httpx.
- **AI:** Anthropic Claude API — Vision for 관상 analysis, Text for daily 운세. JSON-only outputs.
- **DB:** SQLite (dev) → PostgreSQL (prod). Tables: `pitchers`, `face_scores`, `fortune_scores`, `matchups`, `daily_schedules`.
- **Deploy:** Vercel (FE) + Railway/Fly (BE). Only `frontend/` exists today — backend still needs to be scaffolded.

## 2. Scoring invariants — get these wrong and the product breaks

- Each of the 5 axes (제구력 / 구위 / 멘탈 / 지배력 / 운명력) is **20 pts = 관상 10 + 운세 10**. Total 100.
- **관상 scores are SEASON-FIXED.** Compute once per `(pitcher_id, season)`, cache in `face_scores`, never regenerate unless the profile photo changes.
- **운세 scores vary DAILY but are DETERMINISTIC per `(pitcher_id, game_date)`.** First call hits Claude, immediately write-through to `fortune_scores`, every subsequent call returns the cached row. Never re-call Claude for a key that already exists.
- **상성 (chemistry) is RULE-BASED, no AI.** Only the 운명력 axis applies it. Base 2 pts + 띠 궁합 (삼합 +2, 육합 +1.5, 원진 −1.5, 충 −2) + 별자리 원소 궁합. **Clamp to [0, 4].**
- On Claude API failure, fall back to a **hash of `(pitcher_id, date)`** to generate stable pseudo-scores — never raise a 500 to the user for a scheduled matchup.

## 3. Specialized agents — prefer these over doing it yourself

Defined in `.claude/agents/`. Match the task, delegate rather than re-derive:

| Task | Agent |
|---|---|
| React pages, components, Recharts, share-card image export | `react-ui-dev` |
| FastAPI routers, SQLAlchemy models, APScheduler wiring, Pydantic schemas | `fastapi-backend-dev` |
| Claude Vision/Text calls, prompt design, JSON parsing, caching layer, fallback | `claude-ai-integrator` |
| KBO 일정 / 선발투수 / 프로필 사진 crawling (KBO, 네이버, 스탯티즈) and name → `pitcher_id` matching | `kbo-data-crawler` |
| 사주·오행·12지신·별자리 원소 logic, 상성 rules, score calibration vs README §2–3 | `fortune-domain-expert` |

Run them in parallel when the work is independent (e.g. crawler + fortune generation).

## 4. Coding conventions

### Frontend
- Mobile-first. The Head-to-Head card and radar chart must render cleanly on a 360 px viewport — test there before declaring done.
- Recharts radar is always 5 axes in this fixed order: 제구력 → 구위 → 멘탈 → 지배력 → 운명력. Don't reorder.
- Score bars show `score / 20` filled. Highlight the winning side of each axis.
- Korean copy in UI, but keep variable names, files, and comments in English.
- Tailwind only — no styled-components, no CSS modules.

### Backend
- Async everywhere: `async def` routes, `AsyncSession`, `httpx.AsyncClient`. No sync DB calls inside request handlers.
- Pydantic v2 schemas in `app/schemas/`, SQLAlchemy models in `app/models/`. Don't return ORM objects from routes.
- APScheduler jobs live in `app/scheduler.py` and fire at **08:00 / 10:30 / 11:00 KST**. Never hardcode UTC.
- Config via `pydantic-settings` reading `.env`. `ANTHROPIC_API_KEY` never in code, never in git.

### Claude API calls
- Use model `claude-opus-4-6` for quality-critical runs (관상), `claude-sonnet-4-6` for volume (daily 운세). Enable **prompt caching** on the system prompt — it doesn't change between pitchers.
- Every prompt template lives in `backend/app/prompts/*.txt` and is loaded at startup, not inlined.
- Force JSON output, then validate with Pydantic. If parsing fails, retry once with `temperature=0`, then fall back to the hash scorer.
- Log `(pitcher_id, date, model, input_tokens, output_tokens, cache_read_tokens)` for every call.

## 5. Crawling rules

- Primary → fallback chain: **KBO 공식 → 네이버 스포츠 → 스탯티즈.** Never rely on a single source.
- 선발투수 미발표 → retry at 09:00 and 10:00 before giving up.
- Crawled 선수 이름 must map to `pitcher_id` via exact match first, then fuzzy (rapidfuzz ≥ 85). Unknown names go to a review queue, not silently dropped.
- Respect robots.txt, add a UA header, rate-limit to ≤ 1 req/sec per host.

## 6. Legal / ethical guardrails (non-negotiable)

- Every page must show "엔터테인먼트 목적" disclaimer. **Never** link to or mention betting, odds, or real-money predictions.
- Pitcher photos: only KBO-official or verified-license sources. If unlicensed, use a placeholder silhouette and skip 관상 analysis — do not scrape arbitrary social media.
- Fortune/physiognomy commentary stays light and playful. No negative personal judgments about real players beyond baseball-performance framing.

## 7. Before you claim "done"

- **Backend:** `pytest` green, `uvicorn app.main:app` boots, `/api/today` returns a valid matchup list for today's date.
- **Frontend:** `npm run build` clean, `npm run dev` — manually click through TodayMatchups → MatchupDetail → PitcherPage on a mobile viewport. Type check passes.
- **AI work:** show a real Claude response, the parsed Pydantic object, and the DB row. Don't claim cache hits work without a second call proving it.
- If you couldn't actually run it (no API key, no DB, no browser), say so explicitly instead of assuming it works.

## 8. Things NOT to do

- Don't regenerate 관상 scores on every request — they're season-fixed.
- Don't call Claude inside request handlers synchronously blocking the user; the daily pipeline should have pre-populated everything by 11:00.
- Don't invent KBO team codes — stick to `LG / SSG / KT / NC / DS / KIA / LOT / SAM / HH / KW`.
- `frontend/components/ui/shine-border.tsx` and `timeline.tsx` are **legacy stubs** from the old dark/oriental tone — they're no longer used by the current `draft.html` design and are slated for removal. Don't build new features around them; prefer deleting or replacing them when touching the `ui/` folder.
- Don't commit `.env`, API keys, scraped photos of unclear provenance, or `*.db` SQLite files.
- Don't add features, endpoints, or tables not in `README.md` §5–6 without asking first.
