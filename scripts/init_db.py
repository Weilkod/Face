"""Create all tables for the FACEMETRICS dev SQLite DB.

Usage (from repo root, with backend/ on PYTHONPATH):
    python scripts/init_db.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401  (register mappers)


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"[init_db] tables created on {engine.url}")
    print(f"[init_db] registered tables: {sorted(Base.metadata.tables)}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    asyncio.run(main())
