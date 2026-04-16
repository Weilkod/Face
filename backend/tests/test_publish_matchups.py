"""C-2 idempotency guard — publish_matchups should only flip is_published=False rows.

Scenario:
  - 3 Matchup rows for a test date: 1 already True, 2 False.
  - First call: returns 2 (only the False rows are updated).
  - DB state after first call: all 3 are True.
  - Second call (idempotency): returns 0.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import DailySchedule, Matchup, Pitcher
from app.scheduler import publish_matchups

GAME_DATE = date(2026, 4, 20)


@pytest_asyncio.fixture(scope="function")
async def db_with_matchups():
    """Drop/create all tables, seed 2 pitchers and 3 matchup rows."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add_all([
            Pitcher(
                pitcher_id=10, name="테스트A", team="LG",
                birth_date=date(1995, 3, 1),
                chinese_zodiac="해", zodiac_sign="물고기자리", zodiac_element="물",
                profile_photo=None,
            ),
            Pitcher(
                pitcher_id=11, name="테스트B", team="KT",
                birth_date=date(1997, 6, 15),
                chinese_zodiac="축", zodiac_sign="쌍둥이자리", zodiac_element="바람",
                profile_photo=None,
            ),
        ])
        # 3 matchup rows: 1 already published, 2 unpublished
        session.add_all([
            Matchup(
                game_date=GAME_DATE,
                home_team="LG", away_team="KT",
                home_pitcher_id=10, away_pitcher_id=11,
                is_published=True,   # already flipped
                chemistry_score=2.0,
                home_total=50, away_total=48,
            ),
            Matchup(
                game_date=GAME_DATE,
                home_team="KT", away_team="LG",
                home_pitcher_id=11, away_pitcher_id=10,
                is_published=False,
                chemistry_score=1.5,
                home_total=45, away_total=47,
            ),
            Matchup(
                game_date=GAME_DATE,
                home_team="LG", away_team="KT",
                home_pitcher_id=10, away_pitcher_id=11,
                is_published=False,
                chemistry_score=3.0,
                home_total=60, away_total=55,
            ),
        ])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _published_count() -> int:
    async with SessionLocal() as session:
        rows = (await session.execute(
            select(Matchup).where(
                Matchup.game_date == GAME_DATE,
                Matchup.is_published.is_(True),
            )
        )).scalars().all()
        return len(rows)


@pytest.mark.asyncio
async def test_publish_matchups_only_flips_unpublished(db_with_matchups):
    """First call must return 2 (only the 2 False rows), leave all 3 as True."""
    flipped = await publish_matchups(game_date=GAME_DATE)
    assert flipped == 2, f"expected 2 flipped, got {flipped}"

    published = await _published_count()
    assert published == 3, f"expected all 3 published after first call, got {published}"


@pytest.mark.asyncio
async def test_publish_matchups_idempotent(db_with_matchups):
    """Second call on already-published rows must return 0 (no wasted writes)."""
    await publish_matchups(game_date=GAME_DATE)  # first call flips the 2 False rows
    second_flipped = await publish_matchups(game_date=GAME_DATE)
    assert second_flipped == 0, f"expected 0 on second call, got {second_flipped}"

    published = await _published_count()
    assert published == 3, f"all 3 should remain published, got {published}"
