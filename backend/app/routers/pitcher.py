"""
GET /api/pitcher/{pitcher_id} — pitcher profile + 관상 + 오늘 운세.

Returns the pitcher's full profile, their season face scores (2026), and
today's fortune scores (KST date).  No Claude calls — reads DB only.

Sample response:
{
  "pitcher_id": 3,
  "name": "임찬규",
  "name_en": "Lim Chan-gyu",
  "team": "LG",
  "birth_date": "1995-07-08",
  "chinese_zodiac": "돼지",
  "zodiac_sign": "게자리",
  "zodiac_element": "화",
  "blood_type": "A",
  "profile_photo": "https://...kbo.../img/player/3.jpg",
  "face_scores": {
    "command": 7, "stuff": 6, ...
    "overall_impression": "날카로운 눈매..."
  },
  "today_fortune": {
    "command": 6, "stuff": 7, ...
    "daily_summary": "오늘은 제구가...",
    "lucky_inning": 5
  },
  "disclaimer": "본 콘텐츠는 엔터테인먼트 목적입니다."
}
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.pitcher import Pitcher
from app.routers._helpers import _face_detail, _fortune_detail
from app.schemas.response import PitcherProfileResponse

_KST = ZoneInfo("Asia/Seoul")

router = APIRouter(tags=["public"])


def _today_kst() -> date:
    return datetime.now(_KST).date()


@router.get(
    "/pitcher/{pitcher_id}",
    response_model=PitcherProfileResponse,
    summary="투수 프로필 + 관상 + 오늘 운세",
)
async def get_pitcher(
    pitcher_id: int,
    session: AsyncSession = Depends(get_session),
) -> PitcherProfileResponse:
    """
    Return a pitcher's full profile including season face scores and today's
    fortune reading.

    Raises 404 if the pitcher does not exist in the DB.
    """
    stmt = select(Pitcher).where(Pitcher.pitcher_id == pitcher_id)
    pitcher: Pitcher | None = (await session.execute(stmt)).scalar_one_or_none()
    if pitcher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pitcher {pitcher_id} not found",
        )

    today = _today_kst()
    season = today.year

    face_stmt = select(FaceScore).where(
        FaceScore.pitcher_id == pitcher_id,
        FaceScore.season == season,
    )
    face: FaceScore | None = (await session.execute(face_stmt)).scalar_one_or_none()

    fortune_stmt = select(FortuneScore).where(
        FortuneScore.pitcher_id == pitcher_id,
        FortuneScore.game_date == today,
    )
    fortune: FortuneScore | None = (
        await session.execute(fortune_stmt)
    ).scalar_one_or_none()

    return PitcherProfileResponse(
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
        face_scores=_face_detail(face),
        today_fortune=_fortune_detail(fortune),
    )
