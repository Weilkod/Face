"""
services/crawler.py — KBO schedule + starting-pitcher crawler.

Fallback chain (CLAUDE.md §5):
  1. KBO 공식 (koreabaseball.com)
  2. 네이버 스포츠 (sports.naver.com)
  3. 스탯티즈 (statiz.co.kr)

Public API
----------
  fetch_today_schedule(game_date)        -> list[ScheduleEntry]
  match_pitcher_name(session, name, team) -> int | None

Unknown crawled names are appended to data/crawler_review_queue.json
rather than silently dropped (CLAUDE.md §5 requirement).

HTTP rules
----------
  - httpx.AsyncClient with custom UA header
  - Per-host rate limit: asyncio.sleep(1) between requests to same host
  - Timeout: 10 s
  - No sync requests.get anywhere in this module

CSS selector constants are grouped at the top of each source section so
a single-line patch fixes a broken selector without hunting through logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import unicodedata
import urllib.robotparser
from datetime import date, datetime, time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
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
FUZZY_THRESHOLD = 85  # rapidfuzz WRatio minimum for a fuzzy match

REVIEW_QUEUE_PATH = PROJECT_ROOT / "data" / "crawler_review_queue.json"

UA_HEADER = {
    "User-Agent": "FACEMETRICS/0.1 (+research)"
}

# ---------------------------------------------------------------------------
# KBO 공식 — koreabaseball.com
# ---------------------------------------------------------------------------
# Target: https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx?gameDate=20260413
# (or the mobile schedule page — we target the latter as it's simpler HTML)
KBO_SCHEDULE_URL = "https://www.koreabaseball.com/Schedule/Schedule.aspx"
# CSS selectors — update these if the KBO site restructures
KBO_ROW_SEL = "table.tbl-type01 tr, table.schedule_list tr"
KBO_TIME_SEL = "td.time, td:nth-child(1)"
KBO_TEAMS_SEL = "td.home, td.away, td.team"
KBO_STADIUM_SEL = "td.stadium, td.place"
KBO_STARTER_SEL = "td.pitcher, td.starting"

# ---------------------------------------------------------------------------
# 네이버 스포츠 — sports.naver.com
# ---------------------------------------------------------------------------
# Target: https://sports.naver.com/baseball/schedule/index
# Daily schedule with starting pitcher info lives at this API endpoint:
NAVER_SCHEDULE_URL = (
    "https://api-gw.sports.naver.com/schedule/games"
    "?fields=basic,stadium,pitchers"
    "&upperCategoryId=kbaseball"
    "&categoryId=kbo"
    "&gameDate={date_str}"
    "&pageSize=10"
)
# Verified 2026-04-13: GET /schedule/games?...&gameDate=20260413 returns
#   {"code":200,"success":true,"result":{"games":[],"gameTotalCount":0}}
# The endpoint is live and reachable; games array will populate once the
# KBO 2026 season schedule data is loaded into Naver's system.
# HTML fallback (if API fails):
NAVER_HTML_URL = "https://sports.naver.com/kbaseball/schedule/index"
# Verified 2026-04-13: returns 200 but is a JS SPA (1.8 KB shell, no game data in HTML).
# HTML fallback will match 0 elements until Naver provides SSR game rows.
# The JSON API above is the preferred path.
# CSS selectors for the HTML page
NAVER_GAME_SEL = "ul.sch_list li.sch_item, div.game_card"
NAVER_HOME_SEL = ".home_team .team_name, .lft .team_name"
NAVER_AWAY_SEL = ".away_team .team_name, .rgt .team_name"
NAVER_STADIUM_SEL = ".stadium, .place"
NAVER_TIME_SEL = ".time, .game_time"
NAVER_STARTER_SEL = ".pitcher_name, .starting_pitcher"

# ---------------------------------------------------------------------------
# 스탯티즈 — statiz.co.kr
# ---------------------------------------------------------------------------
# Target: http://www.statiz.co.kr/schedule.php?opt=1&sy=2026&sm=04&sd=13
STATIZ_SCHEDULE_URL = "http://www.statiz.co.kr/schedule.php"
STATIZ_GAME_SEL = "table.maintable tr.row0, table.maintable tr.row1"
STATIZ_TEAMS_SEL = "td.team, td a[href*='teamCode']"
STATIZ_STARTER_SEL = "td.pitcher, td a[href*='playerId']"
STATIZ_STADIUM_SEL = "td.stadium"
STATIZ_TIME_SEL = "td.time"

# ---------------------------------------------------------------------------
# KBO team name → internal code mapping
# ---------------------------------------------------------------------------
# Covers common Korean abbreviations / full names found on each site.
TEAM_NAME_MAP: dict[str, str] = {
    # KBO official names
    "LG": "LG",
    "LG트윈스": "LG",
    "SSG": "SSG",
    "SSG랜더스": "SSG",
    "KT": "KT",
    "KT위즈": "KT",
    "NC": "NC",
    "NC다이노스": "NC",
    "두산": "DS",
    "DS": "DS",
    "두산베어스": "DS",
    "KIA": "KIA",
    "KIA타이거즈": "KIA",
    "롯데": "LOT",
    "LOT": "LOT",
    "롯데자이언츠": "LOT",
    "삼성": "SAM",
    "SAM": "SAM",
    "삼성라이온즈": "SAM",
    "한화": "HH",
    "HH": "HH",
    "한화이글스": "HH",
    "키움": "KW",
    "KW": "KW",
    "키움히어로즈": "KW",
    # Naver / Statiz alternate spellings
    "기아": "KIA",
    "기아타이거즈": "KIA",
}


def _normalize_team(raw: str) -> Optional[str]:
    """Normalise a scraped team name to one of the 10 internal codes."""
    raw = raw.strip()
    code = TEAM_NAME_MAP.get(raw)
    if code:
        return code
    # Try partial match for e.g. "SSG 랜더스"
    for key, val in TEAM_NAME_MAP.items():
        if key in raw:
            return val
    return None


# ---------------------------------------------------------------------------
# Name normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """
    NFC normalise, strip whitespace, remove middle-dot variants.
    Handles: leading/trailing spaces, NFC/NFD mixed Korean, ·(U+00B7).
    """
    name = unicodedata.normalize("NFC", name).strip()
    # Remove middle-dot and similar separators sometimes inserted by sites
    name = name.replace("\u00b7", "").replace("\u30fb", "").replace("\u2022", "")
    # Collapse internal whitespace (e.g. "곽 빈" → "곽빈")
    name = "".join(name.split())
    return name


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

def _append_review(entry: dict) -> None:
    """Append an unmatched-pitcher entry to the JSON review queue file."""
    queue: list[dict] = []
    if REVIEW_QUEUE_PATH.exists():
        try:
            with REVIEW_QUEUE_PATH.open("r", encoding="utf-8") as fh:
                queue = json.load(fh)
        except Exception:
            queue = []
    queue.append(entry)
    REVIEW_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_QUEUE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(queue, fh, ensure_ascii=False, indent=2)
    logger.warning(
        "[crawler] unmatched pitcher queued: team=%s name=%s reason=%s",
        entry.get("team"),
        entry.get("crawled_name"),
        entry.get("reason"),
    )


# ---------------------------------------------------------------------------
# Name → pitcher_id matcher
# ---------------------------------------------------------------------------

async def match_pitcher_name(
    session: AsyncSession,
    name: str,
    team: str,
    game_date: Optional[date] = None,
) -> Optional[int]:
    """
    Resolve a crawled pitcher name to a pitcher_id.

    Steps:
      1. Exact match on (normalised name, team).
      2. Fuzzy match: rapidfuzz WRatio >= FUZZY_THRESHOLD scoped to same team.
      3. If still unmatched: append to review queue, return None.

    Does NOT raise on failure — callers can safely treat None as "unknown".
    """
    norm_name = _normalize_name(name)

    # Pull all pitchers for this team (small set — no perf concern)
    stmt = select(Pitcher).where(Pitcher.team == team)
    result = await session.execute(stmt)
    team_pitchers: list[Pitcher] = list(result.scalars().all())

    # 1. Exact match (normalised)
    for p in team_pitchers:
        db_name = _normalize_name(p.name)
        if db_name == norm_name:
            logger.debug(
                "[crawler] exact match: '%s' → pitcher_id=%d (%s)", name, p.pitcher_id, p.name
            )
            return p.pitcher_id
        # Also check English name if present (for foreign players)
        if p.name_en:
            db_en = _normalize_name(p.name_en).lower()
            if db_en == norm_name.lower():
                logger.debug(
                    "[crawler] exact match (en): '%s' → pitcher_id=%d (%s)",
                    name, p.pitcher_id, p.name_en,
                )
                return p.pitcher_id

    # 2. Fuzzy match
    best_id: Optional[int] = None
    best_score: float = 0.0
    best_db_name: str = ""
    for p in team_pitchers:
        db_name = _normalize_name(p.name)
        score = fuzz.WRatio(norm_name, db_name)
        if score > best_score:
            best_score = score
            best_id = p.pitcher_id
            best_db_name = p.name
        # Also try English name
        if p.name_en:
            en_score = fuzz.WRatio(norm_name.lower(), _normalize_name(p.name_en).lower())
            if en_score > best_score:
                best_score = en_score
                best_id = p.pitcher_id
                best_db_name = p.name_en or p.name

    if best_score >= FUZZY_THRESHOLD and best_id is not None:
        logger.info(
            "[crawler] fuzzy match: '%s' → pitcher_id=%d ('%s', score=%.1f)",
            name, best_id, best_db_name, best_score,
        )
        return best_id

    # 3. Unmatched — add to review queue, return None
    review_entry = {
        "date": game_date.isoformat() if game_date else datetime.now(KST).date().isoformat(),
        "team": team,
        "crawled_name": name,
        "normalised_name": norm_name,
        "best_fuzzy_score": round(best_score, 1),
        "reason": f"no match (best score {best_score:.1f} < {FUZZY_THRESHOLD})",
        "queued_at": datetime.now(KST).isoformat(),
    }
    _append_review(review_entry)
    return None


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------

def _make_client() -> httpx.AsyncClient:
    # follow_redirects=False: Statiz redirects unauthenticated GETs to a login
    # page; following those masks the source-unavailable signal. Any 3xx is
    # treated as a terminal failure and handled by the caller's try/except.
    return httpx.AsyncClient(
        headers=UA_HEADER,
        timeout=TIMEOUT_S,
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# robots.txt preflight
# ---------------------------------------------------------------------------

_ROBOTS_CACHE: dict[str, urllib.robotparser.RobotFileParser] = {}


class _RobotsBlocked(Exception):
    """Internal sentinel — raised when robots.txt forbids a specific URL.

    Separate from httpx errors so log handlers can distinguish "we chose not
    to fetch" from "the server returned an error".
    """


async def _robots_allows(client: httpx.AsyncClient, url: str) -> bool:
    """
    Return True if robots.txt at the URL's host allows the UA to fetch the URL.

    One RobotFileParser is cached per host. Network failures fetching robots.txt
    are treated as "allow" (fail-open) so a transient 500 on /robots.txt doesn't
    take down the crawler — CLAUDE.md §5 asks us to respect robots, not to hard-
    fail when the robots endpoint itself is broken.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return True
    host_key = f"{parsed.scheme}://{parsed.netloc}"
    rp = _ROBOTS_CACHE.get(host_key)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{host_key}/robots.txt"
        try:
            # Rate-limit the robots.txt fetch itself — the data fetch that
            # follows hits the same host, so without this we'd issue two
            # requests with zero gap on cold cache (CLAUDE.md §5 ≤1 req/sec).
            await asyncio.sleep(RATE_LIMIT_S)
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.parse([])  # empty → allow_all
        except Exception as exc:  # noqa: BLE001
            logger.debug("[crawler:robots] %s fetch failed (%s) — fail-open", robots_url, exc)
            rp.parse([])
        _ROBOTS_CACHE[host_key] = rp
    return rp.can_fetch(UA_HEADER["User-Agent"], url)


# ---------------------------------------------------------------------------
# Source 1 — KBO 공식 (koreabaseball.com)
# ---------------------------------------------------------------------------

async def _fetch_kbo(client: httpx.AsyncClient, game_date: date) -> list[ScheduleEntry]:
    """
    Scrape the KBO official schedule page.

    Target URL: https://www.koreabaseball.com/Schedule/Schedule.aspx
    The page accepts a POST or has a ?date= param; we attempt GET with query.

    NOTE: This parser is SPECULATIVE — the KBO site requires session cookies
    and anti-scraping measures.  In live use this will likely return an empty
    list (site blocks headless requests) and the crawler will fall through to
    Naver.  The selector constants at the top of the file document what we
    would parse if the HTML were accessible.
    """
    date_str = game_date.strftime("%Y%m%d")
    url = f"{KBO_SCHEDULE_URL}?gameDate={date_str}"
    if not await _robots_allows(client, url):
        logger.info("[crawler:kbo] robots.txt disallows %s — skipping source", url)
        return []
    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.get(url)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("[crawler:kbo] HTTP error for %s: %s", url, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    entries: list[ScheduleEntry] = []

    # The KBO site renders a <table> with one <tr> per game.
    # Each row structure (approximate — verify against live HTML):
    #   <td class="time">18:30</td>
    #   <td class="away"><span class="team">LG</span><span class="pitcher">손주영</span></td>
    #   <td class="stadium">잠실</td>
    #   <td class="home"><span class="team">두산</span><span class="pitcher">곽빈</span></td>
    rows = soup.select(KBO_ROW_SEL)
    if not rows:
        logger.warning(
            "[crawler:kbo] selector '%s' matched 0 rows — site HTML may have changed",
            KBO_ROW_SEL,
        )
        return []

    for row in rows:
        try:
            time_cell = row.select_one(KBO_TIME_SEL)
            stadium_cell = row.select_one(KBO_STADIUM_SEL)
            starter_cells = row.select(KBO_STARTER_SEL)

            # Extract team names (expect away first, home second)
            team_cells = row.select("td.team")
            if len(team_cells) < 2:
                continue

            away_raw = team_cells[0].get_text(strip=True)
            home_raw = team_cells[1].get_text(strip=True)
            away_team = _normalize_team(away_raw)
            home_team = _normalize_team(home_raw)
            if not away_team or not home_team:
                logger.debug("[crawler:kbo] could not normalise teams: %s vs %s", away_raw, home_raw)
                continue

            game_time: Optional[time] = None
            if time_cell:
                try:
                    t_str = time_cell.get_text(strip=True).replace(":", "")
                    if len(t_str) == 4:
                        game_time = time(int(t_str[:2]), int(t_str[2:]))
                except Exception:
                    pass

            stadium: Optional[str] = None
            if stadium_cell:
                stadium = stadium_cell.get_text(strip=True) or None

            away_starter: Optional[str] = None
            home_starter: Optional[str] = None
            if len(starter_cells) >= 2:
                away_starter = starter_cells[0].get_text(strip=True) or None
                home_starter = starter_cells[1].get_text(strip=True) or None

            entries.append(
                ScheduleEntry(
                    game_date=game_date,
                    home_team=home_team,
                    away_team=away_team,
                    stadium=stadium,
                    game_time=game_time,
                    home_starter_name=home_starter,
                    away_starter_name=away_starter,
                    source="kbo",
                    source_url=url,
                )
            )
        except Exception as exc:
            logger.debug("[crawler:kbo] row parse error: %s", exc)
            continue

    logger.info("[crawler:kbo] parsed %d entries for %s", len(entries), game_date)
    return entries


# ---------------------------------------------------------------------------
# Source 2 — 네이버 스포츠 (sports.naver.com)
# ---------------------------------------------------------------------------

async def _fetch_naver(client: httpx.AsyncClient, game_date: date) -> list[ScheduleEntry]:
    """
    Fetch KBO schedule from the Naver Sports JSON API, falling back to
    HTML scraping if the API returns a non-200 or unexpected shape.

    API endpoint (no auth required as of 2026):
      https://api-gw.sports.naver.com/schedule/games?...

    The JSON response shape (approximate):
    {
      "result": {
        "games": [
          {
            "homeTeamCode": "LG",
            "awayTeamCode": "SS",   <-- Naver uses 2-char codes
            "stadium": "잠실야구장",
            "gameDateTime": "20260413183000",
            "homeStartingPitcherName": "임찬규",
            "awayStartingPitcherName": "카스타노"
          }
        ]
      }
    }

    NOTE: The Naver API endpoint and JSON shape are SPECULATIVE — they are
    based on publicly observed network calls and may change.  Parsing
    failures are caught and fall through to statiz.
    """
    # Naver API sometimes uses a 2-char team code that differs from ours.
    # "SS" historically means Samsung; SSG is usually "SK" (legacy SK Wyverns).
    # Verify on first real game day — if Naver sends a different code for SSG,
    # _normalize_team() will catch it via TEAM_NAME_MAP fallback.
    NAVER_TEAM_MAP = {
        "LG": "LG", "SK": "SSG", "KT": "KT", "NC": "NC",
        "OB": "DS", "HT": "KIA", "LT": "LOT", "SS": "SAM",
        "HH": "HH", "WO": "KW",
        # Alternate codes seen in responses:
        "SSG": "SSG", "DS": "DS", "SAM": "SAM", "KIA": "KIA",
        "LOT": "LOT", "KW": "KW",
    }

    date_str = game_date.strftime("%Y%m%d")
    api_url = NAVER_SCHEDULE_URL.format(date_str=date_str)
    # Verified endpoint: returns {"code":200,"result":{"games":[...],"gameTotalCount":N}}
    entries: list[ScheduleEntry] = []
    api_allowed = await _robots_allows(client, api_url)
    if not api_allowed:
        logger.info("[crawler:naver] robots.txt disallows %s — skipping API", api_url)

    # --- Try JSON API first ---
    try:
        if not api_allowed:
            raise _RobotsBlocked(api_url)
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.get(api_url)
        resp.raise_for_status()
        data = resp.json()

        games = (
            data.get("result", {}).get("games")
            or data.get("games")
            or []
        )

        for g in games:
            try:
                home_raw = g.get("homeTeamCode", "")
                away_raw = g.get("awayTeamCode", "")
                home_team = NAVER_TEAM_MAP.get(home_raw) or _normalize_team(home_raw)
                away_team = NAVER_TEAM_MAP.get(away_raw) or _normalize_team(away_raw)
                if not home_team or not away_team:
                    continue

                dt_str = g.get("gameDateTime", "")  # "20260413183000"
                game_time: Optional[time] = None
                if len(dt_str) >= 12:
                    try:
                        game_time = time(int(dt_str[8:10]), int(dt_str[10:12]))
                    except Exception:
                        pass

                home_starter = g.get("homeStartingPitcherName") or g.get("homeStarterName") or None
                away_starter = g.get("awayStartingPitcherName") or g.get("awayStarterName") or None

                entries.append(
                    ScheduleEntry(
                        game_date=game_date,
                        home_team=home_team,
                        away_team=away_team,
                        stadium=g.get("stadium") or g.get("stadiumName"),
                        game_time=game_time,
                        home_starter_name=home_starter,
                        away_starter_name=away_starter,
                        source="naver",
                        source_url=api_url,
                    )
                )
            except Exception as exc:
                logger.debug("[crawler:naver-api] game parse error: %s", exc)
                continue

        if entries:
            logger.info("[crawler:naver-api] parsed %d entries for %s", len(entries), game_date)
            return entries
        else:
            logger.warning("[crawler:naver-api] API returned 0 games for %s — trying HTML", game_date)

    except _RobotsBlocked:
        # Already logged at info level above; this branch exists only to
        # keep the block out of the generic "API call failed" warning.
        pass
    except Exception as exc:
        logger.warning("[crawler:naver-api] API call failed: %s — trying HTML fallback", exc)

    # --- HTML fallback ---
    html_url = NAVER_HTML_URL
    if not await _robots_allows(client, html_url):
        logger.info("[crawler:naver] robots.txt disallows %s — skipping HTML", html_url)
        return []
    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.get(html_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        game_blocks = soup.select(NAVER_GAME_SEL)
        if not game_blocks:
            logger.warning(
                "[crawler:naver-html] selector '%s' matched 0 blocks — HTML may have changed",
                NAVER_GAME_SEL,
            )
            return []

        for block in game_blocks:
            try:
                home_el = block.select_one(NAVER_HOME_SEL)
                away_el = block.select_one(NAVER_AWAY_SEL)
                if not home_el or not away_el:
                    continue
                home_team = _normalize_team(home_el.get_text(strip=True))
                away_team = _normalize_team(away_el.get_text(strip=True))
                if not home_team or not away_team:
                    continue

                stadium_el = block.select_one(NAVER_STADIUM_SEL)
                time_el = block.select_one(NAVER_TIME_SEL)
                starter_els = block.select(NAVER_STARTER_SEL)

                stadium = stadium_el.get_text(strip=True) if stadium_el else None
                game_time = None
                if time_el:
                    try:
                        parts = time_el.get_text(strip=True).replace(":", "")
                        if len(parts) == 4:
                            game_time = time(int(parts[:2]), int(parts[2:]))
                    except Exception:
                        pass

                home_starter = starter_els[0].get_text(strip=True) if len(starter_els) > 0 else None
                away_starter = starter_els[1].get_text(strip=True) if len(starter_els) > 1 else None

                entries.append(
                    ScheduleEntry(
                        game_date=game_date,
                        home_team=home_team,
                        away_team=away_team,
                        stadium=stadium,
                        game_time=game_time,
                        home_starter_name=home_starter or None,
                        away_starter_name=away_starter or None,
                        source="naver",
                        source_url=html_url,
                    )
                )
            except Exception as exc:
                logger.debug("[crawler:naver-html] block parse error: %s", exc)
                continue

        logger.info("[crawler:naver-html] parsed %d entries for %s", len(entries), game_date)
    except Exception as exc:
        logger.warning("[crawler:naver-html] HTML scrape failed: %s", exc)

    return entries


# ---------------------------------------------------------------------------
# Source 3 — 스탯티즈 (statiz.co.kr)
# ---------------------------------------------------------------------------

async def _fetch_statiz(client: httpx.AsyncClient, game_date: date) -> list[ScheduleEntry]:
    """
    Scrape statiz.co.kr schedule page.

    Target: http://www.statiz.co.kr/schedule.php?opt=1&sy=YYYY&sm=MM&sd=DD

    HTML table structure (approximate — verify against live HTML):
    <table class="maintable">
      <tr class="row0">
        <td class="time">18:30</td>
        <td class="team"><a href="...">LG</a></td>
        <td class="team"><a href="...">두산</a></td>
        <td class="stadium">잠실</td>
        <td class="pitcher"><a href="...">임찬규</a></td>
        <td class="pitcher"><a href="...">곽빈</a></td>
      </tr>
    </table>

    NOTE: The exact selector and column order are SPECULATIVE.
    """
    url = (
        f"{STATIZ_SCHEDULE_URL}"
        f"?opt=1&sy={game_date.year}&sm={game_date.month:02d}&sd={game_date.day:02d}"
    )
    if not await _robots_allows(client, url):
        logger.info("[crawler:statiz] robots.txt disallows %s — skipping source", url)
        return []
    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.get(url)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("[crawler:statiz] HTTP error for %s: %s", url, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select(STATIZ_GAME_SEL)
    if not rows:
        logger.warning(
            "[crawler:statiz] selector '%s' matched 0 rows — HTML may have changed",
            STATIZ_GAME_SEL,
        )
        return []

    entries: list[ScheduleEntry] = []
    for row in rows:
        try:
            time_cell = row.select_one(STATIZ_TIME_SEL)
            team_cells = row.select(STATIZ_TEAMS_SEL)
            stadium_cell = row.select_one(STATIZ_STADIUM_SEL)
            starter_cells = row.select(STATIZ_STARTER_SEL)

            if len(team_cells) < 2:
                continue

            away_raw = team_cells[0].get_text(strip=True)
            home_raw = team_cells[1].get_text(strip=True)
            away_team = _normalize_team(away_raw)
            home_team = _normalize_team(home_raw)
            if not away_team or not home_team:
                continue

            game_time = None
            if time_cell:
                try:
                    parts = time_cell.get_text(strip=True).replace(":", "")
                    if len(parts) == 4:
                        game_time = time(int(parts[:2]), int(parts[2:]))
                except Exception:
                    pass

            stadium = stadium_cell.get_text(strip=True) if stadium_cell else None
            away_starter = starter_cells[0].get_text(strip=True) if len(starter_cells) > 0 else None
            home_starter = starter_cells[1].get_text(strip=True) if len(starter_cells) > 1 else None

            entries.append(
                ScheduleEntry(
                    game_date=game_date,
                    home_team=home_team,
                    away_team=away_team,
                    stadium=stadium,
                    game_time=game_time,
                    home_starter_name=home_starter or None,
                    away_starter_name=away_starter or None,
                    source="statiz",
                    source_url=url,
                )
            )
        except Exception as exc:
            logger.debug("[crawler:statiz] row parse error: %s", exc)
            continue

    logger.info("[crawler:statiz] parsed %d entries for %s", len(entries), game_date)
    return entries


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

async def fetch_today_schedule(game_date: date) -> list[ScheduleEntry]:
    """
    Fetch the KBO schedule for game_date using the fallback chain:
      KBO 공식 → 네이버 스포츠 → 스탯티즈

    Returns the first non-empty list.  If all sources fail or return nothing,
    returns an empty list (never raises).

    Logs which source answered (or "all sources empty").
    """
    async with _make_client() as client:
        # Source 1 — KBO
        try:
            entries = await _fetch_kbo(client, game_date)
            if entries:
                logger.info("[crawler] source=kbo answered with %d entries", len(entries))
                return entries
            logger.info("[crawler] kbo returned 0 entries — trying naver")
        except Exception as exc:
            logger.warning("[crawler] kbo raised unexpectedly: %s — trying naver", exc)

        # Source 2 — Naver (different host than KBO — per-host rate limit
        # is enforced inside each _fetch_* function, no cross-source sleep)
        try:
            entries = await _fetch_naver(client, game_date)
            if entries:
                logger.info("[crawler] source=naver answered with %d entries", len(entries))
                return entries
            logger.info("[crawler] naver returned 0 entries — trying statiz")
        except Exception as exc:
            logger.warning("[crawler] naver raised unexpectedly: %s — trying statiz", exc)

        # Source 3 — Statiz (different host)
        try:
            entries = await _fetch_statiz(client, game_date)
            if entries:
                logger.info("[crawler] source=statiz answered with %d entries", len(entries))
                return entries
            logger.info("[crawler] statiz returned 0 entries")
        except Exception as exc:
            logger.warning("[crawler] statiz raised unexpectedly: %s", exc)

    logger.error(
        "[crawler] ALL sources empty for %s — returning empty list.  "
        "Check network, selectors, or try again later.",
        game_date,
    )
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
    pitcher_ids via match_pitcher_name and writing the matchups row.

    Commits once at the end. Caller should not wrap this in an outer
    transaction — use a fresh session per run.

    Returns counts: {"inserted": n, "updated": n, "skipped": n}.
    skipped covers entries whose fields were identical to the DB row.
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
                    source_url=entry.source_url,
                )
            )
            counts["inserted"] += 1
            logger.info(
                "[crawler:upsert] INSERT %s %s@%s home=%s away=%s",
                entry.game_date, entry.away_team, entry.home_team,
                entry.home_starter_name or "(TBD)",
                entry.away_starter_name or "(TBD)",
            )
            continue

        # --- Update path -----------------------------------------------------
        changed = False

        # stadium / game_time: overwrite if crawler has a value
        if entry.stadium and existing.stadium != entry.stadium:
            existing.stadium = entry.stadium
            changed = True
        if entry.game_time and existing.game_time != entry.game_time:
            existing.game_time = entry.game_time
            changed = True

        # Starters: only fill blanks. Never overwrite confirmed with None.
        # A confirmed starter that disagrees with a new crawl is a legitimate
        # mismatch (late scratch, source flip-flop, wrong name in one source)
        # — keep the DB value but queue for human review per CLAUDE.md §5.
        if entry.home_starter_name and existing.home_starter != entry.home_starter_name:
            if existing.home_starter is None:
                existing.home_starter = entry.home_starter_name
                changed = True
            else:
                logger.warning(
                    "[crawler:upsert] starter mismatch for %s %s (home): db=%s crawl=%s — keeping db",
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
                    "source": entry.source,
                    "source_url": entry.source_url,
                    "queued_at": datetime.now(KST).isoformat(),
                })
        if entry.away_starter_name and existing.away_starter != entry.away_starter_name:
            if existing.away_starter is None:
                existing.away_starter = entry.away_starter_name
                changed = True
            else:
                logger.warning(
                    "[crawler:upsert] starter mismatch for %s %s (away): db=%s crawl=%s — keeping db",
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
                    "source": entry.source,
                    "source_url": entry.source_url,
                    "queued_at": datetime.now(KST).isoformat(),
                })

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
