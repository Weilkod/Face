"""End-to-end production DB seeding script.

Runs the full manual pipeline that replaces the APScheduler jobs (which are
disabled in production via SCHEDULER_ENABLED=false):

    1. pre-flight : connect to the configured DATABASE_URL, report row counts
    2. seed       : scripts/seed_pitchers.py logic with --harvest (KBO lookup)
    3. crawl      : scripts/crawl_today.py logic with --write (schedule upsert)
    4. score      : app.scheduler.analyze_and_score_matchups (Claude + scoring)
    5. publish    : app.scheduler.publish_matchups (flip is_published=true)
    6. summary    : final row counts so you can verify from the terminal

Designed to be run from a Korean-IP shell against the production Supabase
pooler URL. The Claude Code sandbox cannot reach Supabase:5432, so this
script exists as the handoff surface for the operator.

Environment variables (required):
    DATABASE_URL       postgresql+asyncpg:// Supabase session-pooler URL
    ANTHROPIC_API_KEY  sk-ant-... (only consumed by step 4)

Environment variables (optional):
    GAME_DATE          YYYY-MM-DD  (default: today KST)
    SKIP_HARVEST       "1" to skip step 2's KBO player-id harvest
    SKIP_CRAWL         "1" to skip step 3 (use existing daily_schedules rows)

Usage (from repo root):
    export DATABASE_URL='postgresql+asyncpg://...pooler.supabase.com:5432/postgres'
    export ANTHROPIC_API_KEY='sk-ant-...'
    python scripts/seed_production.py                    # today KST
    python scripts/seed_production.py --date 2026-04-18  # explicit date
    python scripts/seed_production.py --skip-harvest     # pitchers already seeded

Exit codes:
    0  all steps completed (published >= 1 matchup)
    1  a step failed; earlier steps may have committed — re-run is safe
    2  missing environment variable / bad CLI args
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

KST = ZoneInfo("Asia/Seoul")

BANNER_WIDTH = 72


def _banner(title: str) -> None:
    print("\n" + "=" * BANNER_WIDTH)
    print(f"  {title}")
    print("=" * BANNER_WIDTH)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: environment variable {name} is not set", file=sys.stderr)
        sys.exit(2)
    return value


async def _preflight() -> dict[str, int]:
    """Step 1: verify DB connectivity and print baseline row counts."""
    from sqlalchemy import text

    from app.db import engine

    counts: dict[str, int] = {}
    expected = [
        "alembic_version",
        "pitchers",
        "daily_schedules",
        "face_scores",
        "fortune_scores",
        "matchups",
    ]

    async with engine.begin() as conn:
        rows = await conn.execute(
            text(
                "select tablename from pg_tables where schemaname = 'public' "
                "order by tablename"
            )
        )
        present = sorted(row[0] for row in rows)
        missing = [t for t in expected if t not in present]
        if missing:
            print(
                f"ERROR: missing tables {missing} — run `python scripts/init_db.py` first",
                file=sys.stderr,
            )
            sys.exit(1)
        for t in ["pitchers", "daily_schedules", "face_scores", "fortune_scores", "matchups"]:
            r = await conn.execute(text(f"select count(*) from {t}"))
            counts[t] = int(r.scalar() or 0)

    for t, n in counts.items():
        print(f"  {t:<18} {n} row(s)")
    return counts


async def _seed_pitchers(*, harvest: bool) -> None:
    """Step 2: delegate to scripts/seed_pitchers.main()."""
    import argparse as _ap

    sys.path.insert(0, str(SCRIPT_DIR))
    from seed_pitchers import main as seed_main

    ns = _ap.Namespace(harvest=harvest, dry_run=False, pitcher_id=None)
    rc = await seed_main(ns)
    if rc != 0:
        raise RuntimeError(f"seed_pitchers returned {rc}")


async def _crawl_and_write(game_date: date) -> int:
    """Step 3: fetch today's schedule and upsert into daily_schedules.

    Returns the number of schedule entries persisted (insert + update).
    """
    from app.db import SessionLocal
    from app.services.crawler import (
        fetch_today_schedule,
        match_pitcher_name,
        upsert_schedule,
    )

    entries = await fetch_today_schedule(game_date)
    if not entries:
        print(
            "  no games found — KBO returned an empty schedule. "
            "Either an off-day, or the source is temporarily unavailable."
        )
        return 0

    print(f"  {len(entries)} game(s) returned (source: {entries[0].source})")

    async with SessionLocal() as session:
        for entry in entries:
            if entry.home_starter_name and entry.home_team:
                entry.home_pitcher_id = await match_pitcher_name(
                    session, entry.home_starter_name, entry.home_team, game_date,
                )
            if entry.away_starter_name and entry.away_team:
                entry.away_pitcher_id = await match_pitcher_name(
                    session, entry.away_starter_name, entry.away_team, game_date,
                )

    tbd = [
        e for e in entries
        if not e.home_starter_name or not e.away_starter_name
    ]
    unmatched = [
        (e.home_team, e.home_starter_name) for e in entries
        if e.home_starter_name and e.home_pitcher_id is None
    ] + [
        (e.away_team, e.away_starter_name) for e in entries
        if e.away_starter_name and e.away_pitcher_id is None
    ]

    if tbd:
        print(f"  WARN: {len(tbd)} game(s) still have TBD starter(s):")
        for e in tbd:
            side = []
            if not e.home_starter_name:
                side.append(f"home({e.home_team})")
            if not e.away_starter_name:
                side.append(f"away({e.away_team})")
            print(f"    - {e.away_team} @ {e.home_team}: {', '.join(side)}")
        print("    per CLAUDE.md §5, retry at 09:00 / 10:00 / 11:00 KST")

    if unmatched:
        print(f"  WARN: {len(unmatched)} unmatched pitcher name(s):")
        for team, name in unmatched:
            print(f"    - [{team}] {name}")
        print(
            "    add them to data/pitchers_2026.json and re-run this script "
            "with --skip-crawl=0 so the harvester picks them up."
        )

    async with SessionLocal() as session:
        counts = await upsert_schedule(session, entries)
    print(
        f"  upserted: inserted={counts.get('inserted', 0)} "
        f"updated={counts.get('updated', 0)} "
        f"skipped={counts.get('skipped', 0)}"
    )
    return int(counts.get("inserted", 0)) + int(counts.get("updated", 0))


async def _score(game_date: date) -> dict[str, int]:
    """Step 4: delegate to app.scheduler.analyze_and_score_matchups."""
    from app.scheduler import analyze_and_score_matchups

    result = await analyze_and_score_matchups(game_date)
    for k in ("scored", "inserted", "updated", "skipped", "failed"):
        print(f"  {k:<10} {result.get(k, 0)}")
    return result


async def _publish(game_date: date) -> int:
    """Step 5: delegate to app.scheduler.publish_matchups."""
    from app.scheduler import publish_matchups

    n = await publish_matchups(game_date)
    print(f"  published {n} matchup row(s)")
    return n


async def _summary(game_date: date, before: dict[str, int]) -> None:
    """Step 6: final row counts + delta vs pre-flight."""
    from sqlalchemy import text

    from app.db import engine

    async with engine.begin() as conn:
        after: dict[str, int] = {}
        for t in ["pitchers", "daily_schedules", "face_scores", "fortune_scores", "matchups"]:
            r = await conn.execute(text(f"select count(*) from {t}"))
            after[t] = int(r.scalar() or 0)

        r = await conn.execute(
            text(
                "select count(*) from matchups "
                "where game_date = :gd and is_published = true"
            ),
            {"gd": game_date},
        )
        published_today = int(r.scalar() or 0)

    print(f"  game_date               {game_date.isoformat()}")
    print(f"  published_matchups      {published_today}")
    print(f"  {'table':<18} {'before':>8} {'after':>8}  {'delta':>8}")
    for t, n in after.items():
        b = before.get(t, 0)
        delta = n - b
        print(f"  {t:<18} {b:>8} {n:>8}  {delta:+8d}")


async def _run(game_date: date, *, skip_harvest: bool, skip_crawl: bool) -> int:
    _banner(f"[0/6] FACEMETRICS production seed — game_date={game_date.isoformat()}")

    _banner("[1/6] pre-flight: Supabase connectivity + baseline counts")
    before = await _preflight()

    _banner("[2/6] seed pitchers" + ("  (harvest=off)" if skip_harvest else "  (harvest=on)"))
    await _seed_pitchers(harvest=not skip_harvest)

    if not skip_crawl:
        _banner(f"[3/6] crawl KBO schedule — {game_date.isoformat()}")
        await _crawl_and_write(game_date)
    else:
        _banner("[3/6] crawl — SKIPPED (SKIP_CRAWL=1)")

    _banner(f"[4/6] score matchups — Claude API calls (~$1)")
    score_result = await _score(game_date)
    if score_result.get("scored", 0) == 0:
        print(
            "  WARN: 0 matchups scored. Likely causes: no schedule rows for this "
            "date, or all starters unresolved. Publish step will no-op."
        )

    _banner(f"[5/6] publish matchups — flip is_published=true")
    published = await _publish(game_date)

    _banner("[6/6] summary")
    await _summary(game_date, before)

    if published < 1:
        print(
            "\n  WARN: no matchups were published. /api/today will stay empty. "
            "Check the step 3 (crawl) output above for TBD starters or an "
            "off-day response from KBO."
        )
        return 1
    print(f"\n  OK — {published} matchup(s) live for {game_date.isoformat()}.")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="FACEMETRICS end-to-end production seed pipeline."
    )
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="Game date YYYY-MM-DD (default: today KST, or GAME_DATE env var).",
    )
    p.add_argument(
        "--skip-harvest",
        action="store_true",
        help="Skip the KBO player-id harvest pass in step 2.",
    )
    p.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip step 3 — use whatever is already in daily_schedules.",
    )
    p.add_argument(
        "--loglevel",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Root log level (default: INFO).",
    )
    return p.parse_args(argv)


def main() -> int:
    args = _parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel),
        format="%(levelname)s  %(name)s  %(message)s",
    )

    _require_env("DATABASE_URL")
    _require_env("ANTHROPIC_API_KEY")

    date_src = args.date or os.environ.get("GAME_DATE")
    if date_src:
        try:
            game_date = date.fromisoformat(date_src)
        except ValueError:
            print(
                f"ERROR: invalid date '{date_src}' — use YYYY-MM-DD", file=sys.stderr
            )
            return 2
    else:
        game_date = datetime.now(KST).date()

    skip_harvest = args.skip_harvest or os.environ.get("SKIP_HARVEST") == "1"
    skip_crawl = args.skip_crawl or os.environ.get("SKIP_CRAWL") == "1"

    try:
        return asyncio.run(
            _run(game_date, skip_harvest=skip_harvest, skip_crawl=skip_crawl)
        )
    except KeyboardInterrupt:
        print("\n  interrupted", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        logging.exception("seed_production failed: %s", exc)
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
