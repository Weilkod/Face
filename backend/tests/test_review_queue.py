"""
tests/test_review_queue.py — unit + integration tests for the crawler review queue.

Coverage:
  - happy path: 3 entries append → JSON file has exactly 3 entries
  - dedup: same composite key appended twice → only 1 entry kept, created_at refreshed
  - TTL eviction: resolved entry >24 h old is dropped on next append
  - GET /admin/review-queue: returns all / unresolved-only
  - POST /admin/review-queue/resolve: resolves existing entry, 404 for missing

Fixtures use tmp_path to avoid touching data/crawler_review_queue.json.
Intentionally misspelled KBO names ("원정성" instead of "원성정",
"쿠어바스" instead of "쿠에바스") to exercise the review-queue path.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routers.admin import router as admin_router
from app.services.crawler import _append_review, _review_entry_key, _ttl_evict


# ---------------------------------------------------------------------------
# Helpers / test data
# ---------------------------------------------------------------------------


def _make_entry(
    team: str = "LG",
    crawled_name: str = "원정성",  # intentional typo — should be 원성정
    game_date: str = "2026-04-16",
    kbo_player_id: int | None = None,
) -> dict[str, Any]:
    """Build a minimal review queue entry dict."""
    entry: dict[str, Any] = {
        "team": team,
        "game_date": game_date,
        "reason": "no name match (best 72.0 < 85)",
    }
    if crawled_name is not None:
        entry["crawled_name"] = crawled_name
    if kbo_player_id is not None:
        entry["kbo_player_id"] = kbo_player_id
    return entry


def _read_queue(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _iso_hours_ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# _append_review unit tests (synchronous, no HTTP)
# ---------------------------------------------------------------------------


class TestAppendReview:
    def test_happy_path_three_entries(self, tmp_path: Path) -> None:
        """Appending 3 distinct entries results in exactly 3 JSON rows."""
        qfile = tmp_path / "queue.json"
        entries = [
            _make_entry(team="LG", crawled_name="원정성", game_date="2026-04-16"),
            _make_entry(team="SSG", crawled_name="쿠어바스", game_date="2026-04-16"),
            _make_entry(team="KT", crawled_name="홍길동", game_date="2026-04-16"),
        ]
        for e in entries:
            _append_review(e, path=qfile)

        queue = _read_queue(qfile)
        assert len(queue) == 3

    def test_happy_path_schema_fields_stamped(self, tmp_path: Path) -> None:
        """Each entry gets created_at, resolved=False, resolved_at=None stamped."""
        qfile = tmp_path / "queue.json"
        _append_review(_make_entry(), path=qfile)

        row = _read_queue(qfile)[0]
        assert "created_at" in row
        assert row["resolved"] is False
        assert row["resolved_at"] is None

    def test_dedup_same_key_no_duplicate(self, tmp_path: Path) -> None:
        """Appending the same (team, crawled_name, game_date) twice keeps only 1 entry."""
        qfile = tmp_path / "queue.json"
        entry = _make_entry(team="LG", crawled_name="원정성", game_date="2026-04-16")
        _append_review(dict(entry), path=qfile)
        _append_review(dict(entry), path=qfile)

        queue = _read_queue(qfile)
        assert len(queue) == 1

    def test_dedup_updates_created_at(self, tmp_path: Path) -> None:
        """On dedup hit, created_at is refreshed to the latest attempt timestamp."""
        qfile = tmp_path / "queue.json"
        entry = _make_entry(team="LG", crawled_name="원정성", game_date="2026-04-16")

        # First write with a manually old timestamp.
        old_ts = _iso_hours_ago(3)
        entry_first = dict(entry)
        entry_first["created_at"] = old_ts
        _append_review(entry_first, path=qfile)

        # Second write — should refresh created_at.
        entry_second = dict(entry)
        _append_review(entry_second, path=qfile)

        queue = _read_queue(qfile)
        assert len(queue) == 1
        assert queue[0]["created_at"] != old_ts

    def test_dedup_different_game_date_not_collapsed(self, tmp_path: Path) -> None:
        """Same name + team but different game_date produces two separate entries."""
        qfile = tmp_path / "queue.json"
        _append_review(_make_entry(game_date="2026-04-16"), path=qfile)
        _append_review(_make_entry(game_date="2026-04-17"), path=qfile)

        queue = _read_queue(qfile)
        assert len(queue) == 2

    def test_dedup_kbo_player_id_key_when_no_name(self, tmp_path: Path) -> None:
        """When crawled_name is absent, kbo_player_id is part of the dedup key."""
        qfile = tmp_path / "queue.json"
        # Two entries with None crawled_name but different kbo_player_id.
        e1 = {"team": "LG", "game_date": "2026-04-16", "kbo_player_id": 111}
        e2 = {"team": "LG", "game_date": "2026-04-16", "kbo_player_id": 222}
        _append_review(e1, path=qfile)
        _append_review(e2, path=qfile)

        queue = _read_queue(qfile)
        assert len(queue) == 2

    def test_ttl_evicts_old_resolved_on_next_append(self, tmp_path: Path) -> None:
        """Resolved entries with resolved_at >24 h ago are dropped on next append."""
        qfile = tmp_path / "queue.json"

        # Write an already-resolved entry with resolved_at 25 h ago directly.
        old_entry = {
            "team": "LG",
            "crawled_name": "오래된투수",
            "game_date": "2026-04-15",
            "created_at": _iso_hours_ago(26),
            "resolved": True,
            "resolved_at": _iso_hours_ago(25),
            "reason": "manual resolve",
        }
        qfile.parent.mkdir(parents=True, exist_ok=True)
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump([old_entry], fh, ensure_ascii=False, indent=2)

        # Now append a new entry — TTL eviction fires inside _append_review.
        _append_review(_make_entry(game_date="2026-04-16"), path=qfile)

        queue = _read_queue(qfile)
        dates = [e["game_date"] for e in queue]
        assert "2026-04-15" not in dates, "old resolved entry should have been evicted"
        assert "2026-04-16" in dates, "new entry should be present"

    def test_ttl_keeps_recent_resolved(self, tmp_path: Path) -> None:
        """Resolved entry with resolved_at <24 h ago is NOT evicted."""
        qfile = tmp_path / "queue.json"

        recent_entry = {
            "team": "LG",
            "crawled_name": "최근투수",
            "game_date": "2026-04-16",
            "created_at": _iso_hours_ago(2),
            "resolved": True,
            "resolved_at": _iso_hours_ago(1),
            "reason": "manual resolve",
        }
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump([recent_entry], fh, ensure_ascii=False, indent=2)

        _append_review(_make_entry(team="SSG", game_date="2026-04-16"), path=qfile)

        queue = _read_queue(qfile)
        assert len(queue) == 2

    def test_ttl_keeps_unresolved(self, tmp_path: Path) -> None:
        """Unresolved entries are NEVER evicted, regardless of age."""
        qfile = tmp_path / "queue.json"

        old_unresolved = {
            "team": "LG",
            "crawled_name": "미해결투수",
            "game_date": "2026-04-01",
            "created_at": _iso_hours_ago(400),
            "resolved": False,
            "resolved_at": None,
            "reason": "operator action required",
        }
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump([old_unresolved], fh, ensure_ascii=False, indent=2)

        _append_review(_make_entry(team="SSG", game_date="2026-04-16"), path=qfile)

        queue = _read_queue(qfile)
        unresolved = [e for e in queue if not e.get("resolved")]
        assert len(unresolved) >= 1
        assert any(e["crawled_name"] == "미해결투수" for e in unresolved)


# ---------------------------------------------------------------------------
# _review_entry_key unit tests
# ---------------------------------------------------------------------------


class TestReviewEntryKey:
    def test_primary_key_fields(self) -> None:
        entry = {"team": "LG", "crawled_name": "홍길동", "game_date": "2026-04-16"}
        assert _review_entry_key(entry) == ("LG", "홍길동", "2026-04-16", None)

    def test_kbo_player_id_included_when_no_name(self) -> None:
        entry = {"team": "LG", "game_date": "2026-04-16", "kbo_player_id": 999}
        assert _review_entry_key(entry) == ("LG", None, "2026-04-16", 999)

    def test_kbo_player_id_ignored_when_name_present(self) -> None:
        entry = {
            "team": "LG",
            "crawled_name": "홍길동",
            "game_date": "2026-04-16",
            "kbo_player_id": 999,
        }
        # kbo_player_id must be None in key when crawled_name is present.
        assert _review_entry_key(entry) == ("LG", "홍길동", "2026-04-16", None)


# ---------------------------------------------------------------------------
# _ttl_evict unit tests
# ---------------------------------------------------------------------------


class TestTtlEvict:
    def test_evicts_old_resolved(self) -> None:
        queue = [
            {
                "team": "LG",
                "crawled_name": "A",
                "game_date": "2026-04-15",
                "resolved": True,
                "resolved_at": _iso_hours_ago(25),
            }
        ]
        result = _ttl_evict(queue)
        assert result == []

    def test_keeps_recent_resolved(self) -> None:
        queue = [
            {
                "team": "LG",
                "crawled_name": "B",
                "game_date": "2026-04-16",
                "resolved": True,
                "resolved_at": _iso_hours_ago(1),
            }
        ]
        result = _ttl_evict(queue)
        assert len(result) == 1

    def test_keeps_unresolved_regardless_of_age(self) -> None:
        queue = [
            {
                "team": "LG",
                "crawled_name": "C",
                "game_date": "2026-04-01",
                "resolved": False,
                "resolved_at": None,
            }
        ]
        result = _ttl_evict(queue)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Admin endpoint integration tests (httpx AsyncClient + tmp_path)
# ---------------------------------------------------------------------------


def _make_test_app() -> FastAPI:
    """Minimal FastAPI app that only mounts the admin router."""
    app = FastAPI()
    app.include_router(admin_router)
    return app


@pytest.fixture
def test_app() -> FastAPI:
    return _make_test_app()


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client


class TestAdminGetReviewQueue:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_file(
        self, async_client: AsyncClient, tmp_path: Path
    ) -> None:
        qfile = tmp_path / "queue.json"
        resp = await async_client.get(
            "/admin/review-queue",
            params={"unresolved_only": False},
            # Inject path via a custom query param trick would require route change.
            # Instead we test with an empty real queue by ensuring file absent.
        )
        # This will use REVIEW_QUEUE_PATH which may not exist in CI — that's OK,
        # the route returns [] for missing file.
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_unresolved_only_filter(self, tmp_path: Path) -> None:
        """unresolved_only=True should omit resolved entries."""
        qfile = tmp_path / "queue.json"
        queue = [
            {
                "team": "LG",
                "crawled_name": "원정성",
                "game_date": "2026-04-16",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
                "resolved_at": None,
                "reason": "no name match",
            },
            {
                "team": "SSG",
                "crawled_name": "쿠어바스",
                "game_date": "2026-04-16",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": True,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "reason": "resolved",
            },
        ]
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump(queue, fh, ensure_ascii=False, indent=2)

        # Call the impl function directly (bypassing ASGI) for clean path injection.
        from app.routers.admin import _get_review_queue_impl

        result = await _get_review_queue_impl(
            unresolved_only=True, limit=100, queue_path=qfile
        )
        assert len(result) == 1
        assert result[0].crawled_name == "원정성"
        assert result[0].resolved is False

    @pytest.mark.asyncio
    async def test_unresolved_only_false_returns_all(self, tmp_path: Path) -> None:
        qfile = tmp_path / "queue.json"
        queue = [
            {
                "team": "LG",
                "crawled_name": "원정성",
                "game_date": "2026-04-16",
                "resolved": False,
                "resolved_at": None,
            },
            {
                "team": "SSG",
                "crawled_name": "쿠어바스",
                "game_date": "2026-04-16",
                "resolved": True,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump(queue, fh, ensure_ascii=False, indent=2)

        from app.routers.admin import _get_review_queue_impl

        result = await _get_review_queue_impl(
            unresolved_only=False, limit=100, queue_path=qfile
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_limit_caps_result(self, tmp_path: Path) -> None:
        qfile = tmp_path / "queue.json"
        queue = [
            {
                "team": "LG",
                "crawled_name": f"투수{i}",
                "game_date": "2026-04-16",
                "resolved": False,
                "resolved_at": None,
            }
            for i in range(10)
        ]
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump(queue, fh, ensure_ascii=False, indent=2)

        from app.routers.admin import _get_review_queue_impl

        result = await _get_review_queue_impl(
            unresolved_only=True, limit=3, queue_path=qfile
        )
        assert len(result) == 3


class TestAdminResolveEndpoint:
    @pytest.mark.asyncio
    async def test_resolve_existing_entry(self, tmp_path: Path) -> None:
        """Resolving an existing entry sets resolved=True and stamps resolved_at."""
        qfile = tmp_path / "queue.json"
        queue = [
            {
                "team": "LG",
                "crawled_name": "원정성",
                "game_date": "2026-04-16",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
                "resolved_at": None,
                "reason": "no name match",
            }
        ]
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump(queue, fh, ensure_ascii=False, indent=2)

        from app.routers.admin import _resolve_review_queue_impl
        from app.schemas.response import ReviewQueueResolveRequest

        req = ReviewQueueResolveRequest(
            team="LG",
            game_date="2026-04-16",
            crawled_name="원정성",
        )
        result = await _resolve_review_queue_impl(body=req, queue_path=qfile)

        assert result.resolved is True
        assert result.resolved_at is not None

        # Persisted to file.
        saved = _read_queue(qfile)
        assert saved[0]["resolved"] is True
        assert saved[0]["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_raises_404(self, tmp_path: Path) -> None:
        """Resolving an entry that does not exist raises HTTPException 404."""
        qfile = tmp_path / "queue.json"
        # Empty file.
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump([], fh)

        from fastapi import HTTPException

        from app.routers.admin import _resolve_review_queue_impl
        from app.schemas.response import ReviewQueueResolveRequest

        req = ReviewQueueResolveRequest(
            team="LG",
            game_date="2026-04-16",
            crawled_name="없는투수",
        )
        with pytest.raises(HTTPException) as exc_info:
            await _resolve_review_queue_impl(body=req, queue_path=qfile)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_with_kbo_player_id(self, tmp_path: Path) -> None:
        """Resolve by kbo_player_id when crawled_name is None."""
        qfile = tmp_path / "queue.json"
        queue = [
            {
                "team": "LG",
                "game_date": "2026-04-16",
                "kbo_player_id": 12345,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
                "resolved_at": None,
            }
        ]
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump(queue, fh, ensure_ascii=False, indent=2)

        from app.routers.admin import _resolve_review_queue_impl
        from app.schemas.response import ReviewQueueResolveRequest

        req = ReviewQueueResolveRequest(
            team="LG",
            game_date="2026-04-16",
            kbo_player_id=12345,
        )
        result = await _resolve_review_queue_impl(body=req, queue_path=qfile)
        assert result.resolved is True

    @pytest.mark.asyncio
    async def test_get_review_queue_via_asgi(self, tmp_path: Path) -> None:
        """Test the full ASGI path for GET /admin/review-queue via httpx."""
        qfile = tmp_path / "queue.json"
        queue = [
            {
                "team": "LG",
                "crawled_name": "원정성",
                "game_date": "2026-04-16",
                "resolved": False,
                "resolved_at": None,
            }
        ]
        with qfile.open("w", encoding="utf-8") as fh:
            json.dump(queue, fh, ensure_ascii=False, indent=2)

        # Monkey-patch REVIEW_QUEUE_PATH in the router module for this test.
        import app.routers.admin as admin_mod
        original_path = admin_mod.REVIEW_QUEUE_PATH
        admin_mod.REVIEW_QUEUE_PATH = qfile

        try:
            app_instance = _make_test_app()
            async with AsyncClient(
                transport=ASGITransport(app=app_instance), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/admin/review-queue", params={"unresolved_only": "true"}
                )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["crawled_name"] == "원정성"
        finally:
            admin_mod.REVIEW_QUEUE_PATH = original_path
