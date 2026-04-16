"""
routers/admin.py — Admin-only endpoints for FACEMETRICS.

Authentication convention: none currently (small internal tool). Do not
add auth guards here — follow the project convention of adding auth at the
reverse-proxy / network layer when the service goes production.

Endpoints
---------
GET  /admin/review-queue
    Return entries from the crawler review queue.
    Query params:
        unresolved_only : bool = True   — when True, omit resolved entries
        limit           : int = 100     — cap result count

POST /admin/review-queue/resolve
    Toggle resolved=True on a queue entry identified by its composite key.
    Body: ReviewQueueResolveRequest
    Returns 200 with the updated ReviewQueueItem, or 404 if not found.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.schemas.response import ReviewQueueItem, ReviewQueueResolveRequest
from app.services.crawler import REVIEW_QUEUE_PATH, _review_entry_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_queue(path: Path) -> list[dict]:
    """Read the JSON review queue file.  Returns [] on any I/O / parse error."""
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            logger.warning("[admin] review queue file is not a list — treating as empty")
            return []
        return data
    except Exception as exc:  # noqa: BLE001
        logger.error("[admin] failed to read review queue at %s: %s", path, exc)
        return []


def _save_queue(path: Path, queue: list[dict]) -> None:
    """Write the queue list back to the JSON file atomically (best-effort)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(queue, fh, ensure_ascii=False, indent=2)


def _build_request_key(req: ReviewQueueResolveRequest) -> tuple:
    """
    Reconstruct the _review_entry_key tuple from a resolve request body.

    Mirrors the logic in crawler._review_entry_key:
      primary key: (team, crawled_name, game_date)
      when crawled_name is None and kbo_player_id is present: include kbo_player_id
    """
    kbo_player_id = req.kbo_player_id if req.crawled_name is None else None
    return (req.team, req.crawled_name, req.game_date, kbo_player_id)


# ---------------------------------------------------------------------------
# GET /admin/review-queue
# ---------------------------------------------------------------------------


@router.get(
    "/review-queue",
    response_model=list[ReviewQueueItem],
    summary="List crawler review queue entries",
    description=(
        "Return entries from data/crawler_review_queue.json. "
        "By default returns only unresolved entries. "
        "Resolved entries older than 24 h are lazily evicted on each _append_review() call "
        "but NOT on read — this endpoint may briefly surface entries that will be evicted later."
    ),
)
async def get_review_queue(
    unresolved_only: bool = Query(True, description="When True, omit resolved entries"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
) -> list[ReviewQueueItem]:
    return await _get_review_queue_impl(
        unresolved_only=unresolved_only, limit=limit, queue_path=REVIEW_QUEUE_PATH
    )


async def _get_review_queue_impl(
    *,
    unresolved_only: bool,
    limit: int,
    queue_path: Path,
) -> list[ReviewQueueItem]:
    """
    Implementation separated from the route so tests can inject a custom path
    without exposing it as a query parameter.
    """
    queue = _load_queue(queue_path)

    if unresolved_only:
        queue = [e for e in queue if not e.get("resolved", False)]

    queue = queue[:limit]
    return [ReviewQueueItem.model_validate(e) for e in queue]


# ---------------------------------------------------------------------------
# POST /admin/review-queue/resolve
# ---------------------------------------------------------------------------


@router.post(
    "/review-queue/resolve",
    response_model=ReviewQueueItem,
    summary="Resolve (or un-resolve) a review queue entry",
    description=(
        "Find the entry matching (team, crawled_name|kbo_player_id, game_date) "
        "and toggle resolved=True with the current UTC timestamp. "
        "Returns 404 if no matching entry exists."
    ),
)
async def resolve_review_queue_entry(
    body: ReviewQueueResolveRequest,
) -> ReviewQueueItem:
    return await _resolve_review_queue_impl(body=body, queue_path=REVIEW_QUEUE_PATH)


async def _resolve_review_queue_impl(
    *,
    body: ReviewQueueResolveRequest,
    queue_path: Path,
) -> ReviewQueueItem:
    """
    Implementation separated from the route so tests can inject a custom path
    without exposing it as a route parameter.
    """
    queue = _load_queue(queue_path)
    target_key = _build_request_key(body)

    for idx, entry in enumerate(queue):
        if _review_entry_key(entry) == target_key:
            queue[idx]["resolved"] = True
            queue[idx]["resolved_at"] = datetime.now(timezone.utc).isoformat()
            _save_queue(queue_path, queue)
            logger.info(
                "[admin] resolved review entry: team=%s crawled_name=%s date=%s",
                body.team,
                body.crawled_name or body.kbo_player_id,
                body.game_date,
            )
            return ReviewQueueItem.model_validate(queue[idx])

    raise HTTPException(
        status_code=404,
        detail=(
            f"No review queue entry found for "
            f"team={body.team!r}, crawled_name={body.crawled_name!r}, "
            f"kbo_player_id={body.kbo_player_id!r}, game_date={body.game_date!r}"
        ),
    )
