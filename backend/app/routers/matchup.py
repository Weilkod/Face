"""
GET /api/matchup/{matchup_id} — full matchup detail.

Returns a MatchupDetailResponse with both pitchers' complete face + fortune
score objects (all commentary text included) plus the 5-axis breakdown.

Sample response:
{
  "matchup_id": 1,
  "game_date": "2026-04-13",
  "home_team": "LG",
  "away_team": "KT",
  "stadium": "잠실",
  "home_pitcher": {
    "pitcher_id": 3,
    "name": "임찬규",
    "team": "LG",
    "birth_date": "1995-07-08",
    "chinese_zodiac": "돼지",
    "zodiac_sign": "게자리",
    "zodiac_element": "화",
    "profile_photo": null,
    "face_scores": {
      "command": 7, "stuff": 6, "composure": 8, "dominance": 7, "destiny": 5,
      "command_detail": "눈매가 날카로워...",
      ...
    },
    "fortune_scores": {
      "command": 6, "stuff": 7, "composure": 5, "dominance": 8, "destiny": 6,
      "command_reading": "오늘은 제구가 잘 잡힐 날...",
      ...
    },
    "total_score": 74,
    "axes": [...]
  },
  "away_pitcher": { ... },
  "chemistry_score": 2.5,
  "predicted_winner": "home",
  "winner_comment": "임찬규 근소한 우세 — 경기 흐름이 관건",
  "actual_winner": null,
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
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import build_pitcher_detail
from app.schemas.response import MatchupDetailResponse

_KST = ZoneInfo("Asia/Seoul")

router = APIRouter(tags=["public"])


def _today_kst() -> date:
    return datetime.now(_KST).date()


async def _require_pitcher(session: AsyncSession, pitcher_id: int) -> Pitcher:
    stmt = select(Pitcher).where(Pitcher.pitcher_id == pitcher_id)
    pitcher = (await session.execute(stmt)).scalar_one_or_none()
    if pitcher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pitcher {pitcher_id} not found",
        )
    return pitcher


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


@router.get(
    "/matchup/{matchup_id}",
    response_model=MatchupDetailResponse,
    summary="매치업 상세 조회",
)
async def get_matchup(
    matchup_id: int,
    session: AsyncSession = Depends(get_session),
) -> MatchupDetailResponse:
    """
    Return the full detail for a single matchup including all face/fortune
    commentary text for both pitchers.

    Raises 404 if the matchup_id does not exist.
    """
    stmt = select(Matchup).where(Matchup.matchup_id == matchup_id)
    matchup: Matchup | None = (await session.execute(stmt)).scalar_one_or_none()
    if matchup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Matchup {matchup_id} not found",
        )

    game_date = matchup.game_date
    season = game_date.year
    chemistry = float(matchup.chemistry_score)

    home = await _require_pitcher(session, matchup.home_pitcher_id)
    away = await _require_pitcher(session, matchup.away_pitcher_id)

    home_face = await _get_face(session, matchup.home_pitcher_id, season)
    away_face = await _get_face(session, matchup.away_pitcher_id, season)
    home_fortune = await _get_fortune(session, matchup.home_pitcher_id, game_date)
    away_fortune = await _get_fortune(session, matchup.away_pitcher_id, game_date)

    home_detail = build_pitcher_detail(
        home, home_face, home_fortune, chemistry,
        pitcher_side="home",
        opponent_face=away_face,
        opponent_fortune=away_fortune,
    )
    away_detail = build_pitcher_detail(
        away, away_face, away_fortune, chemistry,
        pitcher_side="away",
        opponent_face=home_face,
        opponent_fortune=home_fortune,
    )

    return MatchupDetailResponse(
        matchup_id=matchup.matchup_id,
        game_date=game_date,
        home_team=matchup.home_team,
        away_team=matchup.away_team,
        stadium=matchup.stadium,
        home_pitcher=home_detail,
        away_pitcher=away_detail,
        chemistry_score=chemistry,
        predicted_winner=matchup.predicted_winner or "tie",
        winner_comment=matchup.winner_comment,
        actual_winner=matchup.actual_winner,
    )
