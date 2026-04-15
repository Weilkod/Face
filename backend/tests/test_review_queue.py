"""C-1 — `_append_review` dedup + concurrency.

이 테스트는 두 가지 regression 을 막는다:

1. 같은 `(date, team, crawled_name)` 에 대해 `_append_review` 를 여러 번 호출해도
   JSON queue 에 한 번만 들어가야 한다 (dedup).

2. 여러 coroutine 이 동시에 `_append_review` 를 호출해도 read-modify-write race 로
   인한 유실이 없어야 한다 — `_review_queue_lock` 가 critical section 을 직렬화한다.

Review queue 파일은 tmp_path 로 monkeypatch 해서 실제 `data/crawler_review_queue.json`
을 건드리지 않는다.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest

from app.services import crawler as crawler_module


@pytest.fixture
def tmp_review_path(tmp_path, monkeypatch):
    """Redirect the review queue to a tmp file for the duration of the test."""
    path = tmp_path / "review_queue.json"
    monkeypatch.setattr(crawler_module, "REVIEW_QUEUE_PATH", path)
    return path


@pytest.mark.asyncio
async def test_append_review_dedups_on_date_team_name(tmp_review_path):
    """같은 (date, team, crawled_name) 은 최초 1회만 queue 에 남는다."""
    entry_a = {
        "date": "2026-04-14",
        "team": "LG",
        "crawled_name": "임찬규",
        "reason": "no name match (best 70.0 < 85)",
        "queued_at": "2026-04-14T08:00:00+09:00",
    }
    # 정확히 동일 키의 두 번째 호출 — queued_at 이 달라도 dedup 되어야 함
    entry_a_dup = {
        **entry_a,
        "queued_at": "2026-04-14T10:30:00+09:00",
        "reason": "later call, same key",
    }
    # 다른 날짜 → 별개 엔트리
    entry_b = {**entry_a, "date": "2026-04-15"}
    # 다른 팀 → 별개 엔트리
    entry_c = {**entry_a, "team": "KT"}

    await crawler_module._append_review(entry_a)
    await crawler_module._append_review(entry_a_dup)
    await crawler_module._append_review(entry_b)
    await crawler_module._append_review(entry_c)
    await crawler_module._append_review(entry_a)  # 또 한 번 dedup

    data = json.loads(tmp_review_path.read_text(encoding="utf-8"))
    assert len(data) == 3, f"dedup 실패 — 예상 3, 실제 {len(data)}: {data}"

    keys = {(d["date"], d["team"], d["crawled_name"]) for d in data}
    assert keys == {
        ("2026-04-14", "LG", "임찬규"),
        ("2026-04-15", "LG", "임찬규"),
        ("2026-04-14", "KT", "임찬규"),
    }

    # 가장 먼저 들어온 entry_a 가 유지되어야 한다 (late-call 덮어쓰기 금지)
    first = next(d for d in data if d["date"] == "2026-04-14" and d["team"] == "LG")
    assert first["queued_at"] == "2026-04-14T08:00:00+09:00"
    assert first["reason"].startswith("no name match")


@pytest.mark.asyncio
async def test_append_review_concurrent_no_lost_updates(tmp_review_path):
    """동시 호출 시 lock 덕분에 append 가 유실되지 않아야 한다.

    20 개의 서로 다른 키를 `asyncio.gather` 로 동시에 호출한다. Lock 이 없으면
    read-modify-write race 로 일부 append 가 유실될 수 있다.
    """
    async def append(i: int) -> None:
        await crawler_module._append_review({
            "date": "2026-04-14",
            "team": "LG",
            "crawled_name": f"투수_{i:02d}",
            "reason": "concurrent test",
            "queued_at": "2026-04-14T08:00:00+09:00",
        })

    await asyncio.gather(*(append(i) for i in range(20)))

    data = json.loads(tmp_review_path.read_text(encoding="utf-8"))
    assert len(data) == 20, f"concurrent append 유실 — 예상 20, 실제 {len(data)}"

    names = {d["crawled_name"] for d in data}
    assert names == {f"투수_{i:02d}" for i in range(20)}


@pytest.mark.asyncio
async def test_match_pitcher_name_append_is_awaited(tmp_review_path):
    """match_pitcher_name 이 dedup 호출을 `await` 로 호출하는지 스모크 테스트.

    같은 이름으로 두 번 연속 호출해도 review queue 에 1건만 남아야 한다.
    이는 `_append_review` 가 async 로 변경된 후 호출부가 빠짐없이 `await` 로
    수정되었는지 확인한다.
    """
    from app.db import Base, SessionLocal, engine
    from app.models import Pitcher

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(Pitcher(
            pitcher_id=1, name="원태인", team="SAM",
            birth_date=date(2000, 4, 6),
            chinese_zodiac="진", zodiac_sign="양자리", zodiac_element="불",
            profile_photo="https://example.com/face1.jpg",
        ))
        await session.commit()

    # 존재하지 않는 이름 → review queue 에 append
    async with SessionLocal() as session:
        pid1 = await crawler_module.match_pitcher_name(
            session, "존재하지않는투수XYZ", "SAM", game_date=date(2026, 4, 14)
        )
        pid2 = await crawler_module.match_pitcher_name(
            session, "존재하지않는투수XYZ", "SAM", game_date=date(2026, 4, 14)
        )

    assert pid1 is None
    assert pid2 is None

    data = json.loads(tmp_review_path.read_text(encoding="utf-8"))
    assert len(data) == 1, f"dedup 미동작 — 예상 1, 실제 {len(data)}: {data}"
    assert data[0]["crawled_name"] == "존재하지않는투수XYZ"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
