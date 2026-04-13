"""
Admin endpoints — trigger the daily pipeline manually.

These endpoints are the ONLY places in the codebase that initiate Claude API
calls (via the face_analyzer and fortune_generator services).  Public read
routes (/api/today, /api/matchup, etc.) never call Claude.

Endpoints
---------
POST /admin/crawl-schedule
    Trigger the 08:00 KST crawl job immediately.

POST /admin/analyze-face/{pitcher_id}
    Run (or return cached) 관상 analysis for one pitcher.

POST /admin/generate-fortune?date={YYYY-MM-DD}
    Run the full 10:30 KST scoring pipeline for a given date.

POST /admin/calculate-matchups?date={YYYY-MM-DD}
    Alias for generate-fortune — runs analyze_and_score_matchups().

POST /admin/update-result/{matchup_id}
    Record the actual game winner for accuracy tracking.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_session
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.scheduler import analyze_and_score_matchups, fetch_and_upsert_schedule
from app.services.face_analyzer import get_or_create_face_scores
from app.schemas.response import FaceScoreDetail

_KST = ZoneInfo("Asia/Seoul")

router = APIRouter(prefix="/admin", tags=["admin"])


def _today_kst() -> date:
    return datetime.now(_KST).date()


# ---------------------------------------------------------------------------
# POST /admin/crawl-schedule
# ---------------------------------------------------------------------------


@router.post("/crawl-schedule", summary="KBO 일정 크롤링 트리거")
async def crawl_schedule() -> dict[str, Any]:
    """
    Immediately trigger the 08:00 KST crawl job.

    Opens its own DB session (same as the scheduled variant) so it is safe
    to call at any time regardless of the scheduler state.
    """
    result = await fetch_and_upsert_schedule()
    return {"status": "ok", "counts": result}


# ---------------------------------------------------------------------------
# POST /admin/analyze-face/{pitcher_id}
# ---------------------------------------------------------------------------


@router.post(
    "/analyze-face/{pitcher_id}",
    response_model=FaceScoreDetail,
    summary="투수 관상 분석 실행",
)
async def analyze_face(
    pitcher_id: int,
    season: int = Query(default=2026, description="분석 시즌 (기본값 2026)", examples=[2026]),
    session: AsyncSession = Depends(get_session),
) -> FaceScoreDetail:
    """
    Run (or return cached) face analysis for a single pitcher.

    If a FaceScore already exists for (pitcher_id, season) the cached row is
    returned immediately — Claude is NOT called again.

    Raises 404 if the pitcher does not exist.
    """
    stmt = select(Pitcher).where(Pitcher.pitcher_id == pitcher_id)
    pitcher: Pitcher | None = (await session.execute(stmt)).scalar_one_or_none()
    if pitcher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pitcher {pitcher_id} not found",
        )

    face_score = await get_or_create_face_scores(session, pitcher, season=season)

    return FaceScoreDetail(
        command=face_score.command,
        stuff=face_score.stuff,
        composure=face_score.composure,
        dominance=face_score.dominance,
        destiny=face_score.destiny,
        command_detail=face_score.command_detail,
        stuff_detail=face_score.stuff_detail,
        composure_detail=face_score.composure_detail,
        dominance_detail=face_score.dominance_detail,
        destiny_detail=face_score.destiny_detail,
        overall_impression=face_score.overall_impression,
    )


# ---------------------------------------------------------------------------
# POST /admin/generate-fortune?date=
# ---------------------------------------------------------------------------


@router.post("/generate-fortune", summary="특정 날짜 운세 + 매치업 점수 생성")
async def generate_fortune(
    date: Optional[str] = Query(
        default=None,
        description="대상 날짜 (YYYY-MM-DD). 생략 시 오늘(KST).",
        examples=["2026-04-13"],
    ),
) -> dict[str, Any]:
    """
    Run the full 10:30 KST pipeline (face + fortune + scoring) for a given date.

    This is equivalent to what the APScheduler fires at 10:30 KST.  Existing
    cached rows are not regenerated (the services are idempotent).
    """
    if date is not None:
        from datetime import date as date_type
        game_date: date_type = date_type.fromisoformat(date)
    else:
        game_date = _today_kst()

    counts = await analyze_and_score_matchups(game_date)
    return {"status": "ok", "game_date": game_date.isoformat(), "counts": counts}


# ---------------------------------------------------------------------------
# POST /admin/calculate-matchups?date=  (alias)
# ---------------------------------------------------------------------------


@router.post("/calculate-matchups", summary="매치업 점수 계산 트리거 (generate-fortune 별칭)")
async def calculate_matchups(
    date: Optional[str] = Query(
        default=None,
        description="대상 날짜 (YYYY-MM-DD). 생략 시 오늘(KST).",
        examples=["2026-04-13"],
    ),
) -> dict[str, Any]:
    """Alias for /admin/generate-fortune — runs the same pipeline."""
    if date is not None:
        from datetime import date as date_type
        game_date: date_type = date_type.fromisoformat(date)
    else:
        game_date = _today_kst()

    counts = await analyze_and_score_matchups(game_date)
    return {"status": "ok", "game_date": game_date.isoformat(), "counts": counts}


# ---------------------------------------------------------------------------
# POST /admin/update-result/{matchup_id}
# ---------------------------------------------------------------------------


@router.post("/update-result/{matchup_id}", summary="실제 경기 결과 입력")
async def update_result(
    matchup_id: int,
    actual_winner: str = Body(
        ...,
        embed=True,
        description="실제 승리 팀 ('home' | 'away' | 'tie')",
        examples=["home"],
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Record the actual game winner for a matchup row.

    This flips actual_winner which is then used by /api/accuracy to compute
    cumulative prediction accuracy.  Accepted values: 'home', 'away', 'tie'.

    Raises 404 if the matchup_id does not exist.
    """
    valid = {"home", "away", "tie"}
    if actual_winner not in valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"actual_winner must be one of {valid}",
        )

    stmt = select(Matchup).where(Matchup.matchup_id == matchup_id)
    matchup: Matchup | None = (await session.execute(stmt)).scalar_one_or_none()
    if matchup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Matchup {matchup_id} not found",
        )

    matchup.actual_winner = actual_winner
    await session.commit()

    return {
        "status": "ok",
        "matchup_id": matchup_id,
        "actual_winner": actual_winner,
        "predicted_winner": matchup.predicted_winner,
        "correct": actual_winner == matchup.predicted_winner,
    }
