"""
GET /api/pitcher/{pitcher_id} — pitcher profile + season face scores + today's fortune.

face_scores: queried by (pitcher_id, season=current year) — None if absent.
today_fortune: queried by (pitcher_id, game_date=today) — None if absent.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.pitcher import Pitcher
from app.schemas.response import FaceScoreDetail, FortuneScoreDetail, PitcherDetail

router = APIRouter()


@router.get(
    "/pitcher/{pitcher_id}",
    response_model=PitcherDetail,
    summary="투수 프로필 + 관상 점수 + 오늘 운세",
    tags=["client"],
)
async def get_pitcher(
    pitcher_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PitcherDetail:
    """Return full pitcher profile with current-season face scores and today's fortune."""
    pitcher = (
        await session.execute(select(Pitcher).where(Pitcher.pitcher_id == pitcher_id))
    ).scalar_one_or_none()
    if pitcher is None:
        raise HTTPException(status_code=404, detail="Pitcher not found")

    today = date.today()
    season = today.year

    # Face scores (season-fixed)
    face_row = (
        await session.execute(
            select(FaceScore).where(
                FaceScore.pitcher_id == pitcher_id,
                FaceScore.season == season,
            )
        )
    ).scalar_one_or_none()

    face_detail: FaceScoreDetail | None = None
    if face_row is not None:
        face_detail = FaceScoreDetail(
            season=face_row.season,
            command=face_row.command,
            stuff=face_row.stuff,
            composure=face_row.composure,
            dominance=face_row.dominance,
            destiny=face_row.destiny,
            command_detail=face_row.command_detail,
            stuff_detail=face_row.stuff_detail,
            composure_detail=face_row.composure_detail,
            dominance_detail=face_row.dominance_detail,
            destiny_detail=face_row.destiny_detail,
            overall_impression=face_row.overall_impression,
            analyzed_at=face_row.analyzed_at,
        )

    # Fortune scores (daily)
    fortune_row = (
        await session.execute(
            select(FortuneScore).where(
                FortuneScore.pitcher_id == pitcher_id,
                FortuneScore.game_date == today,
            )
        )
    ).scalar_one_or_none()

    fortune_detail: FortuneScoreDetail | None = None
    if fortune_row is not None:
        fortune_detail = FortuneScoreDetail(
            game_date=fortune_row.game_date,
            command=fortune_row.command,
            stuff=fortune_row.stuff,
            composure=fortune_row.composure,
            dominance=fortune_row.dominance,
            destiny=fortune_row.destiny,
            command_reading=fortune_row.command_reading,
            stuff_reading=fortune_row.stuff_reading,
            composure_reading=fortune_row.composure_reading,
            dominance_reading=fortune_row.dominance_reading,
            destiny_reading=fortune_row.destiny_reading,
            daily_summary=fortune_row.daily_summary,
            lucky_inning=fortune_row.lucky_inning,
        )

    return PitcherDetail(
        pitcher_id=pitcher.pitcher_id,
        name=pitcher.name,
        name_en=pitcher.name_en,
        team=pitcher.team,
        birth_date=pitcher.birth_date,
        chinese_zodiac=pitcher.chinese_zodiac,
        zodiac_sign=pitcher.zodiac_sign,
        zodiac_element=pitcher.zodiac_element,
        blood_type=pitcher.blood_type,
        profile_photo=pitcher.profile_photo,
        face_scores=face_detail,
        today_fortune=fortune_detail,
    )
