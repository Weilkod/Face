"""
scoring_engine.py — FACEMETRICS 점수 집계 엔진

README §2 + CLAUDE.md §2 에 정의된 수식을 그대로 구현한다.

Public API:
    AXIS_ORDER                          — 고정 5축 순서 (프론트 레이더 차트와 일치)
    score_matchup(session, home, away, game_date, ...) -> MatchupScore   (async)
    score_matchup_from_raw(home, away, hf, hfo, af, afo, game_date) -> MatchupScore (sync)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pitcher import Pitcher
from app.services.chemistry_calculator import ChemistryBreakdown, chemistry_for_pitchers
from app.services.face_analyzer import get_or_create_face_scores
from app.services.fortune_generator import get_or_create_fortune_scores

# ---------------------------------------------------------------------------
# Fixed axis order — shared by radar chart and all downstream consumers.
# README §4-1 / CLAUDE.md §4: 혜안력 → 결행력 → 평정력 → 상승운 → 운명력
# (display labels; internal keys below stay command/stuff/composure/dominance/destiny)
# ---------------------------------------------------------------------------

AXIS_ORDER: tuple[str, ...] = (
    "command",
    "stuff",
    "composure",
    "dominance",
    "destiny",
)

# ---------------------------------------------------------------------------
# Output surface dataclasses (frozen — treat as value objects)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxisTotal:
    axis: str          # one of AXIS_ORDER
    face: int          # raw face score  0..10
    fortune: int       # raw fortune score 0..10
    chemistry: float   # non-zero only for destiny; symmetric between home/away
    total: float       # face + fortune + chemistry  (max 24 for destiny, 20 others)
    winner_side: str   # "home" | "away" | "tie"


@dataclass(frozen=True)
class PitcherScoreCard:
    pitcher_id: int
    name: str
    team: str
    axes: dict[str, AxisTotal]   # keyed by axis name; iteration order = AXIS_ORDER
    total: float                  # sum of all 5 axis totals


@dataclass(frozen=True)
class MatchupScore:
    game_date: date
    home: PitcherScoreCard
    away: PitcherScoreCard
    chemistry: ChemistryBreakdown   # rule-based, shared
    predicted_winner: str           # "home" | "away" | "tie"
    winner_comment: str             # one-line playful Korean verdict


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_REQUIRED_AXES = set(AXIS_ORDER)


def _validate_score_dict(d: dict[str, Any], label: str) -> None:
    """Raise ValueError if any required axis key is missing."""
    missing = _REQUIRED_AXES - set(d.keys())
    if missing:
        raise ValueError(f"{label} is missing axis keys: {missing}")


def _build_axis_totals(
    face: dict[str, Any],
    fortune: dict[str, Any],
    chem_final: float,
) -> dict[str, AxisTotal]:
    """
    Build the per-axis AxisTotal dict for ONE pitcher.

    chemistry is applied ONLY to destiny and is the SHARED value (same for both sides).
    winner_side is left as "" here — filled in by _assign_winner_sides().
    """
    axes: dict[str, AxisTotal] = {}
    for axis in AXIS_ORDER:
        f = int(face[axis])
        fo = int(fortune[axis])
        chem = chem_final if axis == "destiny" else 0.0
        axes[axis] = AxisTotal(
            axis=axis,
            face=f,
            fortune=fo,
            chemistry=chem,
            total=f + fo + chem,
            winner_side="",   # placeholder — filled below
        )
    return axes


def _assign_winner_sides(
    home_axes: dict[str, AxisTotal],
    away_axes: dict[str, AxisTotal],
) -> tuple[dict[str, AxisTotal], dict[str, AxisTotal]]:
    """Return copies of both axes dicts with winner_side populated."""
    new_home: dict[str, AxisTotal] = {}
    new_away: dict[str, AxisTotal] = {}

    for axis in AXIS_ORDER:
        ht = home_axes[axis].total
        at = away_axes[axis].total
        if ht > at:
            ws_home, ws_away = "home", "home"
        elif at > ht:
            ws_home, ws_away = "away", "away"
        else:
            ws_home, ws_away = "tie", "tie"

        new_home[axis] = AxisTotal(
            axis=axis,
            face=home_axes[axis].face,
            fortune=home_axes[axis].fortune,
            chemistry=home_axes[axis].chemistry,
            total=home_axes[axis].total,
            winner_side=ws_home,
        )
        new_away[axis] = AxisTotal(
            axis=axis,
            face=away_axes[axis].face,
            fortune=away_axes[axis].fortune,
            chemistry=away_axes[axis].chemistry,
            total=away_axes[axis].total,
            winner_side=ws_away,
        )

    return new_home, new_away


def _winner_comment(
    home_pitcher: Any,
    away_pitcher: Any,
    home_total: float,
    away_total: float,
    breakdown: ChemistryBreakdown,
) -> tuple[str, str]:
    """
    Return (predicted_winner, winner_comment).

    predicted_winner: "home" | "away" | "tie"
    winner_comment:   playful one-liner in Korean (rule-based, no AI).
    """
    if home_total > away_total:
        predicted = "home"
        winner_name = home_pitcher.name
    elif away_total > home_total:
        predicted = "away"
        winner_name = away_pitcher.name
    else:
        predicted = "tie"
        winner_name = ""

    if predicted == "tie":
        comment = "완전한 균형 — 하늘도 결정을 못 내린 날"
        return predicted, comment

    gap = abs(home_total - away_total)
    if gap >= 15:
        comment = f"{winner_name} 압도적 우세 — 관상과 운세가 모두 그 편"
    elif gap >= 8:
        comment = f"{winner_name} 우세 — 오늘은 {winner_name} 쪽에 기운이 기운다"
    elif gap >= 3:
        comment = f"{winner_name} 근소한 우세 — 경기 흐름이 관건"
    else:
        chem_label = breakdown.zodiac_label
        comment = f"박빙 매치업 — {chem_label} 상성이 승부를 가른다"

    return predicted, comment


# ---------------------------------------------------------------------------
# Secondary function — sync, no DB, hash-fallback-friendly
# ---------------------------------------------------------------------------


def score_matchup_from_raw(
    home_pitcher: Any,
    away_pitcher: Any,
    home_face: dict[str, Any],
    home_fortune: dict[str, Any],
    away_face: dict[str, Any],
    away_fortune: dict[str, Any],
    game_date: date,
) -> MatchupScore:
    """
    Build a MatchupScore from pre-resolved score dicts (no DB, no async).

    Useful for CLI calibration, tests, and the hash-fallback path.
    The dicts must contain keys for all 5 axes in AXIS_ORDER.
    """
    _validate_score_dict(home_face, "home_face")
    _validate_score_dict(home_fortune, "home_fortune")
    _validate_score_dict(away_face, "away_face")
    _validate_score_dict(away_fortune, "away_fortune")

    breakdown = chemistry_for_pitchers(home_pitcher, away_pitcher)
    chem_final: float = breakdown.final

    # Build per-axis totals (winner_side placeholder)
    home_axes = _build_axis_totals(home_face, home_fortune, chem_final)
    away_axes = _build_axis_totals(away_face, away_fortune, chem_final)

    # Populate winner_side via comparison
    home_axes, away_axes = _assign_winner_sides(home_axes, away_axes)

    home_total = sum(a.total for a in home_axes.values())
    away_total = sum(a.total for a in away_axes.values())

    predicted, comment = _winner_comment(
        home_pitcher, away_pitcher, home_total, away_total, breakdown
    )

    home_card = PitcherScoreCard(
        pitcher_id=home_pitcher.pitcher_id,
        name=home_pitcher.name,
        team=home_pitcher.team,
        axes=home_axes,
        total=home_total,
    )
    away_card = PitcherScoreCard(
        pitcher_id=away_pitcher.pitcher_id,
        name=away_pitcher.name,
        team=away_pitcher.team,
        axes=away_axes,
        total=away_total,
    )

    return MatchupScore(
        game_date=game_date,
        home=home_card,
        away=away_card,
        chemistry=breakdown,
        predicted_winner=predicted,
        winner_comment=comment,
    )


# ---------------------------------------------------------------------------
# Primary async function — resolves/creates DB rows then delegates to _from_raw
# ---------------------------------------------------------------------------


async def score_matchup(
    session: AsyncSession,
    home_pitcher: Pitcher,
    away_pitcher: Pitcher,
    game_date: date,
    *,
    season: int = 2026,
    opponent_team_for_home: str = "",
    opponent_team_for_away: str = "",
    stadium: str = "",
) -> MatchupScore:
    """
    Resolve face + fortune scores from DB (creating via Claude or hash fallback
    if absent), then assemble and return a MatchupScore.

    opponent_team_for_home: the away team name seen by the home pitcher's fortune.
    opponent_team_for_away: the home team name seen by the away pitcher's fortune.
    If either is blank, the opposing pitcher's .team attribute is used as default.
    """
    opp_for_home = opponent_team_for_home or away_pitcher.team
    opp_for_away = opponent_team_for_away or home_pitcher.team

    # Resolve face scores (season-fixed cache)
    home_face_row = await get_or_create_face_scores(session, home_pitcher, season=season)
    away_face_row = await get_or_create_face_scores(session, away_pitcher, season=season)

    # Resolve fortune scores (per game_date cache)
    home_fortune_row = await get_or_create_fortune_scores(
        session, home_pitcher, game_date,
        opponent_team=opp_for_home,
        stadium=stadium,
    )
    away_fortune_row = await get_or_create_fortune_scores(
        session, away_pitcher, game_date,
        opponent_team=opp_for_away,
        stadium=stadium,
    )

    # Project ORM rows to plain dicts for the sync path
    home_face: dict[str, Any] = {ax: getattr(home_face_row, ax) for ax in AXIS_ORDER}
    away_face: dict[str, Any] = {ax: getattr(away_face_row, ax) for ax in AXIS_ORDER}
    home_fortune: dict[str, Any] = {ax: getattr(home_fortune_row, ax) for ax in AXIS_ORDER}
    away_fortune: dict[str, Any] = {ax: getattr(away_fortune_row, ax) for ax in AXIS_ORDER}

    return score_matchup_from_raw(
        home_pitcher,
        away_pitcher,
        home_face,
        home_fortune,
        away_face,
        away_fortune,
        game_date,
    )
