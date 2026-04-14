"""Initialize the FACEMETRICS DB by running Alembic migrations to head.

Usage (from repo root):
    python scripts/init_db.py

This replaces the old `Base.metadata.create_all` bootstrap. Alembic is now
the single source of truth for schema; never call `create_all` against the
real DB or migration history will get out of sync.

For a brand-new dev DB this command is sufficient — it will create every
table defined in `backend/alembic/versions/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    print(f"[init_db] running alembic upgrade head against {settings.database_url}")
    command.upgrade(alembic_cfg, "head")
    print("[init_db] migrations applied")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    main()
