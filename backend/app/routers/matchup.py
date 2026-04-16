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
from app.routers._helpers import format_game_time, pitcher_summary, resolve_winner_name
from app.schemas.response import (
    AxisBreakdown,
    ChemistryDetail,
    MatchupDetail,
    PitcherScores,
)
from app.services.chemistry_calculator import calculate_chemistry

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_delta(delta: float) -> str:
    """Pretty-print a chemistry delta as "+2", "-1.5", "+0" — always signed."""
    if delta == 0:
        return "+0"
    return f"{delta:+g}"


# Display expansions for terse calculator labels. Only the zodiac "중립" case is
# expanded to the full phrase from draft.html §428 spec — element labels and
# non-neutral zodiac labels stay as returned by chemistry_calculator.
_ZODIAC_LABEL_DISPLAY: dict[str, str] = {
    "중립": "상충도 상생도 아닌 중립 관계",
}


def _display_zodiac_label(label: str) -> str:
    return _ZODIAC_LABEL_DISPLAY.get(label, label)


def _build_chemistry_detail(
    home_pitcher: Pitcher,
    away_pitcher: Pitcher,
    chemistry_score: float,
) -> ChemistryDetail:
    """Build the chemistry response block with rule-based label text.

    Re-runs ``calculate_chemistry`` to populate ``zodiac_detail`` /
    ``element_detail`` / ``chemistry_comment``. ``chemistry_score`` from the DB
    remains the source of truth for the numeric value — we don't overwrite it
    with ``breakdown.final`` to avoid any drift with the stored score that
    scoring_engine already clamped.

    Falls back to a blank-text ChemistryDetail (numeric score preserved) if the
    pitcher rows are missing zodiac metadata — never raise to the client.
    """
    try:
        breakdown = calculate_chemistry(
            home_pitcher.chinese_zodiac,
            away_pitcher.chinese_zodiac,
            home_pitcher.zodiac_element,
            away_pitcher.zodiac_element,
        )
    except ValueError as e:
        logger.warning(
            "[matchup] chemistry text skipped — %s (home_pid=%s, away_pid=%s)",
            e, home_pitcher.pitcher_id, away_pitcher.pitcher_id,
        )
        return ChemistryDetail(
            zodiac_detail=None,
            element_detail=None,
            chemistry_score=chemistry_score,
            chemistry_comment=None,
        )

    zodiac_sign_delta = _format_delta(breakdown.zodiac_delta)
    element_sign_delta = _format_delta(breakdown.element_delta)

    zodiac_detail = (
        f"{home_pitcher.chinese_zodiac}띠 vs {away_pitcher.chinese_zodiac}띠 — "
        f"{_display_zodiac_label(breakdown.zodiac_label)} ({zodiac_sign_delta})"
    )
    element_detail = (
        f"{home_pitcher.zodiac_sign}({home_pitcher.zodiac_element}) vs "
        f"{away_pitcher.zodiac_sign}({away_pitcher.zodiac_element}) — "
        f"{breakdown.element_label} ({element_sign_delta})"
    )
    chemistry_comment = (
        f"운명력 상성 최종 {breakdown.final:g}점 "
        f"(기본 {breakdown.base:g} + 띠 {zodiac_sign_delta} + 원소 {element_sign_delta})"
    )

    return ChemistryDetail(
        zodiac_detail=zodiac_detail,
        element_detail=element_detail,
        chemistry_score=chemistry_score,
        chemistry_comment=chemistry_comment,
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

    # Build chemistry detail — numeric score stays from DB (scoring_engine has
    # already clamped it). Text fields are derived on-the-fly from the same
    # rule-based module (chemistry_calculator) so they stay in lock-step with
    # the stored score without needing a dedicated DB column. CLAUDE.md §2 —
    # chemistry is rule-based, no AI, so re-deriving here is safe and cheap
    # (pure function + lru_cache on JSON load).
    chemistry = _build_chemistry_detail(home_pitcher, away_pitcher, matchup.chemistry_score)

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
        predicted_winner=resolve_winner_name(matchup.predicted_winner, home_pitcher, away_pitcher),
        winner_comment=matchup.winner_comment,
    )
