"""Unit tests for app/routers/_helpers.py."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.pitcher import Pitcher
from app.routers._helpers import resolve_winner_name


def _pitcher(name: str) -> Pitcher:
    return Pitcher(
        pitcher_id=1,
        name=name,
        team="LG",
        birth_date=date(1990, 1, 1),
        chinese_zodiac="말",
        zodiac_sign="염소자리",
        zodiac_element="土",
    )


class TestResolveWinnerName:
    """Internal enum → display name at response boundary (FE renders names)."""

    def setup_method(self) -> None:
        self.home = _pitcher("홍길동")
        self.away = _pitcher("김철수")

    def test_home_enum_resolves_to_home_name(self) -> None:
        assert resolve_winner_name("home", self.home, self.away) == "홍길동"

    def test_away_enum_resolves_to_away_name(self) -> None:
        assert resolve_winner_name("away", self.home, self.away) == "김철수"

    def test_tie_resolves_to_korean_label(self) -> None:
        assert resolve_winner_name("tie", self.home, self.away) == "무승부"

    def test_none_returns_none(self) -> None:
        assert resolve_winner_name(None, self.home, self.away) is None

    def test_unknown_value_returns_none(self) -> None:
        # Defensive: bad DB rows should not crash the route
        assert resolve_winner_name("garbage", self.home, self.away) is None
