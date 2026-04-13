"""
Pydantic v2 response schemas for FACEMETRICS public API endpoints.

All schemas use model_config = ConfigDict(from_attributes=True) so they can
be built from SQLAlchemy ORM objects as well as plain dicts.

Disclaimer string is included on every top-level response shape per
CLAUDE.md §6 / README §6 entertainment-only requirement.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.services.scoring_engine import AXIS_ORDER  # noqa: F401 — re-exported for routers

_DISCLAIMER = "본 콘텐츠는 엔터테인먼트 목적입니다. 베팅 등에 활용하지 마세요."
_DISCLAIMER_SHORT = "본 콘텐츠는 엔터테인먼트 목적입니다."


class AxisScoreSummary(BaseModel):
    """One axis contribution for a single pitcher — used in the radar chart."""

    model_config = ConfigDict(from_attributes=True)

    axis: str              # one of AXIS_ORDER
    face: int              # 관상 score 0-10
    fortune: int           # 운세 score 0-10
    total: int             # face + fortune (+ chemistry for destiny), rounded to int
    winner: str            # "home" | "away" | "tie"


# ---------------------------------------------------------------------------
# Pitcher summary (list view)
# ---------------------------------------------------------------------------


class PitcherSummary(BaseModel):
    """Compact pitcher card used in /api/today and /api/history."""

    model_config = ConfigDict(from_attributes=True)

    pitcher_id: int
    name: str
    team: str
    profile_photo: Optional[str] = None
    total_score: int
    axes: list[AxisScoreSummary]   # 5 entries, AXIS_ORDER order


# ---------------------------------------------------------------------------
# Matchup summary (list view)
# ---------------------------------------------------------------------------


class MatchupSummary(BaseModel):
    """One matchup card — enough for the today/history list page.

    Always embedded inside TodayResponse / HistoryResponse which carry the
    §6 disclaimer at the envelope level.  MatchupSummary itself is never
    returned as a bare top-level response, so a per-object disclaimer field
    is intentionally omitted here.
    """

    model_config = ConfigDict(from_attributes=True)

    matchup_id: int
    game_date: date
    home_team: str
    away_team: str
    stadium: Optional[str] = None
    home_pitcher: PitcherSummary
    away_pitcher: PitcherSummary
    chemistry_score: float
    predicted_winner: str
    winner_comment: Optional[str] = None


# ---------------------------------------------------------------------------
# /api/today  and  /api/history  top-level response
# ---------------------------------------------------------------------------


class TodayResponse(BaseModel):
    """Response envelope for GET /api/today and GET /api/history."""

    model_config = ConfigDict(from_attributes=True)

    game_date: date
    matchups: list[MatchupSummary]
    disclaimer: str = _DISCLAIMER


# ---------------------------------------------------------------------------
# Detail schemas (face + fortune full text)
# ---------------------------------------------------------------------------


class FaceScoreDetail(BaseModel):
    """Full 관상 analysis for one pitcher — shown in the matchup detail page."""

    model_config = ConfigDict(from_attributes=True)

    command: int
    stuff: int
    composure: int
    dominance: int
    destiny: int
    command_detail: Optional[str] = None
    stuff_detail: Optional[str] = None
    composure_detail: Optional[str] = None
    dominance_detail: Optional[str] = None
    destiny_detail: Optional[str] = None
    overall_impression: Optional[str] = None


class FortuneScoreDetail(BaseModel):
    """Full 운세 reading for one pitcher on one game date."""

    model_config = ConfigDict(from_attributes=True)

    command: int
    stuff: int
    composure: int
    dominance: int
    destiny: int
    command_reading: Optional[str] = None
    stuff_reading: Optional[str] = None
    composure_reading: Optional[str] = None
    dominance_reading: Optional[str] = None
    destiny_reading: Optional[str] = None
    daily_summary: Optional[str] = None
    lucky_inning: Optional[int] = None


# ---------------------------------------------------------------------------
# Full pitcher detail (matchup detail + pitcher page)
# ---------------------------------------------------------------------------


class PitcherDetail(BaseModel):
    """Complete pitcher info including all scores — used in matchup detail."""

    model_config = ConfigDict(from_attributes=True)

    pitcher_id: int
    name: str
    team: str
    birth_date: date
    chinese_zodiac: str
    zodiac_sign: str
    zodiac_element: str
    profile_photo: Optional[str] = None
    face_scores: Optional[FaceScoreDetail] = None
    fortune_scores: Optional[FortuneScoreDetail] = None
    total_score: int
    axes: list[AxisScoreSummary]


# ---------------------------------------------------------------------------
# /api/matchup/{matchup_id}
# ---------------------------------------------------------------------------


class MatchupDetailResponse(BaseModel):
    """Full matchup detail — 5-axis breakdown + all comment text."""

    model_config = ConfigDict(from_attributes=True)

    matchup_id: int
    game_date: date
    home_team: str
    away_team: str
    stadium: Optional[str] = None
    home_pitcher: PitcherDetail
    away_pitcher: PitcherDetail
    chemistry_score: float
    predicted_winner: str
    winner_comment: Optional[str] = None
    actual_winner: Optional[str] = None
    disclaimer: str = _DISCLAIMER_SHORT


# ---------------------------------------------------------------------------
# /api/pitcher/{pitcher_id}
# ---------------------------------------------------------------------------


class PitcherProfileResponse(BaseModel):
    """Pitcher profile page — full info + today's fortune."""

    model_config = ConfigDict(from_attributes=True)

    pitcher_id: int
    name: str
    name_en: Optional[str] = None
    team: str
    birth_date: date
    chinese_zodiac: str
    zodiac_sign: str
    zodiac_element: str
    blood_type: Optional[str] = None
    profile_photo: Optional[str] = None
    face_scores: Optional[FaceScoreDetail] = None
    today_fortune: Optional[FortuneScoreDetail] = None
    disclaimer: str = _DISCLAIMER_SHORT


# ---------------------------------------------------------------------------
# /api/accuracy
# ---------------------------------------------------------------------------


class AccuracyResponse(BaseModel):
    """Cumulative prediction accuracy statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_predictions: int
    correct_predictions: int
    accuracy_rate: float          # 0.0 – 1.0
    disclaimer: str = _DISCLAIMER_SHORT
