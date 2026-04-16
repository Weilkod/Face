"""Shared helpers for FACEMETRICS route handlers."""

from datetime import time
from typing import Optional

from app.models.pitcher import Pitcher
from app.schemas.response import PitcherSummary


def format_game_time(t: Optional[time]) -> Optional[str]:
    """Format a time object as 'HH:MM', or return None if t is None."""
    if t is None:
        return None
    return t.strftime("%H:%M")


def pitcher_summary(pitcher: Pitcher) -> PitcherSummary:
    """Convert a Pitcher ORM row to the PitcherSummary response schema."""
    return PitcherSummary(
        pitcher_id=pitcher.pitcher_id,
        name=pitcher.name,
        name_en=pitcher.name_en,
        team=pitcher.team,
        chinese_zodiac=pitcher.chinese_zodiac,
        zodiac_sign=pitcher.zodiac_sign,
        zodiac_element=pitcher.zodiac_element,
        profile_photo=pitcher.profile_photo,
    )


def resolve_winner_name(
    winner: Optional[str],
    home_pitcher: Pitcher,
    away_pitcher: Pitcher,
) -> Optional[str]:
    # Internal enum "home"/"away"/"tie" → display name at response boundary.
    # DB stays enum (accuracy comparison needs it); FE renders the name.
    if winner == "home":
        return home_pitcher.name
    if winner == "away":
        return away_pitcher.name
    if winner == "tie":
        return "무승부"
    return None
