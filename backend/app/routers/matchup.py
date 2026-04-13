"""
GET /api/matchup/{matchup_id} — full matchup detail with 5-axis scores.

Face scores: (pitcher_id, season=game_date.year)
Fortune scores: (pitcher_id, game_date)
Both default to all-zero if no cached row exists yet.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.schemas.response import (
    AxisBreakdown,
    ChemistryDetail,
    MatchupDetail,
    PitcherScores,
    PitcherSummary,
)

router = APIRouter()


def _pitcher_summary(pitcher: Pitcher) -> PitcherSummary:
    return PitcherSummary(
        pitcher_id=pitcher.pitcher_id,
        name=pitcher.name,
        name_en=pitcher.name_en,
        team=pitcher.team,
        chinese_zodiac=pitcher.chinese_zodiac,
        zodiac_sign=pitcher.zodiac_sign,
        zodiac_element=pitcher.zodiac_element,
        profile_photo=pitcher.profile_photo,
    )


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

    # Load both pitchers
    home_pitcher = (
        await session.execute(select(Pitcher).where(Pitcher.pitcher_id == matchup.home_pitcher_id))
    ).scalar_one_or_none()
    away_pitcher = (
        await session.execute(select(Pitcher).where(Pitcher.pitcher_id == matchup.away_pitcher_id))
    ).scalar_one_or_none()

    if home_pitcher is None or away_pitcher is None:
        raise HTTPException(status_code=404, detail="Pitcher record missing for this matchup")

    # Load face scores
    home_face = (
        await session.execute(
            select(FaceScore).where(
                FaceScore.pitcher_id == matchup.home_pitcher_id,
                FaceScore.season == season,
            )
        )
    ).scalar_one_or_none()
    away_face = (
        await session.execute(
            select(FaceScore).where(
                FaceScore.pitcher_id == matchup.away_pitcher_id,
                FaceScore.season == season,
            )
        )
    ).scalar_one_or_none()

    # Load fortune scores
    home_fortune = (
        await session.execute(
            select(FortuneScore).where(
                FortuneScore.pitcher_id == matchup.home_pitcher_id,
                FortuneScore.game_date == matchup.game_date,
            )
        )
    ).scalar_one_or_none()
    away_fortune = (
        await session.execute(
            select(FortuneScore).where(
                FortuneScore.pitcher_id == matchup.away_pitcher_id,
                FortuneScore.game_date == matchup.game_date,
            )
        )
    ).scalar_one_or_none()

    home_scores = _build_pitcher_scores(home_face, home_fortune)
    away_scores = _build_pitcher_scores(away_face, away_fortune)

    # Build chemistry commentary — textual only, the numeric score is stored
    chemistry = ChemistryDetail(
        zodiac_detail=None,
        element_detail=None,
        chemistry_score=matchup.chemistry_score,
        chemistry_comment=matchup.winner_comment,
    )

    return MatchupDetail(
        matchup_id=matchup.matchup_id,
        game_date=matchup.game_date,
        home_team=matchup.home_team,
        away_team=matchup.away_team,
        stadium=matchup.stadium,
        home_pitcher=_pitcher_summary(home_pitcher),
        away_pitcher=_pitcher_summary(away_pitcher),
        home_scores=home_scores,
        away_scores=away_scores,
        chemistry=chemistry,
        predicted_winner=matchup.predicted_winner,
        winner_comment=matchup.winner_comment,
    )
