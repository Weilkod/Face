"""
services/kbo_profile_harvester.py — eager KBO player profile lookup for seed time.

Scope
-----
Given a Korean pitcher name + FACEMETRICS team code, talk to koreabaseball.com's
`/Player/Search.aspx` ASP.NET form and return the player's `kbo_player_id` plus
the profile image URL on the `6ptotvmi5753.edge.naverncp.com` CDN.

This is the **eager** counterpart to `scheduler._resolve_pitcher_id`'s lazy
write-back (A-5, session 10 PR #10): lazy write-back fills `pitcher.kbo_player_id`
over days as the scheduler observes each pitcher in a real game; the harvester
fills it at seed time so brand-new seeded pitchers reach the id-fast-path on
day 1 of their roster.

Fallback / robots / rate-limit policy matches `services/crawler.py`:
  - Reuses `crawler._make_client` / `DEFAULT_HEADERS` / `RATE_LIMIT_S`.
  - Per-call `asyncio.sleep(RATE_LIMIT_S)` before each HTTP request.
  - `crawler._robots_allows` runs for `/Player/Search.aspx` and the detail page
    (neither is under `/ws/`, so they go through the normal robots check).
  - Fails soft: on any HTTP / parse error returns None, logs at warning.

The sync original (`scripts/crawl_pitcher_images.py::kbo_search_player`) is kept
for the personal-use image downloader tool. This module is its async, service-
layer twin — same URLs, same regex, but returns a structured `HarvestResult`
and does not write to disk.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.crawler import (
    DEFAULT_HEADERS,  # noqa: F401  (kept as doc of which headers the client uses)
    GET_HEADER_OVERRIDE,
    RATE_LIMIT_S,
    _make_client,
    _robots_allows,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KBO_HOST = "https://www.koreabaseball.com"
KBO_SEARCH_URL = f"{KBO_HOST}/Player/Search.aspx"

# ASP.NET control path for the search form. Empirically stable on KBO's
# Player/Search.aspx as of 2026-04-15 — same prefix used by the existing
# sync `scripts/crawl_pitcher_images.kbo_search_player` implementation.
_ASPNET_PREFIX = "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$"

# Profile image URLs look like
#   //6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2026/77250.jpg
# with optional https: prefix. Three size variants (middle/big/small) exist —
# we don't care which one the detail page embeds.
_KBO_PROFILE_IMG_RE = re.compile(
    r"(?:https?:)?//6ptotvmi5753\.edge\.naverncp\.com/KBO_IMAGE/person/"
    r"(?:middle|big|small)/\d+/\d+\.(?:jpg|jpeg|png|webp)",
    re.IGNORECASE,
)

# playerId query param on PitcherDetail / Retire links.
_PLAYER_ID_RE = re.compile(r"[?&]playerId=(\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarvestResult:
    """Outcome of a successful `harvest_profile` call.

    `profile_photo_url` is optional because the detail page occasionally
    uses a placeholder image that doesn't match the CDN regex — we still
    return the `kbo_player_id` in that case so lazy write-back benefits.
    """

    kbo_player_id: int
    profile_photo_url: Optional[str] = None


async def harvest_profile(
    client: httpx.AsyncClient,
    name: str,
    team: str,
) -> Optional[HarvestResult]:
    """
    Look up a pitcher on koreabaseball.com by name and return its KBO playerId
    plus profile image URL.

    `team` is accepted for logging context. Disambiguation across multiple
    hits uses link-priority (active pitcher > retired pitcher > other roles),
    mirroring the sync implementation. For the seed_pitchers cohort this is
    sufficient — every seeded name resolves to exactly one active PitcherDetail
    link in practice.

    Returns None on any miss / HTTP error / parse failure. Never raises.
    """
    if not name or not name.strip():
        return None

    try:
        # Step 1 — fetch search page to harvest the ASP.NET hidden form state.
        viewstate = await _fetch_form_state(client)
        if viewstate is None:
            return None

        # Step 2 — POST the search with the player's Korean name.
        html = await _post_search(client, name, viewstate)
        if html is None:
            return None

        # Step 3 — pick the best candidate PitcherDetail link and extract id.
        candidate = _pick_best_candidate(html)
        if candidate is None:
            logger.info(
                "[harvester] miss: name=%s team=%s — no PitcherDetail link in search result",
                name,
                team,
            )
            return None

        detail_href, kbo_player_id = candidate

        # Step 4 — fetch the detail page to pull the profile image URL.
        detail_url = urljoin(KBO_HOST + "/", detail_href)
        detail_html = await _fetch_detail(client, detail_url)

        photo_url: Optional[str] = None
        if detail_html is not None:
            m = _KBO_PROFILE_IMG_RE.search(detail_html)
            if m:
                photo_url = m.group(0)
                if photo_url.startswith("//"):
                    photo_url = "https:" + photo_url

        logger.info(
            "[harvester] hit: name=%s team=%s → kbo_id=%d photo=%s",
            name,
            team,
            kbo_player_id,
            "yes" if photo_url else "no",
        )
        return HarvestResult(
            kbo_player_id=kbo_player_id,
            profile_photo_url=photo_url,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft by contract
        logger.warning(
            "[harvester] unexpected error for name=%s team=%s: %s",
            name,
            team,
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_form_state(client: httpx.AsyncClient) -> Optional[dict[str, str]]:
    """GET the search page and extract __VIEWSTATE / __VIEWSTATEGENERATOR / __EVENTVALIDATION.

    Returns None if robots.txt disallows the URL, or the page is unreachable /
    unparseable.
    """
    if not await _robots_allows(client, KBO_SEARCH_URL):
        logger.info("[harvester] robots.txt disallows %s — skipping", KBO_SEARCH_URL)
        return None

    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.get(KBO_SEARCH_URL, headers=GET_HEADER_OVERRIDE)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("[harvester] search GET failed: %s", exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    fields = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION")
    state: dict[str, str] = {}
    for field in fields:
        el = soup.find("input", {"name": field})
        if el is None:
            logger.warning("[harvester] search page missing hidden field %s", field)
            return None
        state[field] = el.get("value", "")
    return state


async def _post_search(
    client: httpx.AsyncClient,
    name: str,
    state: dict[str, str],
) -> Optional[str]:
    """POST the search form and return the response HTML body."""
    data = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": state["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": state["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": state["__EVENTVALIDATION"],
        f"{_ASPNET_PREFIX}hfPage": "1",
        f"{_ASPNET_PREFIX}ddlTeam": "",
        f"{_ASPNET_PREFIX}ddlPosition": "",
        f"{_ASPNET_PREFIX}txtSearchPlayerName": name,
        f"{_ASPNET_PREFIX}btnSearch": "검색",
    }
    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.post(
            KBO_SEARCH_URL,
            data=data,
            headers={"Referer": KBO_SEARCH_URL},
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("[harvester] search POST failed for name=%s: %s", name, exc)
        return None
    return resp.text


def _pick_best_candidate(html: str) -> Optional[tuple[str, int]]:
    """Parse search result HTML and pick the best `(detail_href, playerId)` pair.

    Priority order (mirrors the sync script):
      1. Active pitcher detail (`PitcherDetail.aspx`)
      2. Retired pitcher page (`Retire/Pitcher`) — KBO sometimes flags foreign
         pitchers whose contract ended as retired.
      3. Any other playerId link except Retire/Hitter (wrong position).

    Returns None if no usable candidate is present.
    """
    soup = BeautifulSoup(html, "html.parser")
    pitcher_hits: list[str] = []
    retire_pitcher_hits: list[str] = []
    other_hits: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "playerId" not in href:
            continue
        if "PitcherDetail" in href:
            pitcher_hits.append(href)
        elif "Retire/Pitcher" in href:
            retire_pitcher_hits.append(href)
        elif "Retire" not in href:
            other_hits.append(href)

    ordered = pitcher_hits + retire_pitcher_hits + other_hits
    if not ordered:
        return None

    # Multiple active pitcher hits → common-name collision. Log so the operator
    # can verify the chosen player, but still return the first since it is
    # what the sync harvester picks today.
    if len(pitcher_hits) > 1:
        logger.warning(
            "[harvester] ambiguous: %d PitcherDetail hits — picking first",
            len(pitcher_hits),
        )

    href = ordered[0]
    m = _PLAYER_ID_RE.search(href)
    if m is None:
        return None
    try:
        return href, int(m.group(1))
    except ValueError:
        return None


async def _fetch_detail(client: httpx.AsyncClient, detail_url: str) -> Optional[str]:
    """GET the PitcherDetail page and return its HTML body, or None on error."""
    if not await _robots_allows(client, detail_url):
        logger.info("[harvester] robots.txt disallows %s — skipping detail", detail_url)
        return None

    try:
        await asyncio.sleep(RATE_LIMIT_S)
        resp = await client.get(detail_url, headers=GET_HEADER_OVERRIDE)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("[harvester] detail GET failed: %s", exc)
        return None
    return resp.text


# ---------------------------------------------------------------------------
# Convenience helper — callers who don't want to manage a client.
# ---------------------------------------------------------------------------


async def harvest_profile_standalone(name: str, team: str) -> Optional[HarvestResult]:
    """Like `harvest_profile` but creates and tears down its own httpx client.

    For one-off callers (e.g. seed scripts processing a single pitcher). Batch
    callers should create a client once and pass it to `harvest_profile` to
    reuse the TCP connection.
    """
    async with _make_client() as client:
        return await harvest_profile(client, name, team)
