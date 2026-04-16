"""Wave 1 Track D — 상성(相性) calculator audit + edge-case coverage.

These tests lock down the rule-based chemistry scorer against README §2-3
so a future refactor cannot silently drift the zodiac/element tables or the
base+clamp arithmetic. Every assertion references a spec row directly; if
the spec moves, the test must move with it.

Covers:
  1. 띠 table — all 4×samhap groups, all 6 yukhap pairs, all 6 wonjin pairs,
     all 6 chung pairs → exact delta + label.
  2. 별자리 table — same-element (동질), harmony(상생), clash(상극), neutral.
  3. Arithmetic — base=2, raw=base+zodiac+element, final=clamp[0,4].
  4. Clamping edges — samhap+harmony over-clamps to 4; chung+clash under-
     clamps to 0; chung+harmony crosses zero cleanly.
  5. Same-zodiac short-circuit — labelled "자기(동일 띠)", delta 0.
  6. Input validation — unknown zodiac / element raises ValueError.
  7. Whitespace normalization — leading/trailing spaces are stripped.
  8. Symmetry — chemistry(A, B) == chemistry(B, A) for every field.
  9. Duck-typed wrapper — chemistry_for_pitchers() against a plain object.

Note: Section 10 reaches into the module's private JSON-loader helpers
(`_load_zodiac_data` / `_load_constellation_data`) on purpose — they are the
canonical binding between the data files and the scorer, and locking them
against the README tables is exactly what the audit asks for. If these
helpers are ever renamed or replaced by a public accessor, update this file.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.chemistry_calculator import (
    ChemistryBreakdown,
    _load_constellation_data,
    _load_zodiac_data,
    calculate_chemistry,
    chemistry_for_pitchers,
)


# ---------------------------------------------------------------------------
# 1. 띠 — samhap / yukhap / wonjin / chung exhaustive coverage
# ---------------------------------------------------------------------------

# README §2-3: 삼합(+2) — 자-진-신, 축-사-유, 인-오-술, 묘-미-해
SAMHAP_PAIRS = [
    ("자", "진"), ("자", "신"), ("진", "신"),
    ("축", "사"), ("축", "유"), ("사", "유"),
    ("인", "오"), ("인", "술"), ("오", "술"),
    ("묘", "미"), ("묘", "해"), ("미", "해"),
]

# README §2-3: 육합(+1.5) — 자-축, 인-해, 묘-술, 진-유, 사-신, 오-미
YUKHAP_PAIRS = [("자", "축"), ("인", "해"), ("묘", "술"), ("진", "유"), ("사", "신"), ("오", "미")]

# README §2-3: 원진(-1.5) — 자-미, 축-오, 인-사, 묘-진, 신-해, 유-술
WONJIN_PAIRS = [("자", "미"), ("축", "오"), ("인", "사"), ("묘", "진"), ("신", "해"), ("유", "술")]

# README §2-3: 충(-2) — 자-오, 축-미, 인-신, 묘-유, 진-술, 사-해
CHUNG_PAIRS = [("자", "오"), ("축", "미"), ("인", "신"), ("묘", "유"), ("진", "술"), ("사", "해")]


@pytest.mark.parametrize("home,away", SAMHAP_PAIRS)
def test_samhap_pair_gives_plus_two(home: str, away: str) -> None:
    # Neutral element pair isolates the zodiac contribution — raw lands on the
    # exact ceiling 4.0 (base 2 + samhap 2 + neutral 0), so no clamping is
    # exercised here. See test_over_clamp_* for the actual clamp edges.
    r = calculate_chemistry(home, away, "불", "흙")  # 불↔흙 neutral
    assert r.zodiac_label == "삼합"
    assert r.zodiac_delta == 2.0
    assert r.element_label == "중립"
    assert r.element_delta == 0.0
    assert r.raw == 4.0
    assert r.final == 4.0


@pytest.mark.parametrize("home,away", YUKHAP_PAIRS)
def test_yukhap_pair_gives_plus_one_and_a_half(home: str, away: str) -> None:
    r = calculate_chemistry(home, away, "불", "흙")
    assert r.zodiac_label == "육합"
    assert r.zodiac_delta == 1.5
    assert r.raw == pytest.approx(3.5)
    assert r.final == pytest.approx(3.5)


@pytest.mark.parametrize("home,away", WONJIN_PAIRS)
def test_wonjin_pair_gives_minus_one_and_a_half(home: str, away: str) -> None:
    r = calculate_chemistry(home, away, "불", "흙")
    assert r.zodiac_label == "원진"
    assert r.zodiac_delta == -1.5
    assert r.raw == pytest.approx(0.5)
    assert r.final == pytest.approx(0.5)


@pytest.mark.parametrize("home,away", CHUNG_PAIRS)
def test_chung_pair_gives_minus_two(home: str, away: str) -> None:
    r = calculate_chemistry(home, away, "불", "흙")
    assert r.zodiac_label == "충"
    assert r.zodiac_delta == -2.0
    assert r.raw == 0.0
    assert r.final == 0.0


def test_neutral_zodiac_returns_zero_delta() -> None:
    # 자-인: not in samhap/yukhap/wonjin/chung → neutral
    r = calculate_chemistry("자", "인", "불", "흙")
    assert r.zodiac_label == "중립"
    assert r.zodiac_delta == 0.0
    assert r.raw == 2.0
    assert r.final == 2.0


# ---------------------------------------------------------------------------
# 2. 별자리 원소 — same / harmony / clash / neutral
# ---------------------------------------------------------------------------

ELEMENTS = ("불", "흙", "바람", "물")
HARMONY_PAIRS = [("불", "바람"), ("물", "흙")]
CLASH_PAIRS = [("불", "물"), ("바람", "흙")]


@pytest.mark.parametrize("elem", ELEMENTS)
def test_same_element_gives_plus_one(elem: str) -> None:
    # Use a neutral zodiac pair so only element drives the delta
    r = calculate_chemistry("자", "인", elem, elem)
    assert r.element_label == "동질"
    assert r.element_delta == 1.0


@pytest.mark.parametrize("home,away", HARMONY_PAIRS)
def test_harmony_pair_gives_plus_one_and_a_half(home: str, away: str) -> None:
    r = calculate_chemistry("자", "인", home, away)
    assert r.element_label == "상생"
    assert r.element_delta == 1.5


@pytest.mark.parametrize("home,away", CLASH_PAIRS)
def test_clash_pair_gives_minus_one(home: str, away: str) -> None:
    r = calculate_chemistry("자", "인", home, away)
    assert r.element_label == "상극"
    assert r.element_delta == -1.0


def test_element_harmony_and_clash_are_symmetric() -> None:
    # 불-바람 and 바람-불 must tie
    a = calculate_chemistry("자", "인", "불", "바람")
    b = calculate_chemistry("자", "인", "바람", "불")
    assert a.element_label == b.element_label == "상생"
    assert a.element_delta == b.element_delta == 1.5


# README §2-3 neutral: all pairings of 4 elements that are not {same, harmony, clash}.
# With same=4 + harmony=2×2 + clash=2×2 = 12, the 4 remaining ordered pairs are:
# 불-흙, 흙-불, 바람-물, 물-바람. Parametrize both so a future regression that
# promotes either pair to harmony/clash is caught.
NEUTRAL_ELEMENT_PAIRS = [("불", "흙"), ("흙", "불"), ("바람", "물"), ("물", "바람")]


@pytest.mark.parametrize("home,away", NEUTRAL_ELEMENT_PAIRS)
def test_neutral_element_pair_returns_zero(home: str, away: str) -> None:
    r = calculate_chemistry("자", "인", home, away)
    assert r.element_label == "중립"
    assert r.element_delta == 0.0


# ---------------------------------------------------------------------------
# 3. Arithmetic — base 2 + zodiac + element, clamp [0, 4]
# ---------------------------------------------------------------------------

def test_base_score_is_two_and_clamp_range_is_zero_to_four() -> None:
    # Guard the JSON constants themselves — README §2-3 specifies these exactly.
    meta = _load_zodiac_data()["_meta"]
    assert meta["base_score"] == 2.0
    assert meta["clamp_range"] == [0.0, 4.0]


def test_raw_equals_base_plus_both_deltas() -> None:
    r = calculate_chemistry("자", "진", "불", "바람")   # 삼합 +2, 상생 +1.5 → raw 5.5
    assert r.base == 2.0
    assert r.zodiac_delta == 2.0
    assert r.element_delta == 1.5
    assert r.raw == pytest.approx(5.5)


# ---------------------------------------------------------------------------
# 4. Clamping edges — README §2-3 "0~4점 범위로 클램핑"
# ---------------------------------------------------------------------------

def test_over_clamp_samhap_plus_harmony_caps_at_four() -> None:
    # 자-진 삼합 + 불-바람 상생 = 2 + 2 + 1.5 = 5.5 → clamped to 4
    r = calculate_chemistry("자", "진", "불", "바람")
    assert r.raw == pytest.approx(5.5)
    assert r.final == 4.0


def test_over_clamp_samhap_plus_same_element_caps_at_four() -> None:
    # 자-진 삼합 + same element 불-불 = 2 + 2 + 1 = 5 → clamped to 4
    r = calculate_chemistry("자", "진", "불", "불")
    assert r.raw == 5.0
    assert r.final == 4.0


def test_under_clamp_chung_plus_clash_floors_at_zero() -> None:
    # 자-오 충 + 불-물 상극 = 2 + (-2) + (-1) = -1 → clamped to 0
    r = calculate_chemistry("자", "오", "불", "물")
    assert r.raw == -1.0
    assert r.final == 0.0


def test_under_clamp_wonjin_plus_clash_floors_at_zero() -> None:
    # 자-미 원진 + 불-물 상극 = 2 + (-1.5) + (-1) = -0.5 → clamped to 0
    r = calculate_chemistry("자", "미", "불", "물")
    assert r.raw == pytest.approx(-0.5)
    assert r.final == 0.0


def test_chung_plus_harmony_crosses_zero_cleanly() -> None:
    # 자-오 충 + 불-바람 상생 = 2 + (-2) + 1.5 = 1.5 → no clamp
    r = calculate_chemistry("자", "오", "불", "바람")
    assert r.raw == pytest.approx(1.5)
    assert r.final == pytest.approx(1.5)


def test_chung_plus_neutral_hits_floor_exactly() -> None:
    # 자-오 충 + neutral element = 2 + (-2) + 0 = 0, exact floor (not clamped)
    r = calculate_chemistry("자", "오", "불", "흙")
    assert r.raw == 0.0
    assert r.final == 0.0


def test_samhap_plus_neutral_stays_below_ceiling() -> None:
    # 자-진 삼합 + neutral = 2 + 2 + 0 = 4, exact ceiling (not clamped)
    r = calculate_chemistry("자", "진", "불", "흙")
    assert r.raw == 4.0
    assert r.final == 4.0


# ---------------------------------------------------------------------------
# 5. Same-zodiac — treated as 기본(0), not samhap, even when the zodiac
#     appears in a 삼합 group (e.g. 자 ∈ [자, 진, 신]).
# ---------------------------------------------------------------------------

def test_same_zodiac_is_not_treated_as_samhap() -> None:
    # 자-자 would be in the 자-진-신 samhap group if taken literally, but the
    # relation is defined between distinct zodiacs. The calculator must return
    # 0 delta with the dedicated "자기(동일 띠)" label.
    r = calculate_chemistry("자", "자", "불", "흙")
    assert r.zodiac_label == "자기(동일 띠)"
    assert r.zodiac_delta == 0.0


def test_same_zodiac_plus_same_element_intra_team_style() -> None:
    # Same team, same profile: zodiac 자-자 (0) + element 불-불 (+1) = 3
    r = calculate_chemistry("자", "자", "불", "불")
    assert r.zodiac_label == "자기(동일 띠)"
    assert r.element_label == "동질"
    assert r.raw == 3.0
    assert r.final == 3.0


def test_same_zodiac_from_every_branch_gives_label() -> None:
    # Exhaustive: every one of 12 branches hits the same-zodiac short-circuit
    branches = _load_zodiac_data()["_meta"]["branch_order"]
    for z in branches:
        r = calculate_chemistry(z, z, "불", "흙")
        assert r.zodiac_label == "자기(동일 띠)"
        assert r.zodiac_delta == 0.0


# ---------------------------------------------------------------------------
# 6. Input validation
# ---------------------------------------------------------------------------

def test_unknown_home_zodiac_raises() -> None:
    with pytest.raises(ValueError, match="unknown chinese_zodiac"):
        calculate_chemistry("XX", "자", "불", "불")


def test_unknown_away_zodiac_raises() -> None:
    with pytest.raises(ValueError, match="unknown chinese_zodiac"):
        calculate_chemistry("자", "rabbit", "불", "불")


def test_unknown_home_element_raises() -> None:
    with pytest.raises(ValueError, match="unknown element"):
        calculate_chemistry("자", "진", "fire", "불")


def test_unknown_away_element_raises() -> None:
    with pytest.raises(ValueError, match="unknown element"):
        calculate_chemistry("자", "진", "불", "earth")


def test_empty_zodiac_raises() -> None:
    with pytest.raises(ValueError, match="unknown chinese_zodiac"):
        calculate_chemistry("", "자", "불", "불")


# ---------------------------------------------------------------------------
# 7. Whitespace normalization
# ---------------------------------------------------------------------------

def test_whitespace_is_stripped_before_validation() -> None:
    r = calculate_chemistry(" 자 ", "진\t", "\n불", "바람 ")
    assert r.zodiac_label == "삼합"
    assert r.element_label == "상생"
    assert r.final == 4.0


# ---------------------------------------------------------------------------
# 8. Symmetry — README states relationships are between two pitchers, so
#     swapping home/away must not change any field.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("home,away", SAMHAP_PAIRS + YUKHAP_PAIRS + WONJIN_PAIRS + CHUNG_PAIRS)
def test_zodiac_relation_is_symmetric(home: str, away: str) -> None:
    a = calculate_chemistry(home, away, "불", "흙")
    b = calculate_chemistry(away, home, "불", "흙")
    assert a == b


def test_full_chemistry_is_symmetric_with_harmony() -> None:
    a = calculate_chemistry("자", "진", "불", "바람")
    b = calculate_chemistry("진", "자", "바람", "불")
    assert a == b


# ---------------------------------------------------------------------------
# 9. Duck-typed wrapper — chemistry_for_pitchers() must work with any object
#     exposing .chinese_zodiac and .zodiac_element.
# ---------------------------------------------------------------------------

@dataclass
class _FakePitcher:
    chinese_zodiac: str
    zodiac_element: str


def test_chemistry_for_pitchers_accepts_duck_typed_objects() -> None:
    home = _FakePitcher(chinese_zodiac="자", zodiac_element="불")
    away = _FakePitcher(chinese_zodiac="진", zodiac_element="바람")
    r = chemistry_for_pitchers(home, away)
    assert isinstance(r, ChemistryBreakdown)
    assert r.zodiac_label == "삼합"
    assert r.element_label == "상생"
    assert r.final == 4.0


# ---------------------------------------------------------------------------
# 10. JSON spec guards — fail loudly if anyone edits the data files away
#     from README §2-3 without also updating this test.
# ---------------------------------------------------------------------------

def test_zodiac_json_matches_readme_deltas() -> None:
    d = _load_zodiac_data()
    assert d["samhap"]["delta"] == 2.0
    assert d["yukhap"]["delta"] == 1.5
    assert d["wonjin"]["delta"] == -1.5
    assert d["chung"]["delta"] == -2.0
    assert len(d["samhap"]["groups"]) == 4
    assert len(d["yukhap"]["pairs"]) == 6
    assert len(d["wonjin"]["pairs"]) == 6
    assert len(d["chung"]["pairs"]) == 6


def test_element_json_matches_readme_deltas() -> None:
    ec = _load_constellation_data()["_meta"]["element_compat"]
    assert ec["same"]["delta"] == 1.0
    assert ec["harmony"]["delta"] == 1.5
    assert ec["clash"]["delta"] == -1.0
    assert ec["neutral"]["delta"] == 0.0
    assert sorted(tuple(sorted(p)) for p in ec["harmony"]["pairs"]) == [("물", "흙"), ("바람", "불")]
    assert sorted(tuple(sorted(p)) for p in ec["clash"]["pairs"]) == [("물", "불"), ("바람", "흙")]
