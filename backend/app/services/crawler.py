"""
services/crawler.py — KBO 공식 단일 소스 크롤러.

**Single-call pipeline.** `/ws/Main.asmx/GetKboGameList` returns, in ONE POST,
every field this service needs per game:

    G_ID / G_DT / G_TM / S_NM   — identity + schedule
    AWAY_ID / HOME_ID            — KBO internal team codes
    T_PIT_P_ID / T_PIT_P_NM     — 원정 starter KBO ID + 한글 이름
    B_PIT_P_ID / B_PIT_P_NM     — 홈 starter KBO ID + 한글 이름
    CANCEL_SC_ID / CANCEL_SC_NM — cancellation flag
    START_PIT_CK                — 1 = confirmed / 0 = 미정

Discovered 2026-04-13 (session 3) by reading the XHR references inside
`/Schedule/GameCenter/Main.aspx`. This replaces the KBO_CRAWLING_GUIDE.md
§2–3 pipeline (GetTodayGames + GameCenter HTML scrape for `li.game-cont`) —
that guide was written before we knew the grail endpoint existed.

Public API
----------
  fetch_today_schedule(game_date)                    -> list[ScheduleEntry]
  match_pitcher_name(session, name, team, game_date) -> int | None  (legacy fallback)
  upsert_schedule(session, entries)                  -> {"inserted": n, "updated": n, "skipped": n}

Since starter 한글 이름 now comes back with every successful crawl, the
10:30 scoring job can resolve starters via the existing name-based
`match_pitcher_name` today. A-5 / A-6 (kbo_player_id column + ID matcher +
profile harvester) are still listed in PROGRESS.md §A as follow-ups because
they give us homonym-safe matching and automatic player seeding, but they
are no longer blocking — the pipeline is end-to-end functional on names.

Rules
-----
  - Async only (httpx.AsyncClient, AsyncSession).
  - Per-host rate limit: `asyncio.sleep(1)` before each KBO request.
  - robots.txt pre-check with a narrow `/ws/` carve-out on koreabaseball.com
    (see `_ROBOTS_CARVE_OUT_PREFIXES`); loose reading of CLAUDE.md §5
    sanctioned by user 2026-04-13.
  - Unknown crawled name → appended to data/crawler_review_queue.json, not dropped.
  - Never raises from `fetch_today_schedule` — returns [] on any terminal failure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
import urllib.robotparser
from datetime import date, datetime, time
from typing import Optional
from urllib.parse import urlparse

import httpx
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.config import PROJECT_ROOT
from app.models.daily_schedule import DailySchedule
from app.models.pitcher import Pitcher
from app.schemas.crawler import ScheduleEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KST = ZoneInfo("Asia/Seoul")
TIMEOUT_S = 10.0
RATE_LIMIT_S = 1.0  # seconds between requests to the same host
FUZZY_THRESHOLD = 85  # rapidfuzz WRatio minimum for a fuzzy name match

REVIEW_QUEUE_PATH = PROJECT_ROOT / "data" / "crawler_review_queue.json"

# KBO endpoint — single call returns game + starter (ID + 한글 이름) per game.
# Discovered 2026-04-13 session 3 by reading GameCenter Main.aspx JS refs. See
# PROGRESS.md §A carry-over (session 3) for the discovery path and why this
# replaces the guide's 2-step (GetTodayGames + GameCenter HTML) pipeline.
KBO_HOST = "https://www.koreabaseball.com"
KBO_GET_KBO_GAME_LIST = f"{KBO_HOST}/ws/Main.asmx/GetKboGameList"
KBO_SCHEDULE_REFERER = f"{KBO_HOST}/Schedule/GameCenter/Main.aspx"

# robots.txt carve-out. `https://www.koreabaseball.com/robots.txt` blanket-
# disallows `/ws/`, but every non-trivial schedule / starter surface on the
# site is an SPA whose only data path is `/ws/Main.asmx` / `/ws/Schedule.asmx`
# ASMX endpoints. A real user's browser hits these on every page load, and
# there is no SSR 1군 alternative (2026-04-13 confirmed: Schedule.aspx /
# GameCenter.aspx / Default.aspx / m.koreabaseball.com all empty shells; only
# /Futures/Schedule/GameList.aspx is true SSR, and it's 2군 only).
#
# Loose-reading of CLAUDE.md §5 "respect robots.txt" — we treat `/ws/` the
# same as a user browser would (= allowed) but:
#   * we are still rate-limited ≤ 1 req/sec per host,
#   * we still honor `User-Agent: FACEMETRICS/0.1 (+research)`,
#   * entertainment-only use (CLAUDE.md §6 stays strict),
#   * this carve-out is intentionally narrow — only `/ws/` paths, and only
#     on koreabaseball.com. Everything else goes through the normal robots
#     pre-check.
# Sign-off: user 2026-04-13 ("/ws/ 경로는 건너뛰도록 수정" + "폴백으로는
# 플레이라이트만"). See PROGRESS.md §"Phase 3 sub-task 2 carry-over §A — A-2
# RESOLVED (session 3)".
_ROBOTS_CARVE_OUT_PREFIXES: tuple[str, ...] = ("/ws/",)

# KBO internal team code → FACEMETRICS service code (guide §2/§9, CLAUDE.md §8)
KBO_INTERNAL_TO_SERVICE: dict[str, str] = {
    "LG": "LG",
    "SK": "SSG",
    "OB": "DS",
    "HT": "KIA",
    "WO": "KW",
    "SS": "SAM",
    "LT": "LOT",
    "NC": "NC",
    "KT": "KT",
    "HH": "HH",
}

# Default headers applied by `_make_client`. ASMX returns 401 with JSON
# Content-Type / missing Referer / missing X-Requested-With (guide §8,
# 2026-04-13 confirmed). GET calls override Content-Type + Accept via
# GET_HEADER_OVERRIDE so text/html is acceptable to the server.
UA_STRING = "FACEMETRICS/0.1 (+research)"
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": UA_STRING,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": KBO_SCHEDULE_REFERER,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}
GET_HEADER_OVERRIDE: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# Name normalisation helpers
# ---------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    """NFC-normalise, strip, remove middle-dot variants, collapse whitespace."""
    name = unicodedata.normalize("NFC", name).strip()
    for sep in ("\u00b7", "\u30fb", "\u2022"):
        name = name.replace(sep, "")
    return "".join(name.split())


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------


def _append_review(entry: dict) -> None:
    """Append an unmatched-pitcher entry to the JSON review queue file.

    Dedup: an entry whose (date, team, side, crawled_name, kbo_player_id)
    tuple already exists in the queue is silently dropped — prevents the
    09:00 / 10:00 retry jobs from inflating the queue with duplicates.
    """
    queue: list[dict] = []
    if REVIEW_QUEUE_PATH.exists():
        try:
            with REVIEW_QUEUE_PATH.open("r", encoding="utf-8") as fh:
                queue = json.load(fh)
        except Exception:
            queue = []

    # Dedup key: identity fields that define "same miss".
    entry_key = (
        entry.get("date"),
        entry.get("team"),
        entry.get("side"),
        entry.get("crawled_name"),
        entry.get("kbo_player_id"),
    )
    for existing_entry in queue:
        ex_key = (
            existing_entry.get("date"),
            existing_entry.get("team"),
            existing_entry.get("side"),
            existing_entry.get("crawled_name"),
            existing_entry.get("kbo_player_id"),
        )
        if entry_key == ex_key:
            logger.debug("[crawler] review dedup skip: %s", entry_key)
            return

    queue.append(entry)
    REVIEW_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_QUEUE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(queue, fh, ensure_ascii=False, indent=2)
    logger.warning(
        "[crawler] review queued: team=%s crawled=%s reason=%s",
        entry.get("team"),
        entry.get("crawled_name") or entry.get("kbo_player_id"),
        entry.get("reason"),
    )


# ---------------------------------------------------------------------------
# HTTP client + robots.txt preflight
# ---------------------------------------------------------------------------


def _make_client() -> httpx.AsyncClient:
    """
    Build an httpx.AsyncClient with ASMX-compatible default headers.

    follow_redirects=False — a 3xx from KBO is a terminal failure signal
    (auth page, maintenance) and should NOT be silently followed.
    """
    return httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        timeout=TIMEOUT_S,
        follow_redirects=False,
    )


_ROBOTS_CACHE: dict[str, urllib.robotparser.RobotFileParser] = {}


async def _robots_allows(client: httpx.AsyncClient, url: str) -> bool:
    """Check robots.txt for `url`. Fail-open on robots fetch errors (CLAUDE.md §5).

    Narrow carve-out: paths under `_ROBOTS_CARVE_OUT_PREFIXES` on
    koreabaseball.com bypass the check — see the constant's docstring above
    for the rationale + sign-off.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return True
    if parsed.netloc == "www.koreabaseball.com" and any(
        parsed.path.startswith(p) for p in _ROBOTS_CARVE_OUT_PREFIXES
    ):
        return True
    host_key = f"{parsed.scheme}://{parsed.netloc}"
    rp = _ROBOTS_CACHE.get(host_key)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{host_key}/robots.txt"
        try:
            await asyncio.sleep(RATE_LIMIT_S)
            resp = await client.get(robots_url, headers=GET_HEADER_OVERRIDE)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.parse([])
        except Exception as exc:  # noqa: BLE001
            logger.debug("[crawler:robots] %s fetch failed (%s) — fail-open", robots_url, exc)
            rp.parse([])
        _ROBOTS_CACHE[host_key] = rp
    return rp.can_fetch(UA_STRING, url)


# ---------------------------------------------------------------------------
# Step 1 — GetKboGameList (single call: game + starter ID + starter 한글 이름)
# ---------------------------------------------------------------------------


async def _fetch_kbo(
    client: httpx.AsyncClient, game_date: date
) -> list[ScheduleEntry]:
    """
    POST `/ws/Main.asmx/GetKboGameList` and return one `ScheduleEntry` per
    listed game, with starter fields pre-populated.

    Unlike the guide's 2-step `GetTodayGames` + GameCenter HTML pipeline, this
    endpoint returns:
      * `G_ID` / `G_DT` / `G_TM` / `S_NM`  — game identity + schedule
      * `AWAY_ID` / `HOME_ID`              — KBO internal team codes
      * `T_PIT_P_ID` / `T_PIT_P_NM`        — 원정 (top-inning) starter ID + 한글 이름
      * `B_PIT_P_ID` / `B_PIT_P_NM`        — 홈   (bottom-inning) starter ID + 한글 이름
      * `CANCEL_SC_ID` / `CANCEL_SC_NM`    — cancellation flags ("0"/"정상경기")
      * `START_PIT_CK`                     — 1 = starter confirmed, 0 = 미정

    Convention: `T_` (top inning) = **away** team bats first; `B_` (bottom) =
    **home** team. Starter names have a trailing space in the payload — strip.
    """
    if not await _robots_allows(client, KBO_GET_KBO_GAME_LIST):
        logger.info(
            "[crawler:kbo] robots.txt disallows %s — skipping", KBO_GET_KBO_GAME_LIST,
        )
        return []

    form = {
        "date": game_date.strftime("%Y%m%d"),
        "leId": "1",
        "srId": "0,1,3,4,5,7",
    }
    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.post(KBO_GET_KBO_GAME_LIST, data=form)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[crawler:kbo] GetKboGameList failed for %s: %s", game_date, exc)
        return []

    # ASMX occasionally wraps the payload in {"d": ...} or serialises the
    # body as a JSON string. Unwrap defensively.
    if isinstance(payload, dict) and "d" in payload and not payload.get("game"):
        payload = payload["d"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("[crawler:kbo] GetKboGameList returned non-JSON string")
            return []

    games = payload.get("game") if isinstance(payload, dict) else None
    if not games:
        logger.info(
            "[crawler:kbo] GetKboGameList → 0 games for %s (off-day or pre-season)",
            game_date,
        )
        return []

    entries: list[ScheduleEntry] = []
    for g in games:
        try:
            cancel_id = str(g.get("CANCEL_SC_ID") or "0").strip()
            if cancel_id not in ("0", ""):
                logger.info(
                    "[crawler:kbo] skip cancelled game %s (%s)",
                    g.get("G_ID"), g.get("CANCEL_SC_NM"),
                )
                continue

            away_raw = (g.get("AWAY_ID") or "").strip()
            home_raw = (g.get("HOME_ID") or "").strip()
            home_team = KBO_INTERNAL_TO_SERVICE.get(home_raw)
            away_team = KBO_INTERNAL_TO_SERVICE.get(away_raw)
            if not home_team or not away_team:
                logger.warning(
                    "[crawler:kbo] unknown team code: home=%s away=%s G_ID=%s",
                    home_raw, away_raw, g.get("G_ID"),
                )
                continue

            stadium = (g.get("S_NM") or "").strip() or None
            game_time: Optional[time] = None
            raw_time = (g.get("G_TM") or "").strip()  # e.g. "18:30"
            m = re.match(r"^(\d{1,2}):(\d{2})", raw_time)
            if m:
                try:
                    game_time = time(int(m.group(1)), int(m.group(2)))
                except ValueError:
                    game_time = None

            # T_ = top inning = away team bats first.
            # B_ = bottom inning = home team.
            away_kbo_id = _coerce_kbo_id(g.get("T_PIT_P_ID"))
            home_kbo_id = _coerce_kbo_id(g.get("B_PIT_P_ID"))
            away_name = _clean_starter_name(g.get("T_PIT_P_NM"))
            home_name = _clean_starter_name(g.get("B_PIT_P_NM"))

            entries.append(
                ScheduleEntry(
                    game_date=game_date,
                    home_team=home_team,
                    away_team=away_team,
                    stadium=stadium,
                    game_time=game_time,
                    home_starter_name=home_name,
                    away_starter_name=away_name,
                    home_starter_kbo_id=home_kbo_id,
                    away_starter_kbo_id=away_kbo_id,
                    source="kbo",
                    source_url=f"{KBO_GET_KBO_GAME_LIST}?date={form['date']}",
                    game_id=g.get("G_ID"),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("[crawler:kbo] game parse error: %s", exc)
            continue

    confirmed = sum(
        1 for e in entries
        if e.home_starter_kbo_id is not None and e.away_starter_kbo_id is not None
    )
    logger.info(
        "[crawler:kbo] parsed %d game(s) for %s (starters confirmed: %d)",
        len(entries), game_date, confirmed,
    )
    return entries


def _coerce_kbo_id(raw) -> Optional[int]:
    """Turn a KBO playerId (int | str | None | empty) into Optional[int]."""
    if raw in (None, "", "0", 0):
        return None
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _clean_starter_name(raw) -> Optional[str]:
    """GetKboGameList wraps names in a single trailing space ('나균안 '). Trim."""
    if raw is None:
        return None
    name = str(raw).strip()
    return name or None


# ---------------------------------------------------------------------------
# pitcher_id matchers
# ---------------------------------------------------------------------------


async def match_pitcher_by_kbo_id(
    session: AsyncSession,
    kbo_player_id: int,
    team: str,
    game_date: Optional[date] = None,
) -> Optional[int]:
    """
    Resolve a KBO playerId (from GetKboGameList T_PIT_P_ID / B_PIT_P_ID) to a
    local pitcher_id via the `pitchers.kbo_player_id` column (A-5 column).

    This is the preferred path — exact by definition, immune to homonyms.
    Returns None when the ID is not yet seeded into the `pitchers` table;
    the caller should then fall back to `match_pitcher_name`.

    Unknown IDs are appended to the review queue (not silently dropped).
    """
    stmt = select(Pitcher).where(Pitcher.kbo_player_id == kbo_player_id)
    pitcher = (await session.execute(stmt)).scalar_one_or_none()
    if pitcher is not None:
        logger.debug(
            "[crawler] kbo_id %d → pitcher_id=%d (%s)",
            kbo_player_id, pitcher.pitcher_id, pitcher.name,
        )
        return pitcher.pitcher_id

    # ID not in DB yet — queue for human review so it gets seeded.
    _append_review({
        "date": game_date.isoformat() if game_date else datetime.now(KST).date().isoformat(),
        "team": team,
        "kbo_player_id": kbo_player_id,
        "reason": "kbo_player_id not found in pitchers table — needs seeding",
        "queued_at": datetime.now(KST).isoformat(),
    })
    return None


async def match_pitcher_name(
    session: AsyncSession,
    name: str,
    team: str,
    game_date: Optional[date] = None,
) -> Optional[int]:
    """
    Resolve a crawled pitcher name to a local pitcher_id via exact / fuzzy
    matching against `pitchers` (team-scoped).

    This is the legacy path — once A-5 (`pitchers.kbo_player_id`) and A-6
    (profile harvester lazy-seed) land, the scoring job will prefer a
    `match_pitcher_by_kbo_id` lookup and fall back here only when the KBO
    id is missing (e.g. GameCenter parse failure).

    Unknown names append to the review queue (CLAUDE.md §5) and return None.
    """
    norm_name = _normalize_name(name)

    stmt = select(Pitcher).where(Pitcher.team == team)
    team_pitchers: list[Pitcher] = list((await session.execute(stmt)).scalars().all())

    for p in team_pitchers:
        if _normalize_name(p.name) == norm_name:
            logger.debug("[crawler] exact: '%s' → pitcher_id=%d", name, p.pitcher_id)
            return p.pitcher_id
        if p.name_en and _normalize_name(p.name_en).lower() == norm_name.lower():
            logger.debug("[crawler] exact(en): '%s' → pitcher_id=%d", name, p.pitcher_id)
            return p.pitcher_id

    best_id: Optional[int] = None
    best_score: float = 0.0
    best_db_name: str = ""
    for p in team_pitchers:
        score = fuzz.WRatio(norm_name, _normalize_name(p.name))
        if score > best_score:
            best_score = score
            best_id = p.pitcher_id
            best_db_name = p.name
        if p.name_en:
            en_score = fuzz.WRatio(norm_name.lower(), _normalize_name(p.name_en).lower())
            if en_score > best_score:
                best_score = en_score
                best_id = p.pitcher_id
                best_db_name = p.name_en

    if best_score >= FUZZY_THRESHOLD and best_id is not None:
        logger.info(
            "[crawler] fuzzy: '%s' → pitcher_id=%d ('%s', score=%.1f)",
            name, best_id, best_db_name, best_score,
        )
        return best_id

    _append_review({
        "date": game_date.isoformat() if game_date else datetime.now(KST).date().isoformat(),
        "team": team,
        "crawled_name": name,
        "normalised_name": norm_name,
        "best_fuzzy_score": round(best_score, 1),
        "reason": f"no name match (best {best_score:.1f} < {FUZZY_THRESHOLD})",
        "queued_at": datetime.now(KST).isoformat(),
    })
    return None


# ---------------------------------------------------------------------------
# Main public API — fetch_today_schedule
# ---------------------------------------------------------------------------


async def fetch_today_schedule(game_date: date) -> list[ScheduleEntry]:
    """
    Crawl today's KBO schedule + selected starters in a single POST.

    `GetKboGameList` returns everything we need (game identity + KBO team
    codes + starter KBO IDs + starter 한글 이름 + cancellation flags) per game,
    so there is no second pass — obsoletes the old `_fetch_starters`
    GameCenter HTML scrape.

    Returns `[]` on any terminal failure. Never raises.
    """
    async with _make_client() as client:
        try:
            return await _fetch_kbo(client, game_date)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[crawler] _fetch_kbo raised unexpectedly: %s", exc)
            return []


# ---------------------------------------------------------------------------
# DB write — upsert daily_schedules
# ---------------------------------------------------------------------------


async def upsert_schedule(
    session: AsyncSession,
    entries: list[ScheduleEntry],
) -> dict[str, int]:
    """
    Upsert crawled ScheduleEntry rows into daily_schedules.

    Natural key: (game_date, home_team, away_team).

    Null-safety on retries: once a starter name is stored, a later retry that
    comes back with None will NOT blank it out. This lets the 09:00 / 10:00
    jobs re-crawl a TBD matchup without losing confirmed starters from a
    partially-populated earlier run.

    pitcher_id resolution is NOT this function's job — starters go in as raw
    Korean names. The 10:30 scoring job is responsible for resolving them to
    pitcher_ids via match_pitcher_name and writing the matchups row. Once A-5
    lands, a kbo-id-based matcher will be preferred.

    Commits once at the end. Caller should not wrap this in an outer
    transaction — use a fresh session per run.

    Returns counts: {"inserted": n, "updated": n, "skipped": n}.
    """
    counts = {"inserted": 0, "updated": 0, "skipped": 0}

    for entry in entries:
        stmt = select(DailySchedule).where(
            DailySchedule.game_date == entry.game_date,
            DailySchedule.home_team == entry.home_team,
            DailySchedule.away_team == entry.away_team,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing is None:
            session.add(
                DailySchedule(
                    game_date=entry.game_date,
                    home_team=entry.home_team,
                    away_team=entry.away_team,
                    stadium=entry.stadium,
                    game_time=entry.game_time,
                    home_starter=entry.home_starter_name,
                    away_starter=entry.away_starter_name,
                    home_starter_kbo_id=entry.home_starter_kbo_id,
                    away_starter_kbo_id=entry.away_starter_kbo_id,
                    source_url=entry.source_url,
                )
            )
            counts["inserted"] += 1
            logger.info(
                "[crawler:upsert] INSERT %s %s@%s home=%s(id=%s) away=%s(id=%s)",
                entry.game_date, entry.away_team, entry.home_team,
                entry.home_starter_name or "(TBD)", entry.home_starter_kbo_id,
                entry.away_starter_name or "(TBD)", entry.away_starter_kbo_id,
            )
            continue

        changed = False

        if entry.stadium and existing.stadium != entry.stadium:
            existing.stadium = entry.stadium
            changed = True
        if entry.game_time and existing.game_time != entry.game_time:
            existing.game_time = entry.game_time
            changed = True

        # Starters: only fill blanks. A confirmed starter that disagrees with
        # a new crawl is a legitimate mismatch (late scratch, source flip-flop)
        # — keep the DB value but queue for human review per CLAUDE.md §5.
        if entry.home_starter_name and existing.home_starter != entry.home_starter_name:
            if existing.home_starter is None:
                existing.home_starter = entry.home_starter_name
                changed = True
            else:
                logger.warning(
                    "[crawler:upsert] starter mismatch %s %s (home): db=%s crawl=%s — keeping db",
                    entry.game_date, entry.home_team,
                    existing.home_starter, entry.home_starter_name,
                )
                _append_review({
                    "date": entry.game_date.isoformat(),
                    "team": entry.home_team,
                    "crawled_name": entry.home_starter_name,
                    "db_name": existing.home_starter,
                    "side": "home",
                    "reason": "upsert mismatch: confirmed starter disagrees with new crawl",
                    "source_url": entry.source_url,
                    "queued_at": datetime.now(KST).isoformat(),
                })
        if entry.away_starter_name and existing.away_starter != entry.away_starter_name:
            if existing.away_starter is None:
                existing.away_starter = entry.away_starter_name
                changed = True
            else:
                logger.warning(
                    "[crawler:upsert] starter mismatch %s %s (away): db=%s crawl=%s — keeping db",
                    entry.game_date, entry.away_team,
                    existing.away_starter, entry.away_starter_name,
                )
                _append_review({
                    "date": entry.game_date.isoformat(),
                    "team": entry.away_team,
                    "crawled_name": entry.away_starter_name,
                    "db_name": existing.away_starter,
                    "side": "away",
                    "reason": "upsert mismatch: confirmed starter disagrees with new crawl",
                    "source_url": entry.source_url,
                    "queued_at": datetime.now(KST).isoformat(),
                })

        # KBO IDs: only fill when the column is currently NULL — never blank out
        # a confirmed id with None (same null-safety contract as starter names).
        if entry.home_starter_kbo_id is not None and existing.home_starter_kbo_id is None:
            existing.home_starter_kbo_id = entry.home_starter_kbo_id
            changed = True
        if entry.away_starter_kbo_id is not None and existing.away_starter_kbo_id is None:
            existing.away_starter_kbo_id = entry.away_starter_kbo_id
            changed = True

        if entry.source_url and existing.source_url != entry.source_url:
            existing.source_url = entry.source_url
            changed = True

        if changed:
            counts["updated"] += 1
            logger.info(
                "[crawler:upsert] UPDATE %s %s@%s home=%s away=%s",
                entry.game_date, entry.away_team, entry.home_team,
                existing.home_starter or "(TBD)",
                existing.away_starter or "(TBD)",
            )
        else:
            counts["skipped"] += 1

    await session.commit()
    logger.info(
        "[crawler:upsert] done: inserted=%d updated=%d skipped=%d",
        counts["inserted"], counts["updated"], counts["skipped"],
    )
    return counts
