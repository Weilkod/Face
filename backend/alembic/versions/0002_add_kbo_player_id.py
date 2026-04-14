"""add kbo_player_id to pitchers and daily_schedules starter columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-14 00:00:00

A-5: surface the KBO playerId (already returned by GetKboGameList as
T_PIT_P_ID / B_PIT_P_ID) as first-class data.

- `pitchers.kbo_player_id` — unique nullable int. Populated lazily by the
  scheduler when a name-based match succeeds against a daily_schedules row
  that already has a kbo_id. A-6 will add an eager harvester at seed time.
- `daily_schedules.home_starter_kbo_id` / `away_starter_kbo_id` — nullable
  int columns the crawler writes on upsert. Scheduler prefers the id match
  over name fuzzy matching at scoring time.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("pitchers") as batch:
        batch.add_column(sa.Column("kbo_player_id", sa.Integer(), nullable=True))
        batch.create_index(
            "ix_pitchers_kbo_player_id",
            ["kbo_player_id"],
            unique=True,
        )

    with op.batch_alter_table("daily_schedules") as batch:
        batch.add_column(
            sa.Column("home_starter_kbo_id", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column("away_starter_kbo_id", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("daily_schedules") as batch:
        batch.drop_column("away_starter_kbo_id")
        batch.drop_column("home_starter_kbo_id")

    with op.batch_alter_table("pitchers") as batch:
        batch.drop_index("ix_pitchers_kbo_player_id")
        batch.drop_column("kbo_player_id")
