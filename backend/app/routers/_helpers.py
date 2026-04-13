"""Shared helpers for FACEMETRICS route handlers."""

from app.models.pitcher import Pitcher
from app.schemas.response import PitcherSummary


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
