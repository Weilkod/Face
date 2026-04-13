"""
GET /api/today — today's published matchup list.

Returns only rows where Matchup.is_published=True for today's date.
Pitchers are eager-loaded to avoid N+1 queries.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import pitcher_summary
from app.schemas.response import MatchupSummary, TodayResponse

router = APIRouter()

_DAY_OF_WEEK_KR = ["월", "화", "수", "목", "금", "토", "일"]


def _day_of_week(d: date) -> str:
    return _DAY_OF_WEEK_KR[d.weekday()]


def _matchup_summary(matchup: Matchup, home: Pitcher, away: Pitcher) -> MatchupSummary:
    return MatchupSummary(
        matchup_id=matchup.matchup_id,
        home_team=matchup.home_team,
        away_team=matchup.away_team,
        stadium=matchup.stadium,
        home_pitcher=pitcher_summary(home),
        away_pitcher=pitcher_summary(away),
        home_total=matchup.home_total,
        away_total=matchup.away_total,
        predicted_winner=matchup.predicted_winner,
        winner_comment=matchup.winner_comment,
        chemistry_score=matchup.chemistry_score,
    )


@router.get(
    "/today",
    response_model=TodayResponse,
    summary="오늘 매치업 리스트 (published only)",
    tags=["client"],
)
async def get_today(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TodayResponse:
    """Return today's published matchups with embedded pitcher summaries."""
    today = date.today()

    stmt = (
        select(Matchup)
        .where(Matchup.game_date == today, Matchup.is_published.is_(True))
        .order_by(Matchup.matchup_id)
    )
    rows = list((await session.execute(stmt)).scalars().all())

    if not rows:
        return TodayResponse(date=today, day_of_week=_day_of_week(today), matchups=[])

    # Collect all referenced pitcher_ids and batch-load them
    pitcher_ids = set()
    for m in rows:
        pitcher_ids.add(m.home_pitcher_id)
        pitcher_ids.add(m.away_pitcher_id)

    pitcher_stmt = select(Pitcher).where(Pitcher.pitcher_id.in_(pitcher_ids))
    pitchers: dict[int, Pitcher] = {
        p.pitcher_id: p
        for p in (await session.execute(pitcher_stmt)).scalars().all()
    }

    summaries: list[MatchupSummary] = []
    for m in rows:
        home = pitchers.get(m.home_pitcher_id)
        away = pitchers.get(m.away_pitcher_id)
        if home is None or away is None:
            # Skip matchups with unresolvable pitchers
            continue
        summaries.append(_matchup_summary(m, home, away))

    return TodayResponse(date=today, day_of_week=_day_of_week(today), matchups=summaries)
