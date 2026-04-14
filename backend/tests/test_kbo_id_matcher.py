"""A-5 — KBO playerId matcher + scheduler lazy write-back + upsert fill-blank.

Covers the behaviours introduced in A-5:

1. `match_pitcher_by_kbo_id` returns the owning pitcher_id for a given KBO
   playerId, None when unmatched, and None when called with None input.
2. `_resolve_pitcher_id` prefers the id lookup over name fuzzy match when
   the daily_schedules row carries a kbo_id that resolves.
3. `_resolve_pitcher_id` falls back to name match when the id is missing
   or unresolved, and on fallback success writes the crawled kbo_id back
   to the pitcher row (lazy learning). Write-back is skipped when the
   slot is already filled.
4. `upsert_schedule` fill-blank policy for `home/away_starter_kbo_id`: an
   insert persists the crawled ids, and an update fills in a previously
   NULL slot but never overwrites a confirmed id.
"""
from __future__ import annotations

from datetime import date, time

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models.daily_schedule import DailySchedule
from app.models.pitcher import Pitcher
from app.scheduler import _resolve_pitcher_id
from app.schemas.crawler import ScheduleEntry
from app.services.crawler import match_pitcher_by_kbo_id, upsert_schedule


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
async def test_match_by_kbo_id_none_input(fresh_db):
    """Explicit guard: callers may pass Optional[int]; None must return None
    without touching the DB (contract is documented in the Optional[int]
    signature)."""
    async with SessionLocal() as session:
        pid = await match_pitcher_by_kbo_id(session, None)
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
async def test_upsert_schedule_persists_kbo_ids_on_insert(fresh_db):
    """Fresh crawl of a game — `upsert_schedule` must write the crawled
    kbo_ids into the new columns, not drop them silently."""
    entry = ScheduleEntry(
        game_date=GAME_DATE,
        home_team="SAM",
        away_team="DS",
        stadium="대구",
        game_time=time(18, 30),
        home_starter_name="원태인",
        away_starter_name="곽빈",
        home_starter_kbo_id=77250,
        away_starter_kbo_id=88042,
    )
    async with SessionLocal() as session:
        counts = await upsert_schedule(session, [entry])

    assert counts == {"inserted": 1, "updated": 0, "skipped": 0}

    async with SessionLocal() as session:
        row = (await session.execute(select(DailySchedule))).scalar_one()
    assert row.home_starter_kbo_id == 77250
    assert row.away_starter_kbo_id == 88042


@pytest.mark.asyncio
async def test_upsert_schedule_fills_blank_kbo_ids_on_update(fresh_db):
    """First crawl had a TBD away starter (no id). Second crawl supplies the
    id — `upsert_schedule` must fill the previously NULL slot without
    touching the confirmed home id.
    """
    first = ScheduleEntry(
        game_date=GAME_DATE,
        home_team="SAM",
        away_team="DS",
        stadium="대구",
        game_time=time(18, 30),
        home_starter_name="원태인",
        away_starter_name=None,
        home_starter_kbo_id=77250,
        away_starter_kbo_id=None,
    )
    second = first.model_copy(update={
        "away_starter_name": "곽빈",
        "away_starter_kbo_id": 88042,
    })

    async with SessionLocal() as session:
        await upsert_schedule(session, [first])
        counts = await upsert_schedule(session, [second])

    assert counts["updated"] == 1
    assert counts["inserted"] == 0

    async with SessionLocal() as session:
        row = (await session.execute(select(DailySchedule))).scalar_one()
    assert row.home_starter_kbo_id == 77250  # unchanged
    assert row.away_starter_kbo_id == 88042  # filled


@pytest.mark.asyncio
async def test_upsert_schedule_never_overwrites_confirmed_kbo_id(fresh_db):
    """Confirmed kbo_id must not be silently replaced by a later crawl (data
    mismatch — keep DB value, same policy as starter-name fill-blank)."""
    first = ScheduleEntry(
        game_date=GAME_DATE,
        home_team="SAM",
        away_team="DS",
        home_starter_name="원태인",
        away_starter_name="곽빈",
        home_starter_kbo_id=77250,
        away_starter_kbo_id=88042,
    )
    second = first.model_copy(update={
        "home_starter_kbo_id": 99999,  # hypothetical drift — must be ignored
        "away_starter_kbo_id": 88042,
    })

    async with SessionLocal() as session:
        await upsert_schedule(session, [first])
        await upsert_schedule(session, [second])

    async with SessionLocal() as session:
        row = (await session.execute(select(DailySchedule))).scalar_one()
    assert row.home_starter_kbo_id == 77250  # not overwritten
    assert row.away_starter_kbo_id == 88042


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
