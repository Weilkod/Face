"""
Fortune generation service for FACEMETRICS (운세 분석).

Public API:
    get_or_create_fortune_scores(
        session, pitcher, game_date,
        *, opponent_team="미정", stadium="미정"
    ) -> FortuneScore

Flow:
    1. Query fortune_scores by (pitcher_id, game_date) — if found, return cached row.
    2. Format user prompt from fortune_reading.txt with pitcher metadata.
    3. Call Claude Text (claude-sonnet-4-6) with system prompt cached via ephemeral.
       First try: temperature=0.7.
    4. Parse JSON → FortuneReadingResult. On failure, retry once (temperature=0).
    5. On second failure or API error, use hash_fortune_scores fallback.
    6. session.add() + session.flush() — caller owns the transaction and is
       responsible for commit/rollback (see face_analyzer for the same pattern).

Note: flush() can raise IntegrityError on the unique (pitcher_id, game_date)
constraint under concurrent inserts. Callers wrap the call in their outer
try/except.

Implements README §3-2, §3-3, §4-2 and CLAUDE.md §2, §4.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")


def _now_kst() -> datetime:
    return datetime.now(tz=_KST).replace(tzinfo=None)
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.fortune_score import FortuneScore
from app.models.pitcher import Pitcher
from app.prompts import load_prompt
from app.schemas.ai import FortuneReadingResult
from app.services.hash_fallback import hash_fortune_scores

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy client
# ---------------------------------------------------------------------------
_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        import anthropic

        settings = get_settings()
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _clamp_scores(result: FortuneReadingResult) -> FortuneReadingResult:
    axes = [
        "command_fortune",
        "stuff_fortune",
        "composure_fortune",
        "dominance_fortune",
        "destiny_fortune",
    ]
    for axis in axes:
        axis_obj = getattr(result, axis)
        clamped = max(0, min(10, axis_obj.score))
        if clamped != axis_obj.score:
            logger.warning(
                "fortune_generator: score out of range axis=%s score=%d — clamped to %d",
                axis,
                axis_obj.score,
                clamped,
            )
            axis_obj.score = clamped
    lucky = max(1, min(9, result.lucky_inning))
    if lucky != result.lucky_inning:
        logger.warning(
            "fortune_generator: lucky_inning out of range %d — clamped to %d",
            result.lucky_inning,
            lucky,
        )
        result.lucky_inning = lucky
    return result


async def _call_claude_text(
    pitcher: Pitcher,
    game_date: date,
    opponent_team: str,
    stadium: str,
    temperature: float = 0.7,
) -> FortuneReadingResult:
    """Call Claude Text (sonnet) and return a parsed FortuneReadingResult.

    Raises ValueError on JSON parse failure; caller handles retry/fallback.
    """
    settings = get_settings()
    client = _get_client()
    system_text, user_template = load_prompt("fortune_reading")

    # Resolve zodiac/Chinese zodiac — use empty string if attribute missing
    zodiac_sign = getattr(pitcher, "zodiac_sign", "") or ""
    chinese_zodiac = getattr(pitcher, "chinese_zodiac", "") or ""
    birth_date_str = pitcher.birth_date.isoformat() if pitcher.birth_date else ""

    user_prompt = user_template.format(
        pitcher_name=pitcher.name,
        birth_date=birth_date_str,
        zodiac_sign=zodiac_sign,
        chinese_zodiac=chinese_zodiac,
        today_date=game_date.isoformat(),
        opponent_team=opponent_team,
        stadium=stadium,
    )

    response = await client.messages.create(
        model=settings.claude_model_text,
        max_tokens=1024,
        temperature=temperature,
        system=[
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    logger.info(
        "fortune_generator: pitcher_id=%d date=%s model=%s input_tokens=%d output_tokens=%d cache_read_tokens=%d",
        pitcher.pitcher_id,
        game_date.isoformat(),
        settings.claude_model_text,
        usage.input_tokens,
        usage.output_tokens,
        cache_read,
    )

    raw_text = response.content[0].text
    cleaned = _strip_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}\nRaw: {raw_text[:300]}") from exc

    result = FortuneReadingResult.model_validate(data)
    result = _clamp_scores(result)
    return result


def _build_fortune_score_from_result(
    pitcher_id: int,
    game_date: date,
    result: FortuneReadingResult,
) -> FortuneScore:
    return FortuneScore(
        pitcher_id=pitcher_id,
        game_date=game_date,
        command=result.command_fortune.score,
        stuff=result.stuff_fortune.score,
        composure=result.composure_fortune.score,
        dominance=result.dominance_fortune.score,
        destiny=result.destiny_fortune.score,
        command_reading=result.command_fortune.reading,
        stuff_reading=result.stuff_fortune.reading,
        composure_reading=result.composure_fortune.reading,
        dominance_reading=result.dominance_fortune.reading,
        destiny_reading=result.destiny_fortune.reading,
        daily_summary=result.daily_summary,
        lucky_inning=result.lucky_inning,
        generated_at=_now_kst(),
    )


def _build_fortune_score_from_fallback(
    pitcher_id: int,
    game_date: date,
) -> FortuneScore:
    scores = hash_fortune_scores(pitcher_id, game_date)
    return FortuneScore(
        pitcher_id=pitcher_id,
        game_date=game_date,
        command=int(scores["command"]),
        stuff=int(scores["stuff"]),
        composure=int(scores["composure"]),
        dominance=int(scores["dominance"]),
        destiny=int(scores["destiny"]),
        command_reading=str(scores["command_reading"]),
        stuff_reading=str(scores["stuff_reading"]),
        composure_reading=str(scores["composure_reading"]),
        dominance_reading=str(scores["dominance_reading"]),
        destiny_reading=str(scores["destiny_reading"]),
        daily_summary=str(scores["daily_summary"]),
        lucky_inning=int(scores["lucky_inning"]),
        generated_at=_now_kst(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_or_create_fortune_scores(
    session: AsyncSession,
    pitcher: Pitcher,
    game_date: date,
    *,
    opponent_team: str = "미정",
    stadium: str = "미정",
) -> FortuneScore:
    """Return the cached FortuneScore for (pitcher_id, game_date), creating if absent.

    Deterministic per (pitcher_id, game_date) per CLAUDE.md §2:
    once a row is stored it is returned as-is — Claude is never re-called.
    """
    # 1. Cache hit
    stmt = select(FortuneScore).where(
        FortuneScore.pitcher_id == pitcher.pitcher_id,
        FortuneScore.game_date == game_date,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        logger.debug(
            "fortune_generator: cache hit for pitcher_id=%d date=%s",
            pitcher.pitcher_id,
            game_date.isoformat(),
        )
        return existing

    # 2. Call Claude Text
    fortune_score_obj: FortuneScore | None = None

    try:
        parsed = await _call_claude_text(
            pitcher, game_date, opponent_team, stadium, temperature=0.7
        )
        fortune_score_obj = _build_fortune_score_from_result(pitcher.pitcher_id, game_date, parsed)
    except Exception as first_exc:
        logger.warning(
            "fortune_generator: first attempt failed for pitcher_id=%d date=%s — %s. Retrying temperature=0.",
            pitcher.pitcher_id,
            game_date.isoformat(),
            first_exc,
        )
        try:
            parsed = await _call_claude_text(
                pitcher, game_date, opponent_team, stadium, temperature=0.0
            )
            fortune_score_obj = _build_fortune_score_from_result(
                pitcher.pitcher_id, game_date, parsed
            )
        except Exception as second_exc:
            logger.error(
                "fortune_generator: second attempt failed for pitcher_id=%d date=%s — %s. Hash fallback.",
                pitcher.pitcher_id,
                game_date.isoformat(),
                second_exc,
            )
            fortune_score_obj = _build_fortune_score_from_fallback(pitcher.pitcher_id, game_date)

    session.add(fortune_score_obj)
    await session.flush()  # populate PK; caller owns the transaction
    return fortune_score_obj
