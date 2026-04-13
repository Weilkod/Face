"""Seed the `pitchers` table from data/pitchers_2026.json.

Computes chinese_zodiac / zodiac_sign / zodiac_element from birth_date, and
resolves profile_photo from data/pitcher_images/manifest.json (KBO source
preferred, namuwiki as fallback).

Idempotent — existing rows (matched by (name, team)) are updated in place.

A-5 / A-6 extension: if a JSON entry carries a `kbo_player_id` integer field,
it is written to `pitchers.kbo_player_id`.  This enables the ID-primary
matching path in `match_pitcher_by_kbo_id` (crawler.py).

Future --harvest flag (§A-6 TODO): probe
  POST /ws/Player.asmx/GetPlayerInfoList
per team to auto-discover kbo_player_id for every roster member.  The ASMX
endpoint has not yet been verified; implement once confirmed via DevTools.

Usage (from repo root):
    python scripts/seed_pitchers.py
"""
from __future__ import annotations

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

from app.db import SessionLocal, engine, Base  # noqa: E402
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


async def main() -> int:
    raw = json.loads(PITCHERS_PATH.read_text(encoding="utf-8"))
    pitchers_data = raw["pitchers"]
    season = raw["_meta"]["season"]

    signs = json.loads(CONSTELLATIONS_PATH.read_text(encoding="utf-8"))["signs"]
    photo_map = load_manifest_photo_map()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

            kbo_player_id: int | None = row.get("kbo_player_id")

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
                        kbo_player_id=kbo_player_id,
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
                # A-5: set kbo_player_id only when the JSON provides one.
                # Never blank out an existing ID with None from an older JSON entry.
                if kbo_player_id is not None:
                    existing.kbo_player_id = kbo_player_id
                updated += 1
        await session.commit()

    print(f"[seed_pitchers] season={season} inserted={inserted} updated={updated}")
    print(f"[seed_pitchers] db url: {engine.url}")
    print(f"[seed_pitchers] photos wired from manifest: {len(photo_map)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    raise SystemExit(asyncio.run(main()))
