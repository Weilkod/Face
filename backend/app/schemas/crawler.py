"""
schemas/crawler.py — Pydantic v2 models for the KBO schedule crawler.

ScheduleEntry is the canonical output of `fetch_today_schedule()`. It carries
enough information for the pipeline to:
  1. Populate daily_schedules (home_team, away_team, stadium, game_time,
     home_starter, away_starter, source_url, crawled_at).
  2. Resolve starters to pitcher_id — eventually via
     `match_pitcher_by_kbo_id` once A-5 / A-6 land; for now via
     `match_pitcher_name` against crawled Korean names.

KBO 단일 소스로 재설계됨 (2026-04-13, carry-over §A). 네이버/스탯티즈 폴백은
`source` Literal 에서 제거. 과거 크롤 row 가 DB 에 남아 있어도 `extra="ignore"`
이므로 직렬화는 문제 없지만, 새 row 는 반드시 `source="kbo"` 로 쓰인다.
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

    # KBO gameId (e.g. "20260414LTLG0") returned by GetTodayGames. Used to
    # fetch the GameCenter page for the starter playerIds. None if the
    # crawler couldn't parse one out.
    game_id: Optional[str] = Field(None, description="KBO internal gameId")

    # Raw crawled names — may be None until A-5/A-6 wire up the profile
    # harvester (this session only populates kbo_ids below).
    home_starter_name: Optional[str] = Field(None, description="홈 선발투수 한글 이름")
    away_starter_name: Optional[str] = Field(None, description="원정 선발투수 한글 이름")

    # KBO playerId captured from the GameCenter HTML (`li.game-cont` attrs).
    # None means 선발 미정 or parse failure. A-5 will translate these to
    # local pitcher_ids via a new ID-based matcher.
    home_starter_kbo_id: Optional[int] = Field(None, description="KBO playerId (home)")
    away_starter_kbo_id: Optional[int] = Field(None, description="KBO playerId (away)")

    # Resolved local pitcher_ids — None if matching failed.
    home_pitcher_id: Optional[int] = Field(None)
    away_pitcher_id: Optional[int] = Field(None)

    # Which data source produced this row. KBO single-source since §A rewrite.
    source: Literal["kbo"] = Field(
        "kbo", description="Data source that produced this entry"
    )

    # URL of the endpoint that was actually called.
    source_url: Optional[str] = Field(None)
