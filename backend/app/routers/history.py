"""
GET /api/history?date=YYYY-MM-DD — matchup list for any date.

Unlike /api/today, this endpoint returns all matchups for the date
regardless of is_published status (historical review).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import pitcher_summary
from app.schemas.response import HistoryResponse, MatchupSummary

router = APIRouter()


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="특정 날짜 매치업 히스토리",
    tags=["client"],
)
async def get_history(
    session: Annotated[AsyncSession, Depends(get_session)],
    date_param: Annotated[
        Optional[date],
        Query(alias="date", description="조회 날짜 YYYY-MM-DD, 없으면 오늘"),
    ] = None,
) -> HistoryResponse:
    """Return all matchups for the given date (defaults to today).

    is_published is ignored so historical records are always accessible.
    """
    query_date = date_param or date.today()

    stmt = (
        select(Matchup)
        .where(Matchup.game_date == query_date)
        .order_by(Matchup.matchup_id)
    )
    rows = list((await session.execute(stmt)).scalars().all())

    if not rows:
        return HistoryResponse(date=query_date, matchups=[])

    pitcher_ids = set()
    for m in rows:
        pitcher_ids.add(m.home_pitcher_id)
        pitcher_ids.add(m.away_pitcher_id)

    pitchers: dict[int, Pitcher] = {
        p.pitcher_id: p
        for p in (
            await session.execute(select(Pitcher).where(Pitcher.pitcher_id.in_(pitcher_ids)))
        ).scalars().all()
    }

    summaries: list[MatchupSummary] = []
    for m in rows:
        home = pitchers.get(m.home_pitcher_id)
        away = pitchers.get(m.away_pitcher_id)
        if home is None or away is None:
            continue
        summaries.append(
            MatchupSummary(
                matchup_id=m.matchup_id,
                home_team=m.home_team,
                away_team=m.away_team,
                stadium=m.stadium,
                home_pitcher=pitcher_summary(home),
                away_pitcher=pitcher_summary(away),
                home_total=m.home_total,
                away_total=m.away_total,
                predicted_winner=m.predicted_winner,
                winner_comment=m.winner_comment,
                chemistry_score=m.chemistry_score,
            )
        )

    return HistoryResponse(date=query_date, matchups=summaries)
