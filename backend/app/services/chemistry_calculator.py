"""
chemistry_calculator.py — 운명력 상성(相性) 규칙 기반 계산기

README §2-3 "상성(相性) 시스템 — 운명력의 핵심" 에 정의된 규칙을 순수 함수로 구현.
AI 호출 없음, DB 없음, I/O는 모듈 로드 시 JSON 읽기 1회만.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

# config.py 에서 PROJECT_ROOT 를 가져온다 (backend/app/config.py 에 정의돼 있음).
from app.config import PROJECT_ROOT


# ---------------------------------------------------------------------------
# JSON 로드 (lru_cache 로 최초 1회만 읽음)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_zodiac_data() -> dict[str, Any]:
    """data/zodiac_compatibility.json 로드 — README §2-3 띠 궁합표"""
    path = PROJECT_ROOT / "data" / "zodiac_compatibility.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_constellation_data() -> dict[str, Any]:
    """data/constellation_elements.json 로드 — README §2-3 별자리 원소 궁합표"""
    path = PROJECT_ROOT / "data" / "constellation_elements.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 유효값 집합 (lru_cache 로 최초 1회 계산)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _valid_zodiacs() -> frozenset[str]:
    data = _load_zodiac_data()
    return frozenset(data["_meta"]["branch_order"])


@lru_cache(maxsize=1)
def _valid_elements() -> frozenset[str]:
    data = _load_constellation_data()
    return frozenset(sign["element"] for sign in data["signs"])


# ---------------------------------------------------------------------------
# 결과 데이터클래스
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChemistryBreakdown:
    base: float           # 항상 2.0 (README §2-3 "상성운 기본 점수 2점")
    zodiac_delta: float   # 삼합/육합/원진/충/중립 조정값
    zodiac_label: str     # "삼합" | "육합" | "원진" | "충" | "중립" | "자기(동일 띠)"
    element_delta: float  # 별자리 원소 조정값
    element_label: str    # "동질" | "상생" | "상극" | "중립"
    raw: float            # base + zodiac_delta + element_delta (클램핑 전)
    final: float          # clamp_range([0, 4]) 적용 후 최종값


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _match_zodiac(home: str, away: str) -> tuple[float, str]:
    """
    README §2-3 띠 궁합표 — 첫 번째 매칭 규칙 우선.

    우선순위:
      1. 동일 띠 → 자기(동일 띠), delta 0.0
      2. 삼합(三合) +2.0  (같은 3-그룹, 자기 제외)
      3. 육합(六合) +1.5
      4. 원진(怨嗔) -1.5
      5. 충(沖)    -2.0
      6. 중립       0.0
    """
    if home == away:
        return 0.0, "자기(동일 띠)"

    data = _load_zodiac_data()
    pair = frozenset([home, away])

    # README §2-3 삼합: 자-진-신, 축-사-유, 인-오-술, 묘-미-해
    for group in data["samhap"]["groups"]:
        if home in group and away in group:
            return float(data["samhap"]["delta"]), "삼합"

    # README §2-3 육합: 자-축, 인-해, 묘-술, 진-유, 사-신, 오-미
    for p in data["yukhap"]["pairs"]:
        if pair == frozenset(p):
            return float(data["yukhap"]["delta"]), "육합"

    # README §2-3 원진: 자-미, 축-오, 인-사, 묘-진, 신-해, 유-술
    for p in data["wonjin"]["pairs"]:
        if pair == frozenset(p):
            return float(data["wonjin"]["delta"]), "원진"

    # README §2-3 충: 자-오, 축-미, 인-신, 묘-유, 진-술, 사-해
    for p in data["chung"]["pairs"]:
        if pair == frozenset(p):
            return float(data["chung"]["delta"]), "충"

    return 0.0, "중립"


def _match_element(home_elem: str, away_elem: str) -> tuple[float, str]:
    """
    README §2-3 별자리 원소 궁합표.

    - 같은 원소 → 동질 +1.0
    - 불-바람, 물-흙 → 상생 +1.5
    - 불-물, 바람-흙 → 상극 -1.0
    - 나머지 → 중립 0.0
    """
    if home_elem == away_elem:
        return 1.0, "동질"

    data = _load_constellation_data()
    ec = data["_meta"]["element_compat"]
    pair = frozenset([home_elem, away_elem])

    for p in ec["harmony"]["pairs"]:
        if pair == frozenset(p):
            return float(ec["harmony"]["delta"]), "상생"

    for p in ec["clash"]["pairs"]:
        if pair == frozenset(p):
            return float(ec["clash"]["delta"]), "상극"

    return 0.0, "중립"


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def calculate_chemistry(
    home_chinese_zodiac: str,
    away_chinese_zodiac: str,
    home_element: str,
    away_element: str,
) -> ChemistryBreakdown:
    """
    두 투수 간 상성(相性) 점수를 계산한다.

    README §2-3 "상성운 기본 점수 2점에서 위 두 궁합의 합산을 더해 0~4점 범위로 클램핑."

    Parameters
    ----------
    home_chinese_zodiac : str
        홈 투수의 띠 (예: "자", "축", "인" … "해")
    away_chinese_zodiac : str
        원정 투수의 띠
    home_element : str
        홈 투수의 별자리 원소 ("불" | "흙" | "바람" | "물")
    away_element : str
        원정 투수의 별자리 원소

    Returns
    -------
    ChemistryBreakdown

    Raises
    ------
    ValueError
        알 수 없는 띠 또는 원소가 입력될 경우.
    """
    # --- 입력 정규화 (공백 제거, 풀-width 고려 불필요 — 데이터는 단일 한자) ---
    home_z = home_chinese_zodiac.strip()
    away_z = away_chinese_zodiac.strip()
    home_e = home_element.strip()
    away_e = away_element.strip()

    # --- 검증 ---
    valid_z = _valid_zodiacs()
    if home_z not in valid_z:
        raise ValueError(f"unknown chinese_zodiac: {home_z!r}")
    if away_z not in valid_z:
        raise ValueError(f"unknown chinese_zodiac: {away_z!r}")

    valid_e = _valid_elements()
    if home_e not in valid_e:
        raise ValueError(f"unknown element: {home_e!r}")
    if away_e not in valid_e:
        raise ValueError(f"unknown element: {away_e!r}")

    # --- 계산 ---
    zodiac_delta, zodiac_label = _match_zodiac(home_z, away_z)
    element_delta, element_label = _match_element(home_e, away_e)

    # clamp_range 를 JSON 에서 읽어 하드코딩 방지 (README §2-3 clamp [0, 4])
    clamp_min, clamp_max = _load_zodiac_data()["_meta"]["clamp_range"]
    base: float = float(_load_zodiac_data()["_meta"]["base_score"])

    raw = base + zodiac_delta + element_delta
    final = max(clamp_min, min(clamp_max, raw))

    return ChemistryBreakdown(
        base=base,
        zodiac_delta=zodiac_delta,
        zodiac_label=zodiac_label,
        element_delta=element_delta,
        element_label=element_label,
        raw=raw,
        final=final,
    )


def chemistry_for_pitchers(home_pitcher: Any, away_pitcher: Any) -> ChemistryBreakdown:
    """
    ORM 모델을 직접 임포트하지 않는 덕타입 래퍼 — scoring_engine 연동용.

    home_pitcher / away_pitcher 는 아래 4개 속성을 가진 객체면 무엇이든 수용:
      .chinese_zodiac  (str) — 띠
      .zodiac_element  (str) — 별자리 원소
    """
    return calculate_chemistry(
        home_pitcher.chinese_zodiac,
        away_pitcher.chinese_zodiac,
        home_pitcher.zodiac_element,
        away_pitcher.zodiac_element,
    )
