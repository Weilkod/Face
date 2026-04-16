"""
GET /api/history?date=YYYY-MM-DD — matchup list for any date.

Unlike /api/today, this endpoint returns all matchups for the date
regardless of is_published status (historical review).
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.daily_schedule import DailySchedule
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import format_game_time, pitcher_summary, resolve_winner_name
from app.schemas.response import HistoryMatchup, HistoryResponse

logger = logging.getLogger(__name__)

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

    # Batch-load DailySchedule rows for game_time lookup, grouped by
    # (home_team, away_team). Doubleheaders produce 2 rows for the same key;
    # neither table is keyed by game_number so we can't unambiguously pair
    # them to matchups. Walk the group in game_time order as a FIFO queue so
    # every matchup still gets a distinct schedule when a doubleheader exists,
    # and warn so operators know the deterministic-but-imprecise pairing was
    # used.
    schedule_groups: dict[tuple[str, str], deque[DailySchedule]] = defaultdict(deque)
    for s in (
        await session.execute(
            select(DailySchedule)
            .where(DailySchedule.game_date == query_date)
            .order_by(DailySchedule.game_time.asc().nulls_last())
        )
    ).scalars().all():
        schedule_groups[(s.home_team, s.away_team)].append(s)

    for key, group in schedule_groups.items():
        if len(group) > 1:
            logger.warning(
                "[history:%s] doubleheader detected for %s@%s (%d schedule rows) — pairing by game_time order",
                query_date, key[1], key[0], len(group),
            )

    history_matchups: list[HistoryMatchup] = []
    for m in rows:
        home = pitchers.get(m.home_pitcher_id)
        away = pitchers.get(m.away_pitcher_id)
        if home is None or away is None:
            continue

        # Pop one schedule per matchup so doubleheader rows get distinct times.
        # If the queue is empty (schedule missing or already consumed), fall
        # back to None — game_time is optional.
        group = schedule_groups.get((m.home_team, m.away_team))
        schedule = group.popleft() if group else None

        # prediction_correct: None if either side is missing
        prediction_correct: Optional[bool] = None
        if m.actual_winner is not None and m.predicted_winner is not None:
            prediction_correct = m.predicted_winner == m.actual_winner

        history_matchups.append(
            HistoryMatchup(
                matchup_id=m.matchup_id,
                home_team=m.home_team,
                away_team=m.away_team,
                stadium=m.stadium,
                home_pitcher=pitcher_summary(home),
                away_pitcher=pitcher_summary(away),
                home_total=m.home_total,
                away_total=m.away_total,
                predicted_winner=resolve_winner_name(m.predicted_winner, home, away),
                winner_comment=m.winner_comment,
                chemistry_score=m.chemistry_score,
                game_time=format_game_time(schedule.game_time if schedule else None),
                series_label=None,
                game_date=m.game_date,
                actual_winner=resolve_winner_name(m.actual_winner, home, away),
                prediction_correct=prediction_correct,
            )
        )

    return HistoryResponse(date=query_date, matchups=history_matchups)
