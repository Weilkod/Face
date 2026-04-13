"""
GET /api/accuracy — cumulative prediction accuracy statistics.

Counts all matchups where actual_winner has been recorded and computes the
fraction whose predicted_winner matches.

Sample response:
{
  "total_predictions": 42,
  "correct_predictions": 27,
  "accuracy_rate": 0.6428571428571429,
  "disclaimer": "본 콘텐츠는 엔터테인먼트 목적입니다."
}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.matchup import Matchup
from app.schemas.response import AccuracyResponse

router = APIRouter(tags=["public"])


@router.get("/accuracy", response_model=AccuracyResponse, summary="누적 예측 적중률")
async def get_accuracy(
    session: AsyncSession = Depends(get_session),
) -> AccuracyResponse:
    """
    Return cumulative prediction accuracy across all matchups that have a
    recorded actual_winner.

    accuracy_rate is 0.0 when no results have been entered yet.
    """
    # Total matchups that have a recorded result
    total_stmt = select(func.count()).where(
        Matchup.actual_winner.is_not(None)
    )
    total: int = (await session.execute(total_stmt)).scalar_one()

    # Correct predictions
    correct_stmt = select(func.count()).where(
        Matchup.actual_winner.is_not(None),
        Matchup.actual_winner == Matchup.predicted_winner,
    )
    correct: int = (await session.execute(correct_stmt)).scalar_one()

    accuracy_rate = correct / total if total > 0 else 0.0

    return AccuracyResponse(
        total_predictions=total,
        correct_predictions=correct,
        accuracy_rate=accuracy_rate,
    )
