"""
GET /api/accuracy — cumulative prediction accuracy statistics.

Only matchups where both predicted_winner and actual_winner are set
contribute to counts.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.matchup import Matchup
from app.schemas.response import AccuracyResponse, PeriodAccuracy

router = APIRouter()


@router.get(
    "/accuracy",
    response_model=AccuracyResponse,
    summary="누적 예측 적중률",
    tags=["client"],
)
async def get_accuracy(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccuracyResponse:
    """Return cumulative and 7-day rolling accuracy."""
    # All matchups where a result has been recorded
    stmt = select(Matchup).where(
        Matchup.actual_winner.isnot(None),
        Matchup.predicted_winner.isnot(None),
    )
    all_rows = list((await session.execute(stmt)).scalars().all())

    total = len(all_rows)
    correct = sum(1 for m in all_rows if m.predicted_winner == m.actual_winner)
    accuracy_rate = round(correct / total, 3) if total else 0.0

    # Recent 7 days
    cutoff = date.today() - timedelta(days=6)  # today inclusive = 7 days
    recent = [m for m in all_rows if m.game_date >= cutoff]
    r_total = len(recent)
    r_correct = sum(1 for m in recent if m.predicted_winner == m.actual_winner)
    r_rate = round(r_correct / r_total, 3) if r_total else 0.0

    return AccuracyResponse(
        total_predictions=total,
        correct_predictions=correct,
        accuracy_rate=accuracy_rate,
        recent_7_days=PeriodAccuracy(
            total=r_total,
            correct=r_correct,
            accuracy_rate=r_rate,
        ),
    )
