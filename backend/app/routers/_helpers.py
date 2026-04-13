"""
Internal helpers shared across routers.

build_pitcher_summary / build_pitcher_detail
    Assemble Pydantic response objects from ORM rows without calling any
    external service. Routers that need to call Claude (admin only) import
    face_analyzer / fortune_generator directly.
"""

from __future__ import annotations

from typing import Optional

from app.models.face_score import FaceScore
from app.services.scoring_engine import AXIS_ORDER
from app.models.fortune_score import FortuneScore
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.schemas.response import (
    AxisScoreSummary,
    FaceScoreDetail,
    FortuneScoreDetail,
    MatchupSummary,
    PitcherDetail,
    PitcherSummary,
)

# ---------------------------------------------------------------------------
# Per-axis assembly helpers
# ---------------------------------------------------------------------------


def _face_dict(fs: Optional[FaceScore]) -> dict[str, int]:
    if fs is None:
        return {ax: 0 for ax in AXIS_ORDER}
    return {ax: int(getattr(fs, ax)) for ax in AXIS_ORDER}


def _fortune_dict(fo: Optional[FortuneScore]) -> dict[str, int]:
    if fo is None:
        return {ax: 0 for ax in AXIS_ORDER}
    return {ax: int(getattr(fo, ax)) for ax in AXIS_ORDER}


def _build_axes(
    face: dict[str, int],
    fortune: dict[str, int],
    chemistry: float,
    *,
    pitcher_side: str,                     # "home" | "away"
    opponent_face: dict[str, int],
    opponent_fortune: dict[str, int],
) -> list[AxisScoreSummary]:
    """
    Build 5 AxisScoreSummary objects for one pitcher.

    chemistry is applied only to the destiny axis (same value for both sides).
    winner is computed by comparing this pitcher's total against the opponent's
    total on each axis.
    """
    axes: list[AxisScoreSummary] = []
    opp_side = "away" if pitcher_side == "home" else "home"

    for ax in AXIS_ORDER:
        f = face[ax]
        fo = fortune[ax]
        chem_contrib = chemistry if ax == "destiny" else 0.0
        total = int(round(f + fo + chem_contrib))

        opp_f = opponent_face[ax]
        opp_fo = opponent_fortune[ax]
        opp_chem = chemistry if ax == "destiny" else 0.0
        opp_total = int(round(opp_f + opp_fo + opp_chem))

        if total > opp_total:
            winner = pitcher_side
        elif total < opp_total:
            winner = opp_side
        else:
            winner = "tie"

        axes.append(
            AxisScoreSummary(
                axis=ax,
                face=f,
                fortune=fo,
                total=total,
                winner=winner,
            )
        )
    return axes


def _pitcher_total(axes: list[AxisScoreSummary]) -> int:
    return sum(a.total for a in axes)


# ---------------------------------------------------------------------------
# FaceScoreDetail / FortuneScoreDetail builders
# ---------------------------------------------------------------------------


def _face_detail(fs: Optional[FaceScore]) -> Optional[FaceScoreDetail]:
    if fs is None:
        return None
    return FaceScoreDetail(
        command=fs.command,
        stuff=fs.stuff,
        composure=fs.composure,
        dominance=fs.dominance,
        destiny=fs.destiny,
        command_detail=fs.command_detail,
        stuff_detail=fs.stuff_detail,
        composure_detail=fs.composure_detail,
        dominance_detail=fs.dominance_detail,
        destiny_detail=fs.destiny_detail,
        overall_impression=fs.overall_impression,
    )


def _fortune_detail(fo: Optional[FortuneScore]) -> Optional[FortuneScoreDetail]:
    if fo is None:
        return None
    return FortuneScoreDetail(
        command=fo.command,
        stuff=fo.stuff,
        composure=fo.composure,
        dominance=fo.dominance,
        destiny=fo.destiny,
        command_reading=fo.command_reading,
        stuff_reading=fo.stuff_reading,
        composure_reading=fo.composure_reading,
        dominance_reading=fo.dominance_reading,
        destiny_reading=fo.destiny_reading,
        daily_summary=fo.daily_summary,
        lucky_inning=fo.lucky_inning,
    )


# ---------------------------------------------------------------------------
# PitcherSummary
# ---------------------------------------------------------------------------


def build_pitcher_summary(
    pitcher: Pitcher,
    face: Optional[FaceScore],
    fortune: Optional[FortuneScore],
    chemistry: float,
    *,
    pitcher_side: str,
    opponent_face: Optional[FaceScore],
    opponent_fortune: Optional[FortuneScore],
) -> PitcherSummary:
    fd = _face_dict(face)
    fo = _fortune_dict(fortune)
    ofd = _face_dict(opponent_face)
    ofo = _fortune_dict(opponent_fortune)

    axes = _build_axes(
        fd, fo, chemistry,
        pitcher_side=pitcher_side,
        opponent_face=ofd,
        opponent_fortune=ofo,
    )
    return PitcherSummary(
        pitcher_id=pitcher.pitcher_id,
        name=pitcher.name,
        team=pitcher.team,
        profile_photo=pitcher.profile_photo,
        total_score=_pitcher_total(axes),
        axes=axes,
    )


# ---------------------------------------------------------------------------
# PitcherDetail
# ---------------------------------------------------------------------------


def build_pitcher_detail(
    pitcher: Pitcher,
    face: Optional[FaceScore],
    fortune: Optional[FortuneScore],
    chemistry: float,
    *,
    pitcher_side: str,
    opponent_face: Optional[FaceScore],
    opponent_fortune: Optional[FortuneScore],
) -> PitcherDetail:
    fd = _face_dict(face)
    fo = _fortune_dict(fortune)
    ofd = _face_dict(opponent_face)
    ofo = _fortune_dict(opponent_fortune)

    axes = _build_axes(
        fd, fo, chemistry,
        pitcher_side=pitcher_side,
        opponent_face=ofd,
        opponent_fortune=ofo,
    )
    return PitcherDetail(
        pitcher_id=pitcher.pitcher_id,
        name=pitcher.name,
        team=pitcher.team,
        birth_date=pitcher.birth_date,
        chinese_zodiac=pitcher.chinese_zodiac,
        zodiac_sign=pitcher.zodiac_sign,
        zodiac_element=pitcher.zodiac_element,
        profile_photo=pitcher.profile_photo,
        face_scores=_face_detail(face),
        fortune_scores=_fortune_detail(fortune),
        total_score=_pitcher_total(axes),
        axes=axes,
    )


# ---------------------------------------------------------------------------
# MatchupSummary (used by today + history)
# ---------------------------------------------------------------------------


def build_matchup_summary(
    matchup: Matchup,
    home: Pitcher,
    away: Pitcher,
    home_face: Optional[FaceScore],
    away_face: Optional[FaceScore],
    home_fortune: Optional[FortuneScore],
    away_fortune: Optional[FortuneScore],
) -> MatchupSummary:
    chemistry = float(matchup.chemistry_score)

    home_summary = build_pitcher_summary(
        home, home_face, home_fortune, chemistry,
        pitcher_side="home",
        opponent_face=away_face,
        opponent_fortune=away_fortune,
    )
    away_summary = build_pitcher_summary(
        away, away_face, away_fortune, chemistry,
        pitcher_side="away",
        opponent_face=home_face,
        opponent_fortune=home_fortune,
    )

    return MatchupSummary(
        matchup_id=matchup.matchup_id,
        game_date=matchup.game_date,
        home_team=matchup.home_team,
        away_team=matchup.away_team,
        stadium=matchup.stadium,
        home_pitcher=home_summary,
        away_pitcher=away_summary,
        chemistry_score=chemistry,
        predicted_winner=matchup.predicted_winner or "tie",
        winner_comment=matchup.winner_comment,
    )
