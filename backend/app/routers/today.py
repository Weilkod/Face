"""
GET /api/today — today's published KBO matchup list.

Returns only rows where Matchup.is_published == True (flipped by the 11:00
KST publish_matchups job).  FaceScore and FortuneScore are read from the DB
with no Claude API calls; the pipeline pre-populates them before publish.

Sample response:
{
  "game_date": "2026-04-13",
  "matchups": [
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
        "profile_photo": null,
        "total_score": 74,
        "axes": [
          {"axis": "command", "face": 7, "fortune": 6, "total": 13, "winner": "home"},
          ...
        ]
      },
      "away_pitcher": { ... },
      "chemistry_score": 2.5,
      "predicted_winner": "home",
      "winner_comment": "임찬규 근소한 우세 — 경기 흐름이 관건"
    }
  ],
  "disclaimer": "본 콘텐츠는 엔터테인먼트 목적입니다. 베팅 등에 활용하지 마세요."
}
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.routers._helpers import build_matchup_summary
from app.schemas.response import TodayResponse

_KST = ZoneInfo("Asia/Seoul")

router = APIRouter(tags=["public"])


def _today_kst() -> date:
    return datetime.now(_KST).date()


async def _get_pitcher(session: AsyncSession, pitcher_id: int) -> Pitcher | None:
    stmt = select(Pitcher).where(Pitcher.pitcher_id == pitcher_id)
    return (await session.execute(stmt)).scalar_one_or_none()


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


@router.get("/today", response_model=TodayResponse, summary="오늘의 매치업 리스트")
async def get_today(
    session: AsyncSession = Depends(get_session),
) -> TodayResponse:
    """
    Return today's published matchups with per-axis score breakdowns.

    Only rows where is_published=True are returned.  Scores are read purely
    from the DB — this endpoint never triggers a Claude API call.
    """
    today = _today_kst()
    season = today.year

    stmt = select(Matchup).where(
        Matchup.game_date == today,
        Matchup.is_published.is_(True),
    )
    rows: list[Matchup] = list((await session.execute(stmt)).scalars().all())

    summaries = []
    for matchup in rows:
        home = await _get_pitcher(session, matchup.home_pitcher_id)
        away = await _get_pitcher(session, matchup.away_pitcher_id)
        if home is None or away is None:
            continue

        home_face = await _get_face(session, matchup.home_pitcher_id, season)
        away_face = await _get_face(session, matchup.away_pitcher_id, season)
        home_fortune = await _get_fortune(session, matchup.home_pitcher_id, today)
        away_fortune = await _get_fortune(session, matchup.away_pitcher_id, today)

        summaries.append(
            build_matchup_summary(
                matchup, home, away,
                home_face, away_face,
                home_fortune, away_fortune,
            )
        )

    return TodayResponse(game_date=today, matchups=summaries)
