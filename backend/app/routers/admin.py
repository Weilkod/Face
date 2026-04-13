"""
Admin API endpoints for the FACEMETRICS pipeline.

All routes are prefixed /admin and are not authenticated in dev.
They directly invoke scheduler-level functions or service functions.

POST /admin/crawl-schedule?date=YYYY-MM-DD
POST /admin/analyze-face/{pitcher_id}
POST /admin/generate-fortune?date=YYYY-MM-DD
POST /admin/calculate-matchups?date=YYYY-MM-DD
POST /admin/update-result/{matchup_id}
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models.daily_schedule import DailySchedule
from app.models.face_score import FaceScore
from app.models.fortune_score import FortuneScore
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.scheduler import (
    analyze_and_score_matchups,
    fetch_and_upsert_schedule,
)
from app.schemas.response import (
    AdminAnalyzeFaceResult,
    AdminFortuneResult,
    AdminMatchupResult,
    AdminScheduleResult,
    UpdateResultRequest,
    UpdateResultResponse,
)
from app.services.face_analyzer import get_or_create_face_scores
from app.services.fortune_generator import get_or_create_fortune_scores

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# ---------------------------------------------------------------------------
# POST /admin/crawl-schedule
# ---------------------------------------------------------------------------


@router.post(
    "/crawl-schedule",
    response_model=AdminScheduleResult,
    summary="KBO 일정 크롤링 트리거",
)
async def crawl_schedule(
    date_param: Annotated[
        Optional[date],
        Query(alias="date", description="크롤링 날짜 YYYY-MM-DD, 없으면 오늘"),
    ] = None,
) -> AdminScheduleResult:
    """Trigger the schedule crawl for the given date (defaults to today).

    Calls the same function as the 08:00 KST scheduler job.
    """
    target_date = date_param or date.today()
    try:
        counts = await fetch_and_upsert_schedule(game_date=target_date)
    except Exception as exc:
        logger.exception("[admin:crawl-schedule] failed for %s: %s", target_date, exc)
        raise HTTPException(status_code=502, detail=f"Crawl failed: {exc}") from exc

    return AdminScheduleResult(
        date=target_date,
        inserted=counts.get("inserted", 0),
        updated=counts.get("updated", 0),
        skipped=counts.get("skipped", 0),
    )


# ---------------------------------------------------------------------------
# POST /admin/analyze-face/{pitcher_id}
# ---------------------------------------------------------------------------


@router.post(
    "/analyze-face/{pitcher_id}",
    response_model=AdminAnalyzeFaceResult,
    summary="관상 분석 수동 트리거 (단일 투수)",
)
async def analyze_face(
    pitcher_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminAnalyzeFaceResult:
    """Run (or return cached) face analysis for a single pitcher for the current season.

    Returns HTTP 400 when ANTHROPIC_API_KEY is not configured — the pipeline
    will fall back to hash scores automatically, but callers that need a
    human-readable error get one here.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="API key not configured: set ANTHROPIC_API_KEY in environment",
        )

    pitcher = (
        await session.execute(select(Pitcher).where(Pitcher.pitcher_id == pitcher_id))
    ).scalar_one_or_none()
    if pitcher is None:
        raise HTTPException(status_code=404, detail="Pitcher not found")

    season = date.today().year
    try:
        face_score = await get_or_create_face_scores(session, pitcher, season=season)
    except Exception as exc:
        logger.exception(
            "[admin:analyze-face] failed for pitcher_id=%d: %s", pitcher_id, exc
        )
        raise HTTPException(
            status_code=502, detail=f"Face analysis failed: {exc}"
        ) from exc

    return AdminAnalyzeFaceResult(
        pitcher_id=pitcher_id,
        season=face_score.season,
        face_score_id=face_score.face_score_id,
        command=face_score.command,
        stuff=face_score.stuff,
        composure=face_score.composure,
        dominance=face_score.dominance,
        destiny=face_score.destiny,
        message="ok",
    )


# ---------------------------------------------------------------------------
# POST /admin/generate-fortune
# ---------------------------------------------------------------------------


@router.post(
    "/generate-fortune",
    response_model=AdminFortuneResult,
    summary="선발투수 운세 일괄 생성",
)
async def generate_fortune(
    session: Annotated[AsyncSession, Depends(get_session)],
    date_param: Annotated[
        Optional[date],
        Query(alias="date", description="운세 생성 날짜 YYYY-MM-DD, 없으면 오늘"),
    ] = None,
) -> AdminFortuneResult:
    """Generate fortune scores for all scheduled starters on the given date.

    If a fortune row already exists for (pitcher_id, game_date) it is returned
    from cache without hitting Claude.  Returns 400 when ANTHROPIC_API_KEY is
    absent (callers that need an explicit error rather than silent hash fallback).
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="API key not configured: set ANTHROPIC_API_KEY in environment",
        )

    target_date = date_param or date.today()

    # Find today's schedule rows that have starters assigned
    stmt = select(DailySchedule).where(DailySchedule.game_date == target_date)
    schedule_rows = list((await session.execute(stmt)).scalars().all())

    generated = 0
    skipped = 0
    failed = 0

    for sched in schedule_rows:
        for starter_name, team in [
            (sched.home_starter, sched.home_team),
            (sched.away_starter, sched.away_team),
        ]:
            if not starter_name:
                skipped += 1
                continue

            # Resolve name → Pitcher row (exact match only here — admin path)
            pitcher = (
                await session.execute(
                    select(Pitcher).where(
                        Pitcher.name == starter_name,
                        Pitcher.team == team,
                    )
                )
            ).scalar_one_or_none()

            if pitcher is None:
                logger.warning(
                    "[admin:generate-fortune] pitcher not found: name=%s team=%s",
                    starter_name,
                    team,
                )
                skipped += 1
                continue

            # Check if already cached
            existing = (
                await session.execute(
                    select(FortuneScore).where(
                        FortuneScore.pitcher_id == pitcher.pitcher_id,
                        FortuneScore.game_date == target_date,
                    )
                )
            ).scalar_one_or_none()

            if existing is not None:
                skipped += 1
                continue

            try:
                await get_or_create_fortune_scores(
                    session,
                    pitcher,
                    target_date,
                    opponent_team=team,
                    stadium=sched.stadium or "미정",
                )
                generated += 1
            except Exception as exc:
                logger.exception(
                    "[admin:generate-fortune] failed for pitcher_id=%d date=%s: %s",
                    pitcher.pitcher_id,
                    target_date,
                    exc,
                )
                failed += 1

    return AdminFortuneResult(
        date=target_date,
        generated=generated,
        skipped=skipped,
        failed=failed,
    )


# ---------------------------------------------------------------------------
# POST /admin/calculate-matchups
# ---------------------------------------------------------------------------


@router.post(
    "/calculate-matchups",
    response_model=AdminMatchupResult,
    summary="매치업 점수 계산 + 승자 판정",
)
async def calculate_matchups(
    date_param: Annotated[
        Optional[date],
        Query(alias="date", description="계산 날짜 YYYY-MM-DD, 없으면 오늘"),
    ] = None,
) -> AdminMatchupResult:
    """Run the full scoring pipeline for the given date.

    This is the same function as the 10:30 KST scheduler job.
    """
    target_date = date_param or date.today()
    try:
        counts = await analyze_and_score_matchups(game_date=target_date)
    except Exception as exc:
        logger.exception(
            "[admin:calculate-matchups] failed for %s: %s", target_date, exc
        )
        raise HTTPException(
            status_code=502, detail=f"Matchup calculation failed: {exc}"
        ) from exc

    return AdminMatchupResult(
        date=target_date,
        scored=counts.get("scored", 0),
        inserted=counts.get("inserted", 0),
        updated=counts.get("updated", 0),
        skipped=counts.get("skipped", 0),
        failed=counts.get("failed", 0),
    )


# ---------------------------------------------------------------------------
# POST /admin/update-result/{matchup_id}
# ---------------------------------------------------------------------------


@router.post(
    "/update-result/{matchup_id}",
    response_model=UpdateResultResponse,
    summary="실제 경기 결과 업데이트",
)
async def update_result(
    matchup_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: Annotated[UpdateResultRequest, Body()],
) -> UpdateResultResponse:
    """Record the actual winner for a matchup to enable accuracy tracking."""
    matchup = (
        await session.execute(
            select(Matchup).where(Matchup.matchup_id == matchup_id)
        )
    ).scalar_one_or_none()
    if matchup is None:
        raise HTTPException(status_code=404, detail="Matchup not found")

    matchup.actual_winner = body.actual_winner
    await session.commit()
    logger.info(
        "[admin:update-result] matchup_id=%d actual_winner=%s",
        matchup_id,
        body.actual_winner,
    )

    return UpdateResultResponse(
        matchup_id=matchup_id,
        actual_winner=body.actual_winner,
        message="updated",
    )
