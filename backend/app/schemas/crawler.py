"""
schemas/crawler.py — Pydantic v2 models for the KBO schedule crawler.

ScheduleEntry is the canonical output of fetch_today_schedule().
It carries enough information for the pipeline to:
  1. Populate daily_schedules (home_team, away_team, stadium, game_time,
     home_starter, away_starter, source_url, crawled_at).
  2. Resolve pitcher names to pitcher_id via match_pitcher_name().

source: which of the three fallback tiers actually answered.
  "kbo"    — koreabaseball.com (primary)
  "naver"  — sports.naver.com  (secondary)
  "statiz" — statiz.co.kr      (tertiary)
"""

from __future__ import annotations

from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScheduleEntry(BaseModel):
    """One game fetched by the crawler for a given date."""

    model_config = ConfigDict(extra="ignore")

    game_date: date
    home_team: str = Field(..., description="Home team code, e.g. 'LG'")
    away_team: str = Field(..., description="Away team code, e.g. 'SSG'")
    stadium: Optional[str] = Field(None, description="Stadium name in Korean")
    game_time: Optional[time] = Field(None, description="Scheduled first pitch (KST)")

    # Raw crawled names — may be None if starter not yet announced.
    home_starter_name: Optional[str] = Field(None, description="홈 선발투수 한글 이름")
    away_starter_name: Optional[str] = Field(None, description="원정 선발투수 한글 이름")

    # Resolved pitcher_ids — None if name→id matching failed.
    home_pitcher_id: Optional[int] = Field(None)
    away_pitcher_id: Optional[int] = Field(None)

    # Which data source produced this row.
    source: Literal["kbo", "naver", "statiz"] = Field(
        ..., description="Data source that produced this entry"
    )

    # URL of the page that was actually parsed.
    source_url: Optional[str] = Field(None)
