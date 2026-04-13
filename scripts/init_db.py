"""Create all tables for the FACEMETRICS dev SQLite DB.

Usage (from repo root, with backend/ on PYTHONPATH):
    python scripts/init_db.py

Idempotent: create_all is safe on a fresh DB; the sqlite3 ALTER block
below handles existing DBs by adding new columns without touching data.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401  (register mappers)


def _sqlite_alter_if_needed(db_path: Path) -> None:
    """
    Add new columns to existing SQLite tables without losing data.

    SQLite does not support ALTER TABLE ADD COLUMN IF NOT EXISTS, so we
    query PRAGMA table_info first and skip columns that already exist.

    Only runs when db_path is a real file (not :memory:).
    """
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    try:
        # ---- pitchers table ----
        cols_pitchers = {
            row[1] for row in conn.execute("PRAGMA table_info(pitchers)").fetchall()
        }
        if "kbo_player_id" not in cols_pitchers:
            conn.execute("ALTER TABLE pitchers ADD COLUMN kbo_player_id INTEGER UNIQUE")
            conn.commit()
            print("[init_db] ALTER pitchers: added kbo_player_id")

        # ---- daily_schedules table ----
        cols_daily = {
            row[1] for row in conn.execute("PRAGMA table_info(daily_schedules)").fetchall()
        }
        for col, typedef in [
            ("home_starter_kbo_id", "INTEGER"),
            ("away_starter_kbo_id", "INTEGER"),
        ]:
            if col not in cols_daily:
                conn.execute(f"ALTER TABLE daily_schedules ADD COLUMN {col} {typedef}")
                conn.commit()
                print(f"[init_db] ALTER daily_schedules: added {col}")
    finally:
        conn.close()


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"[init_db] tables created on {engine.url}")
    print(f"[init_db] registered tables: {sorted(Base.metadata.tables)}")

    # Apply idempotent column additions to existing SQLite DBs.
    # For PostgreSQL (prod) a proper migration tool (Alembic) handles schema.
    url = str(engine.url)
    if url.startswith("sqlite"):
        # Resolve the file path from the URL: strip driver prefix and query string.
        # e.g. "sqlite+aiosqlite:///./data/facemetrics.db" → "./data/facemetrics.db"
        raw_path = url.split("///", 1)[-1].split("?")[0]
        db_path = (PROJECT_ROOT / raw_path).resolve()
        _sqlite_alter_if_needed(db_path)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    asyncio.run(main())
