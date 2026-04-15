"""C-2 — publish_matchups 는 이미 published 된 행을 재건드리면 안 된다.

이전 버그:
    `select(Matchup).where(Matchup.game_date == gd)` 만 있어서 11:00 KST 잡이
    재실행되면 `is_published=True` 행도 다시 True 로 덮어쓰고 있었다. 이 때문에
    리턴 카운트가 실제로 "이번에 flip 된 행 수" 가 아니라 "그 날의 전체 행 수" 가
    되는 의미론적 버그 + 다운스트림 publish-side-effect (캐시 무효화, 프론트엔드
    revalidation) 가 중복으로 발생할 가능성이 있다.

수정:
    `Matchup.is_published.is_(False)` 필터를 추가해 unpublished 행만 flip 한다.

이 테스트:
    같은 game_date 에 published=True 1건 + False 1건 을 시드하고
    publish_matchups 를 호출한 다음, 반환값이 1 이고 True 행은 손대지 않고
    False 행만 True 로 flip 되었는지 확인한다.
"""
from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import DailySchedule, Matchup, Pitcher  # noqa: F401 — ensure all tables created
from app.scheduler import publish_matchups


GAME_DATE = date(2026, 4, 14)


@pytest_asyncio.fixture(scope="function")
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add_all([
            Pitcher(
                pitcher_id=1, name="원태인", team="SAM",
                birth_date=date(2000, 4, 6),
                chinese_zodiac="진", zodiac_sign="양자리", zodiac_element="불",
                profile_photo="https://example.com/face1.jpg",
            ),
            Pitcher(
                pitcher_id=2, name="곽빈", team="DS",
                birth_date=date(1999, 5, 28),
                chinese_zodiac="묘", zodiac_sign="쌍둥이자리", zodiac_element="바람",
                profile_photo="https://example.com/face2.jpg",
            ),
            Pitcher(
                pitcher_id=3, name="안우진", team="KW",
                birth_date=date(1999, 8, 30),
                chinese_zodiac="묘", zodiac_sign="처녀자리", zodiac_element="흙",
                profile_photo="https://example.com/face3.jpg",
            ),
            Pitcher(
                pitcher_id=4, name="문동주", team="HH",
                birth_date=date(2003, 12, 23),
                chinese_zodiac="미", zodiac_sign="염소자리", zodiac_element="흙",
                profile_photo="https://example.com/face4.jpg",
            ),
        ])
        # 이미 published 된 매치업 (rerun 시 건드리면 안 됨)
        session.add(Matchup(
            game_date=GAME_DATE,
            home_team="SAM", away_team="DS",
            stadium="대구",
            home_pitcher_id=1, away_pitcher_id=2,
            chemistry_score=2.5,
            home_total=78, away_total=72,
            predicted_winner="SAM",
            winner_comment="previous run",
            is_published=True,
        ))
        # 아직 unpublished 매치업 (이번에 flip 되어야 함)
        session.add(Matchup(
            game_date=GAME_DATE,
            home_team="KW", away_team="HH",
            stadium="고척",
            home_pitcher_id=3, away_pitcher_id=4,
            chemistry_score=1.0,
            home_total=80, away_total=70,
            predicted_winner="KW",
            winner_comment="fresh run",
            is_published=False,
        ))
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_publish_only_flips_unpublished(fresh_db):
    """published=True 행은 건드리지 말고, False 행만 flip 해야 한다."""
    flipped = await publish_matchups(game_date=GAME_DATE)

    assert flipped == 1, (
        f"publish_matchups 가 unpublished 1 건만 flip 해야 함 (이미 published 행 무시), 실제={flipped}"
    )

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Matchup).where(Matchup.game_date == GAME_DATE).order_by(Matchup.home_team)
            )
        ).scalars().all()

    # 전부 최종적으로 published 상태여야 한다
    assert all(r.is_published for r in rows), "모든 매치업이 published 상태여야 함"
    assert len(rows) == 2, f"매치업 2건이어야 함, 실제={len(rows)}"

    # 이전에 published 된 행의 metadata 는 그대로여야 한다 (rerun 으로 덮어쓰지 않음)
    by_home = {r.home_team: r for r in rows}
    assert by_home["SAM"].winner_comment == "previous run", (
        "이미 published 된 행의 winner_comment 가 그대로 유지되어야 함"
    )
    assert by_home["KW"].winner_comment == "fresh run"
