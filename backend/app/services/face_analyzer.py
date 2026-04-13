"""
Face analysis service for FACEMETRICS (관상 분석).

Public API:
    get_or_create_face_scores(session, pitcher, season=2026) -> FaceScore

Flow:
    1. Query face_scores by (pitcher_id, season) — if found, return cached row.
    2. Build image message block from pitcher.profile_photo (URL or local path).
    3. Call Claude Vision (claude-opus-4-6) with system prompt cached via ephemeral.
    4. Parse JSON → FaceAnalysisResult. On failure, retry once (temperature=0).
    5. On second failure or API error, use hash_face_scores fallback.
    6. Insert FaceScore row, commit, return.

Implements README §3-2, §3-3, §4-1 and CLAUDE.md §2, §4.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")


def _now_kst() -> datetime:
    return datetime.now(tz=_KST).replace(tzinfo=None)
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.face_score import FaceScore
from app.models.pitcher import Pitcher
from app.prompts import load_prompt
from app.schemas.ai import FaceAnalysisResult
from app.services.hash_fallback import hash_face_scores

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy client initialisation — avoids blowing up on import when no key is set
# ---------------------------------------------------------------------------
_client: Any = None  # anthropic.AsyncAnthropic | None


def _get_client() -> Any:
    global _client
    if _client is None:
        import anthropic  # local import keeps module importable without key

        settings = get_settings()
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PITCHER_IMAGES_DIR = Path(__file__).resolve().parents[3] / "data" / "pitcher_images"


def _build_image_block(profile_photo: str) -> dict[str, Any]:
    """Return an Anthropic image content block for a local path or http(s) URL."""
    if profile_photo.startswith("http://") or profile_photo.startswith("https://"):
        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": profile_photo,
            },
        }

    # Local file — resolve relative to pitcher_images dir or as absolute path
    path = Path(profile_photo)
    if not path.is_absolute():
        path = _PITCHER_IMAGES_DIR / profile_photo

    raw = path.read_bytes()
    b64 = base64.standard_b64encode(raw).decode()

    # Guess media type from extension
    suffix = path.suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_map.get(suffix, "image/jpeg")

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": b64,
        },
    }


def _build_messages(pitcher: Pitcher) -> list[dict[str, Any]]:
    """Compose the user message: image block + user prompt text."""
    _, user_template = load_prompt("face_analysis")

    # User prompt for face analysis has no template variables
    user_text = user_template

    content: list[dict[str, Any]] = []
    if pitcher.profile_photo:
        content.append(_build_image_block(pitcher.profile_photo))
    content.append({"type": "text", "text": user_text})

    return [{"role": "user", "content": content}]


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Claude adds them despite instructions."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _clamp_scores(result: FaceAnalysisResult) -> FaceAnalysisResult:
    """Clamp any out-of-range scores to [0,10] and log a warning."""
    axes = ["command", "stuff", "composure", "dominance", "destiny"]
    changed = False
    for axis in axes:
        axis_score = getattr(result, axis)
        clamped = max(0, min(10, axis_score.score))
        if clamped != axis_score.score:
            logger.warning(
                "face_analyzer: score out of range for axis=%s score=%d — clamped to %d",
                axis,
                axis_score.score,
                clamped,
            )
            axis_score.score = clamped
            changed = True
    return result


async def _call_claude_vision(pitcher: Pitcher, temperature: float = 0.3) -> FaceAnalysisResult:
    """Call Claude Vision and return a parsed FaceAnalysisResult.

    Raises ValueError if JSON parsing fails (caller handles retry/fallback).
    """
    import anthropic

    settings = get_settings()
    client = _get_client()
    system_text, _ = load_prompt("face_analysis")

    messages = _build_messages(pitcher)

    response = await client.messages.create(
        model=settings.claude_model_vision,
        max_tokens=1024,
        temperature=temperature,
        system=[
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )

    # Log token usage
    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    logger.info(
        "face_analyzer: pitcher_id=%d model=%s input_tokens=%d output_tokens=%d cache_read_tokens=%d",
        pitcher.pitcher_id,
        settings.claude_model_vision,
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

    result = FaceAnalysisResult.model_validate(data)
    result = _clamp_scores(result)
    return result


def _build_face_score_from_result(
    pitcher_id: int,
    season: int,
    result: FaceAnalysisResult,
    *,
    is_fallback: bool = False,
) -> FaceScore:
    """Build a FaceScore ORM object from a parsed result."""
    return FaceScore(
        pitcher_id=pitcher_id,
        season=season,
        command=result.command.score,
        stuff=result.stuff.score,
        composure=result.composure.score,
        dominance=result.dominance.score,
        destiny=result.destiny.score,
        command_detail=result.command.detail,
        stuff_detail=result.stuff.detail,
        composure_detail=result.composure.detail,
        dominance_detail=result.dominance.detail,
        destiny_detail=result.destiny.detail,
        overall_impression=result.overall_impression,
        analyzed_at=_now_kst(),
    )


def _build_face_score_from_fallback(
    pitcher_id: int,
    season: int,
) -> FaceScore:
    """Build a FaceScore ORM object from hash fallback scores."""
    scores = hash_face_scores(pitcher_id, season)
    return FaceScore(
        pitcher_id=pitcher_id,
        season=season,
        command=int(scores["command"]),
        stuff=int(scores["stuff"]),
        composure=int(scores["composure"]),
        dominance=int(scores["dominance"]),
        destiny=int(scores["destiny"]),
        command_detail=str(scores["command_detail"]),
        stuff_detail=str(scores["stuff_detail"]),
        composure_detail=str(scores["composure_detail"]),
        dominance_detail=str(scores["dominance_detail"]),
        destiny_detail=str(scores["destiny_detail"]),
        overall_impression=str(scores["overall_impression"]),
        analyzed_at=_now_kst(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_or_create_face_scores(
    session: AsyncSession,
    pitcher: Pitcher,
    season: int = 2026,
) -> FaceScore:
    """Return the cached FaceScore for (pitcher_id, season), creating it if absent.

    Season-fixed per CLAUDE.md §2: once a row exists it is NEVER regenerated.
    """
    # 1. Cache hit — return immediately without any API call
    stmt = select(FaceScore).where(
        FaceScore.pitcher_id == pitcher.pitcher_id,
        FaceScore.season == season,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        logger.debug(
            "face_analyzer: cache hit for pitcher_id=%d season=%d",
            pitcher.pitcher_id,
            season,
        )
        return existing

    # 2. No photo — skip Claude entirely, use hash fallback
    if not pitcher.profile_photo:
        logger.warning(
            "face_analyzer: pitcher_id=%d has no profile_photo — using hash fallback",
            pitcher.pitcher_id,
        )
        face_score = _build_face_score_from_fallback(pitcher.pitcher_id, season)
        session.add(face_score)
        await session.commit()
        await session.refresh(face_score)
        return face_score

    # 3. Call Claude Vision
    face_score_obj: FaceScore | None = None

    try:
        parsed = await _call_claude_vision(pitcher, temperature=0.3)
        face_score_obj = _build_face_score_from_result(pitcher.pitcher_id, season, parsed)
    except Exception as first_exc:
        logger.warning(
            "face_analyzer: first attempt failed for pitcher_id=%d — %s. Retrying with temperature=0.",
            pitcher.pitcher_id,
            first_exc,
        )
        try:
            parsed = await _call_claude_vision(pitcher, temperature=0.0)
            face_score_obj = _build_face_score_from_result(pitcher.pitcher_id, season, parsed)
        except Exception as second_exc:
            logger.error(
                "face_analyzer: second attempt also failed for pitcher_id=%d — %s. Using hash fallback.",
                pitcher.pitcher_id,
                second_exc,
            )
            face_score_obj = _build_face_score_from_fallback(pitcher.pitcher_id, season)

    session.add(face_score_obj)
    await session.commit()
    await session.refresh(face_score_obj)
    return face_score_obj
