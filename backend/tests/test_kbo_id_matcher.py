"""A-5 — KBO playerId matcher + scheduler lazy write-back.

Covers three behaviours introduced in A-5:

1. `match_pitcher_by_kbo_id` returns the owning pitcher_id for a given KBO
   playerId and None when unmatched.
2. `_resolve_pitcher_id` prefers the id lookup over name fuzzy match when
   the daily_schedules row carries a kbo_id that resolves.
3. `_resolve_pitcher_id` falls back to name match when the id is missing
   or unresolved, and on fallback success writes the crawled kbo_id back
   to the pitcher row (lazy learning). Write-back is refused when the
   kbo_id is already claimed by another pitcher.
"""
from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio

from app.db import Base, SessionLocal, engine
from app.models.pitcher import Pitcher
from app.scheduler import _resolve_pitcher_id
from app.services.crawler import match_pitcher_by_kbo_id


GAME_DATE = date(2026, 4, 14)


@pytest_asyncio.fixture(scope="function")
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add_all([
            Pitcher(
                pitcher_id=1, kbo_player_id=77250, name="원태인", team="SAM",
                birth_date=date(2000, 4, 6),
                chinese_zodiac="진", zodiac_sign="양자리", zodiac_element="불",
            ),
            Pitcher(
                pitcher_id=2, kbo_player_id=None, name="곽빈", team="DS",
                birth_date=date(1999, 5, 28),
                chinese_zodiac="묘", zodiac_sign="쌍둥이자리", zodiac_element="바람",
            ),
            Pitcher(
                pitcher_id=3, kbo_player_id=99001, name="네일", team="KIA",
                name_en="James Naile",
                birth_date=date(1993, 2, 2),
                chinese_zodiac="유", zodiac_sign="물병자리", zodiac_element="바람",
            ),
        ])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_match_by_kbo_id_hit(fresh_db):
    async with SessionLocal() as session:
        pid = await match_pitcher_by_kbo_id(session, 77250)
    assert pid == 1


@pytest.mark.asyncio
async def test_match_by_kbo_id_miss_returns_none(fresh_db):
    async with SessionLocal() as session:
        pid = await match_pitcher_by_kbo_id(session, 12345)
    assert pid is None


@pytest.mark.asyncio
async def test_resolve_prefers_kbo_id_over_name(fresh_db):
    """id hit short-circuits — name/team don't need to match at all."""
    async with SessionLocal() as session:
        pid = await _resolve_pitcher_id(
            session,
            kbo_player_id=77250,
            starter_name="completely different name",
            team="SAM",
            gd=GAME_DATE,
        )
    assert pid == 1


@pytest.mark.asyncio
async def test_resolve_fallback_learns_kbo_id(fresh_db):
    """곽빈 has kbo_player_id=None in seed. Scheduler matches by name, then
    writes the crawled kbo_id back to the pitcher row so the next run takes
    the fast path.
    """
    async with SessionLocal() as session:
        pid = await _resolve_pitcher_id(
            session,
            kbo_player_id=88042,
            starter_name="곽빈",
            team="DS",
            gd=GAME_DATE,
        )
        await session.commit()
        pitcher = await session.get(Pitcher, 2)

    assert pid == 2
    assert pitcher is not None and pitcher.kbo_player_id == 88042


@pytest.mark.asyncio
async def test_resolve_skips_write_back_when_pitcher_already_has_kbo_id(fresh_db):
    """원태인 already has kbo_player_id=77250 in seed. If a (hypothetical)
    crawl returned a different id for the same name, scoring should still
    proceed but the existing mapping must NOT be overwritten — that's the
    "never silently clobber" guarantee. In practice this branch fires when
    match_pitcher_by_kbo_id at the top missed (new id), yet the name match
    lands on a pitcher whose slot is already filled.
    """
    async with SessionLocal() as session:
        # Drop 원태인's id match by passing a brand-new id; name match still
        # resolves to pitcher_id=1. Write-back must skip.
        pid = await _resolve_pitcher_id(
            session,
            kbo_player_id=11111,
            starter_name="원태인",
            team="SAM",
            gd=GAME_DATE,
        )
        await session.commit()
        won = await session.get(Pitcher, 1)

    assert pid == 1
    assert won is not None and won.kbo_player_id == 77250  # unchanged
