"""
Pydantic v2 response schemas for FACEMETRICS API endpoints.

All routes return one of these models — never a raw dict or ORM object.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class PitcherSummary(BaseModel):
    """Minimal pitcher info embedded in matchup responses."""

    model_config = ConfigDict(from_attributes=True)

    pitcher_id: int
    name: str
    name_en: Optional[str] = None
    team: str
    chinese_zodiac: str
    zodiac_sign: str
    zodiac_element: str
    profile_photo: Optional[str] = None


class AxisBreakdown(BaseModel):
    """One axis (e.g. command) showing face + fortune sub-scores."""

    face: int = Field(..., ge=0, le=10, description="관상 점수 0~10")
    fortune: int = Field(..., ge=0, le=10, description="운세 점수 0~10")
    total: int = Field(..., ge=0, le=20, description="합산 점수 0~20")
    face_detail: Optional[str] = None
    fortune_reading: Optional[str] = None


class PitcherScores(BaseModel):
    """All five axis breakdowns for one pitcher in a matchup detail."""

    command: AxisBreakdown
    stuff: AxisBreakdown
    composure: AxisBreakdown
    dominance: AxisBreakdown
    destiny: AxisBreakdown
    total: int = Field(..., ge=0, le=100, description="합산 총점 0~100")
    lucky_inning: Optional[int] = Field(None, ge=1, le=9)
    daily_summary: Optional[str] = None


class ChemistryDetail(BaseModel):
    """띠 + 별자리 상성 breakdown."""

    zodiac_detail: Optional[str] = None
    element_detail: Optional[str] = None
    chemistry_score: float = Field(..., ge=0.0, le=4.0, description="상성 점수 (clamp 0~4)")
    chemistry_comment: Optional[str] = None


# ---------------------------------------------------------------------------
# GET /api/today
# ---------------------------------------------------------------------------


class MatchupSummary(BaseModel):
    """One row in the /api/today matchup list."""

    model_config = ConfigDict(from_attributes=True)

    matchup_id: int
    home_team: str
    away_team: str
    stadium: Optional[str] = None
    home_pitcher: PitcherSummary
    away_pitcher: PitcherSummary
    home_total: int
    away_total: int
    predicted_winner: Optional[str] = None
    winner_comment: Optional[str] = None
    chemistry_score: float = Field(..., ge=0.0, le=4.0)
    game_time: Optional[str] = None
    series_label: Optional[str] = None


class TodayResponse(BaseModel):
    """Response for GET /api/today."""

    date: date
    day_of_week: str
    matchups: list[MatchupSummary]


# ---------------------------------------------------------------------------
# GET /api/matchup/{matchup_id}
# ---------------------------------------------------------------------------


class MatchupDetail(BaseModel):
    """Full detail response for GET /api/matchup/{matchup_id}."""

    matchup_id: int
    game_date: date
    home_team: str
    away_team: str
    stadium: Optional[str] = None
    # TODO: populate once DailySchedule.series_label column exists
    series_label: Optional[str] = None
    game_time: Optional[str] = None
    home_pitcher: PitcherSummary
    away_pitcher: PitcherSummary
    home_scores: PitcherScores
    away_scores: PitcherScores
    home_total: int
    away_total: int
    chemistry: ChemistryDetail
    chemistry_score: float = Field(..., ge=0.0, le=4.0)
    predicted_winner: Optional[str] = None
    winner_comment: Optional[str] = None


# ---------------------------------------------------------------------------
# GET /api/pitcher/{pitcher_id}
# ---------------------------------------------------------------------------


class FaceScoreDetail(BaseModel):
    """관상 점수 블록 — embedded in PitcherDetail."""

    season: int
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
    analyzed_at: datetime


class FortuneScoreDetail(BaseModel):
    """운세 점수 블록 — embedded in PitcherDetail."""

    game_date: date
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
    lucky_inning: Optional[int] = Field(None, ge=1, le=9)


class PitcherDetail(BaseModel):
    """Full pitcher profile response for GET /api/pitcher/{pitcher_id}."""

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


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------


class HistoryMatchup(MatchupSummary):
    """History row — MatchupSummary + 결과 필드."""

    game_date: date
    actual_winner: Optional[str] = None
    prediction_correct: Optional[bool] = None


class HistoryResponse(BaseModel):
    """Response for GET /api/history."""

    date: date
    matchups: list[HistoryMatchup]


# ---------------------------------------------------------------------------
# GET /api/accuracy
# ---------------------------------------------------------------------------


class PeriodAccuracy(BaseModel):
    total: int
    correct: int
    accuracy_rate: float


class AccuracyResponse(BaseModel):
    """Response for GET /api/accuracy."""

    total_predictions: int
    correct_predictions: int
    accuracy_rate: float
    recent_7_days: Optional[PeriodAccuracy] = None


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


class AdminScheduleResult(BaseModel):
    """Response for POST /admin/crawl-schedule."""

    date: date
    inserted: int
    updated: int
    skipped: int


class AdminAnalyzeFaceResult(BaseModel):
    """Response for POST /admin/analyze-face/{pitcher_id}."""

    pitcher_id: int
    season: int
    face_score_id: int
    command: int
    stuff: int
    composure: int
    dominance: int
    destiny: int
    message: str = "ok"


class AdminFortuneResult(BaseModel):
    """Response for POST /admin/generate-fortune."""

    date: date
    generated: int
    skipped: int
    failed: int


class AdminMatchupResult(BaseModel):
    """Response for POST /admin/calculate-matchups."""

    date: date
    scored: int
    inserted: int
    updated: int
    skipped: int
    failed: int


class UpdateResultRequest(BaseModel):
    """Request body for POST /admin/update-result/{matchup_id}."""

    actual_winner: str = Field(..., min_length=2, max_length=8)


class UpdateResultResponse(BaseModel):
    """Response for POST /admin/update-result/{matchup_id}."""

    matchup_id: int
    actual_winner: str
    message: str = "updated"


# ---------------------------------------------------------------------------
# Crawler review queue (Wave 2 Track F)
# ---------------------------------------------------------------------------


class ReviewQueueItem(BaseModel):
    """
    One entry from the crawler review queue (JSON file representation).

    Mirrors fields stamped by `crawler._append_review()`.
    """

    model_config = ConfigDict(extra="ignore")

    # Identification fields — form the dedup key.
    team: Optional[str] = Field(None, description="Service team code, e.g. 'LG'")
    crawled_name: Optional[str] = Field(None, description="Korean name as crawled from KBO")
    game_date: Optional[str] = Field(None, description="ISO8601 date string, e.g. '2026-04-16'")
    kbo_player_id: Optional[int] = Field(
        None,
        description="KBO playerId — only relevant when crawled_name is None",
    )

    # Optional diagnostic fields set by the crawler.
    normalised_name: Optional[str] = Field(None, description="NFC-normalised crawled_name")
    best_fuzzy_score: Optional[float] = Field(
        None, description="Best rapidfuzz WRatio score at queue time"
    )
    reason: Optional[str] = Field(None, description="Human-readable reason for queueing")

    # Lifecycle timestamps.
    created_at: Optional[str] = Field(None, description="ISO8601 UTC timestamp of first queue")
    resolved: bool = Field(False, description="True when an operator has resolved this entry")
    resolved_at: Optional[str] = Field(
        None, description="ISO8601 UTC timestamp when resolved was set to True"
    )


class ReviewQueueResolveRequest(BaseModel):
    """
    Body for POST /admin/review-queue/resolve.

    Exactly one of crawled_name or kbo_player_id must be supplied to
    reconstruct the composite dedup key together with team + game_date.
    """

    model_config = ConfigDict(extra="forbid")

    team: str = Field(..., description="Service team code, e.g. 'LG'")
    game_date: str = Field(..., description="ISO8601 date string, e.g. '2026-04-16'")
    crawled_name: Optional[str] = Field(
        None,
        description="Korean name as crawled — supply this OR kbo_player_id",
    )
    kbo_player_id: Optional[int] = Field(
        None,
        description="KBO playerId — supply this OR crawled_name (when name is None)",
    )

    @model_validator(mode="after")
    def _check_xor_identifier(self) -> "ReviewQueueResolveRequest":
        has_name = self.crawled_name is not None
        has_id = self.kbo_player_id is not None
        if has_name == has_id:
            raise ValueError(
                "Exactly one of crawled_name or kbo_player_id must be supplied"
            )
        return self
