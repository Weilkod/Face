"""
schemas/response.py — Pydantic v2 response schemas for FACEMETRICS admin endpoints.

ReviewQueueItem:
    Serialisation of a single entry in data/crawler_review_queue.json.
    Field definitions match the fields stamped by crawler._append_review().

ReviewQueueResolveRequest:
    Body for POST /admin/review-queue/resolve.
    Caller supplies the composite key to identify the entry to toggle.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewQueueItem(BaseModel):
    """One entry from the crawler review queue (JSON file representation)."""

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
