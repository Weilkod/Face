"""Seed the `pitchers` table from data/pitchers_2026.json.

Computes chinese_zodiac / zodiac_sign / zodiac_element from birth_date, and
resolves profile_photo from data/pitcher_images/manifest.json (KBO source
preferred, namuwiki as fallback).

Idempotent — existing rows (matched by (name, team)) are updated in place.

Prerequisite: the DB schema must already exist. Run `python scripts/init_db.py`
first so Alembic applies `upgrade head`. This script intentionally does NOT
call `Base.metadata.create_all` — Alembic is the single source of truth for
schema and bypassing it would leave `alembic_version` un-stamped.

Usage (from repo root):
    python scripts/init_db.py        # once, to create tables
    python scripts/seed_pitchers.py  # baseline seed from JSON

    # A-6 eager harvester (opt-in) — talks to koreabaseball.com and fills
    # `kbo_player_id` for any seeded pitcher whose slot is still NULL.
    # Rate-limited at 1 req/sec per host, so expect ~2s per pitcher.
    python scripts/seed_pitchers.py --harvest
    python scripts/seed_pitchers.py --harvest --dry-run
    python scripts/seed_pitchers.py --harvest --pitcher-id 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402,F401
from app.models import Pitcher  # noqa: E402


DATA_DIR = PROJECT_ROOT / "data"
PITCHERS_PATH = DATA_DIR / "pitchers_2026.json"
CONSTELLATIONS_PATH = DATA_DIR / "constellation_elements.json"
MANIFEST_PATH = DATA_DIR / "pitcher_images" / "manifest.json"

# (year - 1900) % 12 → zodiac index. 1900 was 자(rat).
CHINESE_ZODIAC = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]


def chinese_zodiac_for(birth: date) -> str:
    return CHINESE_ZODIAC[(birth.year - 1900) % 12]


def _mmdd(s: str) -> tuple[int, int]:
    m, d = s.split("-")
    return int(m), int(d)


def zodiac_sign_for(birth: date, signs: list[dict]) -> dict:
    """Pick the constellation whose [start, end] window contains `birth` (MM-DD).

    Handles the Capricorn year-wrap (12-22 → 01-19).
    """
    mm, dd = birth.month, birth.day
    for sign in signs:
        sm, sd = _mmdd(sign["start"])
        em, ed = _mmdd(sign["end"])
        if sm <= em:
            if (mm, dd) >= (sm, sd) and (mm, dd) <= (em, ed):
                return sign
        else:
            # wrap: e.g. 12-22 .. 01-19
            if (mm, dd) >= (sm, sd) or (mm, dd) <= (em, ed):
                return sign
    raise ValueError(f"no zodiac sign matched for {birth}")


def load_manifest_photo_map() -> dict[int, str]:
    """Map manifest_index → repo-relative profile photo path.

    Prefer KBO source (official), fall back to namuwiki.
    """
    if not MANIFEST_PATH.exists():
        return {}
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_index_kbo: dict[int, str] = {}
    by_index_namu: dict[int, str] = {}
    for row in data.get("success", []):
        idx = row.get("index")
        src = row.get("source")
        file_ = row.get("file")
        if idx is None or not file_:
            continue
        if src == "kbo":
            by_index_kbo[idx] = file_
        elif src == "namuwiki":
            by_index_namu[idx] = file_
    merged: dict[int, str] = dict(by_index_namu)
    merged.update(by_index_kbo)  # KBO overrides namuwiki
    return merged


async def _harvest_missing_kbo_ids(
    session,
    pitcher_id_filter: int | None = None,
) -> dict[str, int]:
    """Fill `pitcher.kbo_player_id` (and profile_photo if empty) by calling
    the KBO player search site. Opt-in path; caller flushes the session."""
    from app.services.crawler import _make_client
    from app.services.kbo_profile_harvester import harvest_profile

    stmt = select(Pitcher)
    if pitcher_id_filter is not None:
        stmt = stmt.where(Pitcher.pitcher_id == pitcher_id_filter)
    all_pitchers = list((await session.execute(stmt)).scalars().all())

    counts = {"hit": 0, "miss": 0, "skipped": 0, "photo_filled": 0}

    async with _make_client() as client:
        for p in all_pitchers:
            if p.kbo_player_id is not None:
                counts["skipped"] += 1
                print(
                    f"[harvest] skip {p.name} ({p.team}): already has kbo_id={p.kbo_player_id}"
                )
                continue

            result = await harvest_profile(client, p.name, p.team)
            if result is None:
                counts["miss"] += 1
                print(f"[harvest] MISS {p.name} ({p.team}): no KBO match")
                continue

            p.kbo_player_id = result.kbo_player_id
            counts["hit"] += 1
            if result.profile_photo_url and not p.profile_photo:
                p.profile_photo = result.profile_photo_url
                counts["photo_filled"] += 1
                print(
                    f"[harvest] HIT  {p.name} ({p.team}): kbo_id={result.kbo_player_id} + photo"
                )
            else:
                print(
                    f"[harvest] HIT  {p.name} ({p.team}): kbo_id={result.kbo_player_id}"
                )

    return counts


async def main(args: argparse.Namespace) -> int:
    raw = json.loads(PITCHERS_PATH.read_text(encoding="utf-8"))
    pitchers_data = raw["pitchers"]
    season = raw["_meta"]["season"]

    signs = json.loads(CONSTELLATIONS_PATH.read_text(encoding="utf-8"))["signs"]
    photo_map = load_manifest_photo_map()

    inserted = 0
    updated = 0
    async with SessionLocal() as session:
        for row in pitchers_data:
            name: str = row["name"]
            team: str = row["team"]
            birth = date.fromisoformat(row["birth_date"])
            sign = zodiac_sign_for(birth, signs)
            cz = chinese_zodiac_for(birth)
            idx = row.get("manifest_index")
            photo = photo_map.get(idx) if idx is not None else None

            existing = (
                await session.execute(
                    select(Pitcher).where(Pitcher.name == name, Pitcher.team == team)
                )
            ).scalar_one_or_none()

            if existing is None:
                session.add(
                    Pitcher(
                        name=name,
                        name_en=row.get("name_en"),
                        team=team,
                        birth_date=birth,
                        chinese_zodiac=cz,
                        zodiac_sign=sign["name"],
                        zodiac_element=sign["element"],
                        blood_type=row.get("blood_type"),
                        profile_photo=photo,
                    )
                )
                inserted += 1
            else:
                existing.name_en = row.get("name_en")
                existing.birth_date = birth
                existing.chinese_zodiac = cz
                existing.zodiac_sign = sign["name"]
                existing.zodiac_element = sign["element"]
                existing.blood_type = row.get("blood_type")
                if photo:
                    existing.profile_photo = photo
                updated += 1

        # Flush JSON upserts before the harvest pass so the harvester sees the
        # latest `kbo_player_id` state (including any NULLs that the JSON seed
        # just created for new rows).
        await session.flush()

        harvest_counts = None
        if args.harvest:
            print("[harvest] starting KBO eager harvester...")
            harvest_counts = await _harvest_missing_kbo_ids(
                session,
                pitcher_id_filter=args.pitcher_id,
            )

        if args.dry_run:
            await session.rollback()
            print("[seed_pitchers] --dry-run: rolled back, no rows written")
        else:
            await session.commit()

    print(
        f"[seed_pitchers] season={season} inserted={inserted} updated={updated}"
    )
    print(f"[seed_pitchers] db url: {engine.url}")
    print(f"[seed_pitchers] photos wired from manifest: {len(photo_map)}")
    if harvest_counts is not None:
        print(
            "[harvest] summary: "
            f"hit={harvest_counts['hit']} "
            f"miss={harvest_counts['miss']} "
            f"skipped={harvest_counts['skipped']} "
            f"photo_filled={harvest_counts['photo_filled']}"
        )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the pitchers table from JSON.")
    parser.add_argument(
        "--harvest",
        action="store_true",
        help=(
            "After seeding, talk to koreabaseball.com/Player/Search.aspx and "
            "fill pitcher.kbo_player_id (and profile_photo if empty) for any "
            "row whose id slot is still NULL. Opt-in — omit to preserve the "
            "original offline seed behavior (CI / test environments)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Roll back all DB writes at the end. Useful with --harvest to "
        "preview what would be filled without mutating dev state.",
    )
    parser.add_argument(
        "--pitcher-id",
        type=int,
        default=None,
        help="Restrict the harvest pass to a single pitcher_id (debugging).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    raise SystemExit(asyncio.run(main(parse_args())))
