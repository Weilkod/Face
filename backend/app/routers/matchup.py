"""
GET /api/matchup/{matchup_id} — full matchup detail with 5-axis scores.

Face scores: (pitcher_id, season=game_date.year)
Fortune scores: (pitcher_id, game_date)
Both default to all-zero if no cached row exists yet.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.daily_schedule import DailySchedule
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import format_game_time, pitcher_summary
from app.schemas.response import (
    AxisBreakdown,
    ChemistryDetail,
    MatchupDetail,
    PitcherScores,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_pitcher_scores(
    face: Optional[FaceScore],
    fortune: Optional[FortuneScore],
) -> PitcherScores:
    """Combine face and fortune scores into the nested AxisBreakdown structure.

    If either source is absent the relevant sub-score is 0 and detail/reading
    is None. Total is the sum of all five axis totals.
    """

    def _axis(
        face_val: int,
        fortune_val: int,
        face_detail: Optional[str],
        fortune_reading: Optional[str],
    ) -> AxisBreakdown:
        return AxisBreakdown(
            face=face_val,
            fortune=fortune_val,
            total=face_val + fortune_val,
            face_detail=face_detail,
            fortune_reading=fortune_reading,
        )

    f_cmd = face.command if face else 0
    f_stf = face.stuff if face else 0
    f_cmp = face.composure if face else 0
    f_dom = face.dominance if face else 0
    f_dst = face.destiny if face else 0

    r_cmd = fortune.command if fortune else 0
    r_stf = fortune.stuff if fortune else 0
    r_cmp = fortune.composure if fortune else 0
    r_dom = fortune.dominance if fortune else 0
    r_dst = fortune.destiny if fortune else 0

    command = _axis(f_cmd, r_cmd, face.command_detail if face else None, fortune.command_reading if fortune else None)
    stuff = _axis(f_stf, r_stf, face.stuff_detail if face else None, fortune.stuff_reading if fortune else None)
    composure = _axis(f_cmp, r_cmp, face.composure_detail if face else None, fortune.composure_reading if fortune else None)
    dominance = _axis(f_dom, r_dom, face.dominance_detail if face else None, fortune.dominance_reading if fortune else None)
    destiny = _axis(f_dst, r_dst, face.destiny_detail if face else None, fortune.destiny_reading if fortune else None)

    total = command.total + stuff.total + composure.total + dominance.total + destiny.total

    return PitcherScores(
        command=command,
        stuff=stuff,
        composure=composure,
        dominance=dominance,
        destiny=destiny,
        total=total,
        lucky_inning=fortune.lucky_inning if fortune else None,
        daily_summary=fortune.daily_summary if fortune else None,
    )


@router.get(
    "/matchup/{matchup_id}",
    response_model=MatchupDetail,
    summary="매치업 상세 — 5개 축 점수 전체",
    tags=["client"],
)
async def get_matchup_detail(
    matchup_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchupDetail:
    """Return full 5-axis breakdown for both pitchers in a matchup."""
    # Load matchup
    matchup = (
        await session.execute(select(Matchup).where(Matchup.matchup_id == matchup_id))
    ).scalar_one_or_none()
    if matchup is None:
        raise HTTPException(status_code=404, detail="Matchup not found")

    season = matchup.game_date.year
    pitcher_ids = [matchup.home_pitcher_id, matchup.away_pitcher_id]

    # Batch-load both pitchers in a single query
    pitchers: dict[int, Pitcher] = {
        p.pitcher_id: p
        for p in (
            await session.execute(select(Pitcher).where(Pitcher.pitcher_id.in_(pitcher_ids)))
        ).scalars().all()
    }
    home_pitcher = pitchers.get(matchup.home_pitcher_id)
    away_pitcher = pitchers.get(matchup.away_pitcher_id)

    if home_pitcher is None or away_pitcher is None:
        raise HTTPException(status_code=404, detail="Pitcher record missing for this matchup")

    # Batch-load face scores for both pitchers in a single query
    face_rows: dict[int, FaceScore] = {
        r.pitcher_id: r
        for r in (
            await session.execute(
                select(FaceScore).where(
                    FaceScore.pitcher_id.in_(pitcher_ids),
                    FaceScore.season == season,
                )
            )
        ).scalars().all()
    }
    home_face = face_rows.get(matchup.home_pitcher_id)
    away_face = face_rows.get(matchup.away_pitcher_id)

    # Batch-load fortune scores for both pitchers in a single query
    fortune_rows: dict[int, FortuneScore] = {
        r.pitcher_id: r
        for r in (
            await session.execute(
                select(FortuneScore).where(
                    FortuneScore.pitcher_id.in_(pitcher_ids),
                    FortuneScore.game_date == matchup.game_date,
                )
            )
        ).scalars().all()
    }
    home_fortune = fortune_rows.get(matchup.home_pitcher_id)
    away_fortune = fortune_rows.get(matchup.away_pitcher_id)

    home_scores = _build_pitcher_scores(home_face, home_fortune)
    away_scores = _build_pitcher_scores(away_face, away_fortune)

    # Load corresponding DailySchedule row to get game_time.
    # Doubleheaders may yield 2 schedule rows for the same (date, home, away) —
    # neither Matchup nor DailySchedule is keyed by game_number, so we can't
    # unambiguously pair them. Pick the earliest game_time deterministically
    # and warn so operators know a doubleheader case was hit.
    schedule_rows = list(
        (
            await session.execute(
                select(DailySchedule)
                .where(
                    DailySchedule.game_date == matchup.game_date,
                    DailySchedule.home_team == matchup.home_team,
                    DailySchedule.away_team == matchup.away_team,
                )
                .order_by(DailySchedule.game_time.asc().nulls_last())
            )
        ).scalars().all()
    )
    if len(schedule_rows) > 1:
        logger.warning(
            "[matchup:%d] doubleheader detected for %s %s@%s — picking earliest game_time",
            matchup.matchup_id, matchup.game_date, matchup.away_team, matchup.home_team,
        )
    schedule = schedule_rows[0] if schedule_rows else None

    # Build chemistry detail — numeric score from DB; text fields populated
    # once a dedicated chemistry_comment column is added to Matchup.
    chemistry = ChemistryDetail(
        zodiac_detail=None,
        element_detail=None,
        chemistry_score=matchup.chemistry_score,
        chemistry_comment=None,
    )

    return MatchupDetail(
        matchup_id=matchup.matchup_id,
        game_date=matchup.game_date,
        home_team=matchup.home_team,
        away_team=matchup.away_team,
        stadium=matchup.stadium,
        game_time=format_game_time(schedule.game_time if schedule else None),
        series_label=None,
        home_pitcher=pitcher_summary(home_pitcher),
        away_pitcher=pitcher_summary(away_pitcher),
        home_scores=home_scores,
        away_scores=away_scores,
        home_total=matchup.home_total,
        away_total=matchup.away_total,
        chemistry=chemistry,
        chemistry_score=matchup.chemistry_score,
        predicted_winner=matchup.predicted_winner,
        winner_comment=matchup.winner_comment,
    )
