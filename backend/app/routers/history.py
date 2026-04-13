"""
GET /api/history?date={YYYY-MM-DD} — past matchup list for any date.

Unlike /api/today this endpoint does NOT filter by is_published; past dates
show all matchups regardless of publish status (they were already served in
their day).

date parameter defaults to today - 1 day (KST) when omitted.

Sample response: same structure as TodayResponse.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import build_matchup_summary
from app.schemas.response import TodayResponse

_KST = ZoneInfo("Asia/Seoul")

router = APIRouter(tags=["public"])


def _today_kst() -> date:
    return datetime.now(_KST).date()


async def _get_pitcher(session: AsyncSession, pitcher_id: int) -> Pitcher | None:
    stmt = select(Pitcher).where(Pitcher.pitcher_id == pitcher_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _get_face(
    session: AsyncSession, pitcher_id: int, season: int
) -> FaceScore | None:
    stmt = select(FaceScore).where(
        FaceScore.pitcher_id == pitcher_id,
        FaceScore.season == season,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _get_fortune(
    session: AsyncSession, pitcher_id: int, game_date: date
) -> FortuneScore | None:
    stmt = select(FortuneScore).where(
        FortuneScore.pitcher_id == pitcher_id,
        FortuneScore.game_date == game_date,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


@router.get("/history", response_model=TodayResponse, summary="과거 날짜 매치업 조회")
async def get_history(
    date: Optional[str] = Query(
        default=None,
        description="조회 날짜 (YYYY-MM-DD). 생략 시 어제(KST).",
        examples=["2026-04-12"],
    ),
    session: AsyncSession = Depends(get_session),
) -> TodayResponse:
    """
    Return all matchups for a past date.

    All rows are returned regardless of is_published (past dates are already
    finalised).  If *date* is omitted the response covers yesterday (KST).
    """
    if date is not None:
        from datetime import date as date_type  # avoid shadowing builtin
        game_date: date_type = date_type.fromisoformat(date)
    else:
        game_date = _today_kst() - timedelta(days=1)

    season = game_date.year

    stmt = select(Matchup).where(Matchup.game_date == game_date)
    rows: list[Matchup] = list((await session.execute(stmt)).scalars().all())

    summaries = []
    for matchup in rows:
        home = await _get_pitcher(session, matchup.home_pitcher_id)
        away = await _get_pitcher(session, matchup.away_pitcher_id)
        if home is None or away is None:
            continue

        home_face = await _get_face(session, matchup.home_pitcher_id, season)
        away_face = await _get_face(session, matchup.away_pitcher_id, season)
        home_fortune = await _get_fortune(session, matchup.home_pitcher_id, game_date)
        away_fortune = await _get_fortune(session, matchup.away_pitcher_id, game_date)

        summaries.append(
            build_matchup_summary(
                matchup, home, away,
                home_face, away_face,
                home_fortune, away_fortune,
            )
        )

    return TodayResponse(game_date=game_date, matchups=summaries)
