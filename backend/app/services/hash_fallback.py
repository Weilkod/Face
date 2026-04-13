"""
Deterministic hash-based fallback scorer for FACEMETRICS.

Used when the Claude API is unavailable or JSON parsing fails after retries.
All functions are pure sync, no I/O, no async.

Hash strategy:
  sha256("<pitcher_id>-<key>-<seed_suffix>")[0] % 11  → 0..10
  A bias of +2 is added and clamped to [0,10] so the distribution
  centres around ~5 rather than ~2.5 (raw mod 11 mean).
"""

from __future__ import annotations

import hashlib
from datetime import date

_FACE_AXES = ("command", "stuff", "composure", "dominance", "destiny")
_FORTUNE_AXES = ("command", "stuff", "composure", "dominance", "destiny")
_FALLBACK_DETAIL = "(폴백) 해시 기반 근사치"
_FALLBACK_READING = "(폴백) 해시 기반 근사치"


def _hash_score(seed: str) -> int:
    """Return a deterministic integer in [0, 10] from an arbitrary seed string.

    Raw sha256[0] % 11 has mean 2.5 (values 0-10 with 11 possible outcomes,
    but byte range 0-255 means values 0-10 are not perfectly uniform).
    We add +2 and clamp to [0,10] to push the mean toward ~5.
    """
    raw = hashlib.sha256(seed.encode()).digest()[0] % 11  # 0..10
    biased = raw + 2  # shift mean up
    return min(biased, 10)


def hash_face_scores(pitcher_id: int, season: int) -> dict[str, int | str]:
    """Return deterministic 관상 fallback scores for (pitcher_id, season).

    Keys: command, stuff, composure, dominance, destiny (each int 0-10),
          plus *_detail strings and overall_impression.
    """
    scores: dict[str, int | str] = {}
    for axis in _FACE_AXES:
        seed = f"{pitcher_id}-{season}-{axis}-face"
        scores[axis] = _hash_score(seed)
        scores[f"{axis}_detail"] = _FALLBACK_DETAIL

    scores["overall_impression"] = _FALLBACK_DETAIL
    return scores


def hash_fortune_scores(pitcher_id: int, game_date: date) -> dict[str, int | str]:
    """Return deterministic 운세 fallback scores for (pitcher_id, game_date).

    Keys: command, stuff, composure, dominance, destiny (each int 0-10),
          plus *_reading strings, daily_summary, and lucky_inning (1-9).
    """
    date_str = game_date.isoformat()
    scores: dict[str, int | str] = {}
    for axis in _FORTUNE_AXES:
        seed = f"{pitcher_id}-{date_str}-{axis}-fortune"
        scores[axis] = _hash_score(seed)
        scores[f"{axis}_reading"] = _FALLBACK_READING

    scores["daily_summary"] = _FALLBACK_READING

    # lucky_inning: deterministic 1..9
    lucky_seed = f"{pitcher_id}-{date_str}-lucky_inning"
    raw = hashlib.sha256(lucky_seed.encode()).digest()[0] % 9  # 0..8
    scores["lucky_inning"] = raw + 1  # 1..9

    return scores
