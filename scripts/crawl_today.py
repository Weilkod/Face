"""
scripts/crawl_today.py — CLI entrypoint for Phase 3 crawler verification.

Usage:
    # From the repo root:
    python scripts/crawl_today.py
    python scripts/crawl_today.py --date 2026-04-13
    python scripts/crawl_today.py --date 2026-04-13 --loglevel DEBUG
    python scripts/crawl_today.py --write   # persist to daily_schedules

What it does
------------
1. Loads today's date in KST (or the --date override).
2. Calls fetch_today_schedule(game_date).
3. For each ScheduleEntry, calls match_pitcher_name() against the live DB.
4. Prints a formatted summary table.
5. If --write is passed, calls upsert_schedule() to persist the crawled rows
   into the daily_schedules table and prints the insert/update counts.

Without --write this pass is READ-ONLY — nothing is written to the DB.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Bootstrap sys.path so we can import backend/app from the repo root
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Imports (after path fix)
# ---------------------------------------------------------------------------
from app.db import SessionLocal                            # noqa: E402
from app.services.crawler import (                         # noqa: E402
    fetch_today_schedule,
    match_pitcher_name,
    upsert_schedule,
)
from app.schemas.crawler import ScheduleEntry             # noqa: E402

KST = ZoneInfo("Asia/Seoul")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FACEMETRICS — KBO schedule crawler CLI")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Game date in YYYY-MM-DD format (default: today KST)",
    )
    parser.add_argument(
        "--loglevel",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist crawled rows to daily_schedules via upsert_schedule "
             "(default: read-only dry-run).",
    )
    return parser.parse_args()


def _header(label: str) -> None:
    width = 72
    print("\n" + "=" * width)
    print(f"  {label}")
    print("=" * width)


def _row(label: str, value: object) -> None:
    print(f"  {label:<28} {value}")


async def _run(game_date: date, *, write: bool = False) -> None:
    _header(
        f"FACEMETRICS crawler - {game_date.isoformat()} (KST)"
        f"{'  [--write]' if write else '  [dry-run]'}"
    )

    # -----------------------------------------------------------------------
    # Step 1: Fetch schedule
    # -----------------------------------------------------------------------
    print("\n[1] Fetching schedule...")
    entries = await fetch_today_schedule(game_date)

    if not entries:
        print(
            "\n  No games found for this date.  Possible causes:\n"
            "  - All three sources blocked or down.\n"
            "  - No games scheduled (off-day).\n"
            "  - Selectors need updating.\n"
            "  Check logs above for per-source details."
        )
        return

    print(f"  {len(entries)} game(s) found  (source: {entries[0].source})\n")

    # -----------------------------------------------------------------------
    # Step 2: Resolve pitcher names → pitcher_ids
    # -----------------------------------------------------------------------
    print("[2] Resolving pitcher names to DB ids...")

    async with SessionLocal() as session:
        for i, entry in enumerate(entries):
            # Resolve home starter
            if entry.home_starter_name and entry.home_team:
                hid = await match_pitcher_name(
                    session,
                    entry.home_starter_name,
                    entry.home_team,
                    game_date,
                )
                entry.home_pitcher_id = hid
            # Resolve away starter
            if entry.away_starter_name and entry.away_team:
                aid = await match_pitcher_name(
                    session,
                    entry.away_starter_name,
                    entry.away_team,
                    game_date,
                )
                entry.away_pitcher_id = aid

    # -----------------------------------------------------------------------
    # Step 3: Print summary table
    # -----------------------------------------------------------------------
    _header("SUMMARY TABLE")
    col_w = [12, 6, 6, 14, 22, 22, 8, 10]
    headers = ["date", "away", "home", "stadium", "away_pitcher", "home_pitcher", "source", "unknown?"]
    header_line = "  " + "  ".join(h.ljust(w) for h, w in zip(headers, col_w))
    print(header_line)
    print("  " + "-" * (sum(col_w) + 2 * len(col_w)))

    unknowns: list[tuple[str, str]] = []  # (team, name) pairs that didn't resolve

    for entry in entries:
        away_pitcher_str = (
            f"{entry.away_starter_name}(id={entry.away_pitcher_id})"
            if entry.away_starter_name
            else "(TBD)"
        )
        home_pitcher_str = (
            f"{entry.home_starter_name}(id={entry.home_pitcher_id})"
            if entry.home_starter_name
            else "(TBD)"
        )

        unknown_flag = ""
        if entry.away_starter_name and entry.away_pitcher_id is None:
            unknown_flag += "A"
            unknowns.append((entry.away_team, entry.away_starter_name))
        if entry.home_starter_name and entry.home_pitcher_id is None:
            unknown_flag += "H"
            unknowns.append((entry.home_team, entry.home_starter_name))

        cols = [
            entry.game_date.isoformat(),
            entry.away_team,
            entry.home_team,
            (entry.stadium or "")[:14],
            away_pitcher_str[:22],
            home_pitcher_str[:22],
            entry.source,
            unknown_flag or "ok",
        ]
        print("  " + "  ".join(str(c).ljust(w) for c, w in zip(cols, col_w)))

    # -----------------------------------------------------------------------
    # Step 4: Unknown-name report
    # -----------------------------------------------------------------------
    if unknowns:
        _header("UNMATCHED PITCHER NAMES  (added to data/crawler_review_queue.json)")
        for team, name in unknowns:
            print(f"  [{team}] {name}")
        print(
            "\n  Action required: add these pitchers to data/pitchers_2026.json\n"
            "  and re-run python scripts/seed_pitchers.py, then retry this script."
        )
    else:
        print("\n  All pitcher names resolved successfully.")

    # -----------------------------------------------------------------------
    # Step 5: Starter TBD report
    # -----------------------------------------------------------------------
    tbd_games = [
        e for e in entries
        if not e.home_starter_name or not e.away_starter_name
    ]
    if tbd_games:
        _header(f"STARTERS NOT YET ANNOUNCED ({len(tbd_games)} game(s))")
        for e in tbd_games:
            sides = []
            if not e.away_starter_name:
                sides.append(f"away ({e.away_team})")
            if not e.home_starter_name:
                sides.append(f"home ({e.home_team})")
            print(f"  {e.away_team} @ {e.home_team} — {', '.join(sides)} TBD")
        print(
            "\n  Per CLAUDE.md §5: retry at 09:00 and 10:00 KST before giving up.\n"
            "  The scheduler sub-task will wire up the retry loop."
        )

    # -----------------------------------------------------------------------
    # Step 6 (--write only): persist to daily_schedules
    # -----------------------------------------------------------------------
    if write:
        _header("WRITING TO daily_schedules")
        async with SessionLocal() as session:
            counts = await upsert_schedule(session, entries)
        print(
            f"  inserted={counts.get('inserted', 0)}  "
            f"updated={counts.get('updated', 0)}  "
            f"skipped={counts.get('skipped', 0)}"
        )

    _header("DONE")
    print(
        f"  entries={len(entries)}  "
        f"resolved={sum(1 for e in entries if e.home_pitcher_id and e.away_pitcher_id)}  "
        f"tbd_starters={len(tbd_games)}  "
        f"unmatched_names={len(unknowns)}  "
        f"mode={'write' if write else 'dry-run'}"
    )


def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel),
        format="%(levelname)s  %(name)s  %(message)s",
    )

    if args.date:
        try:
            game_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"ERROR: invalid date '{args.date}' — use YYYY-MM-DD format", file=sys.stderr)
            sys.exit(1)
    else:
        game_date = datetime.now(KST).date()

    asyncio.run(_run(game_date, write=args.write))


if __name__ == "__main__":
    main()
