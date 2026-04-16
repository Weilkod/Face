"""Unit tests for app/routers/matchup.py private helpers.

Integration coverage of the /api/matchup/{id} route lives elsewhere; this file
just exercises the rule-based chemistry text population added on top of the
numeric score (see README §2-3 / CLAUDE.md §2).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.models.pitcher import Pitcher
from app.routers.matchup import _build_chemistry_detail, _format_delta


def _pitcher(
    pitcher_id: int,
    name: str,
    chinese_zodiac: str,
    zodiac_sign: str,
    zodiac_element: str,
) -> Pitcher:
    return Pitcher(
        pitcher_id=pitcher_id,
        name=name,
        team="LG",
        birth_date=date(1990, 1, 1),
        chinese_zodiac=chinese_zodiac,
        zodiac_sign=zodiac_sign,
        zodiac_element=zodiac_element,
    )


class TestFormatDelta:
    def test_zero_is_positive_plus_zero(self) -> None:
        assert _format_delta(0) == "+0"

    def test_positive_integer_signed(self) -> None:
        assert _format_delta(2) == "+2"

    def test_negative_float_signed(self) -> None:
        assert _format_delta(-1.5) == "-1.5"

    def test_positive_float_signed(self) -> None:
        assert _format_delta(1.5) == "+1.5"


class TestBuildChemistryDetail:
    """Ensure the helper fills all three text fields from chemistry_calculator."""

    def test_same_element_same_zodiac_group_produces_labels(self) -> None:
        # 자(쥐) + 진(용) are in 삼합 group (자-진-신), both 물 element.
        home = _pitcher(1, "Home", "자", "전갈자리", "물")
        away = _pitcher(2, "Away", "진", "게자리", "물")
        detail = _build_chemistry_detail(home, away, chemistry_score=3.5)

        assert detail.zodiac_detail == "자띠 vs 진띠 — 삼합 (+2)"
        assert detail.element_detail == "전갈자리(물) vs 게자리(물) — 동질 (+1)"
        assert detail.chemistry_comment is not None
        assert "기본 2" in detail.chemistry_comment
        # chemistry_score from the caller must be preserved verbatim.
        assert detail.chemistry_score == 3.5

    def test_numeric_score_not_overwritten_by_breakdown_final(self) -> None:
        # scoring_engine is the source of truth for the stored numeric value;
        # the helper must not silently recompute it from breakdown.final.
        home = _pitcher(1, "Home", "자", "전갈자리", "물")
        away = _pitcher(2, "Away", "오", "사자자리", "불")  # 자-오 충 (-2)
        detail = _build_chemistry_detail(home, away, chemistry_score=1.0)

        assert detail.chemistry_score == 1.0
        assert detail.zodiac_detail is not None
        assert "충 (-2)" in detail.zodiac_detail

    def test_invalid_zodiac_metadata_falls_back_to_blank_text(self) -> None:
        # Defence against unexpected DB values — must not raise to the client.
        home = _pitcher(1, "Home", "자", "전갈자리", "물")
        away = _pitcher(2, "Away", "XYZ", "BadSign", "UnknownElem")
        detail = _build_chemistry_detail(home, away, chemistry_score=2.0)

        assert detail.zodiac_detail is None
        assert detail.element_detail is None
        assert detail.chemistry_comment is None
        # Numeric score is still returned — never surface a 500 to the user.
        assert detail.chemistry_score == 2.0
