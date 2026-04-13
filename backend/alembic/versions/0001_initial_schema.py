"""initial schema — pitchers, face_scores, fortune_scores, matchups, daily_schedules

Revision ID: 0001
Revises:
Create Date: 2026-04-13 00:00:00

This single migration defines the full FACEMETRICS schema as it stood at the
end of Phase 4 (commit 72a5803). Future schema changes go in new revision
files; never edit this one in place.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pitchers",
        sa.Column("pitcher_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=True),
        sa.Column("team", sa.String(length=8), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("chinese_zodiac", sa.String(length=8), nullable=False),
        sa.Column("zodiac_sign", sa.String(length=16), nullable=False),
        sa.Column("zodiac_element", sa.String(length=8), nullable=False),
        sa.Column("blood_type", sa.String(length=4), nullable=True),
        sa.Column("profile_photo", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("pitcher_id"),
    )
    op.create_index("ix_pitchers_name", "pitchers", ["name"])
    op.create_index("ix_pitchers_team", "pitchers", ["team"])

    op.create_table(
        "face_scores",
        sa.Column("face_score_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pitcher_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("command", sa.Integer(), nullable=False),
        sa.Column("stuff", sa.Integer(), nullable=False),
        sa.Column("composure", sa.Integer(), nullable=False),
        sa.Column("dominance", sa.Integer(), nullable=False),
        sa.Column("destiny", sa.Integer(), nullable=False),
        sa.Column("command_detail", sa.String(length=1024), nullable=True),
        sa.Column("stuff_detail", sa.String(length=1024), nullable=True),
        sa.Column("composure_detail", sa.String(length=1024), nullable=True),
        sa.Column("dominance_detail", sa.String(length=1024), nullable=True),
        sa.Column("destiny_detail", sa.String(length=1024), nullable=True),
        sa.Column("overall_impression", sa.String(length=1024), nullable=True),
        sa.Column(
            "analyzed_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pitcher_id"], ["pitchers.pitcher_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("face_score_id"),
        sa.UniqueConstraint("pitcher_id", "season", name="uq_face_pitcher_season"),
    )
    op.create_index("ix_face_scores_pitcher_id", "face_scores", ["pitcher_id"])

    op.create_table(
        "fortune_scores",
        sa.Column("fortune_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pitcher_id", sa.Integer(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("command", sa.Integer(), nullable=False),
        sa.Column("stuff", sa.Integer(), nullable=False),
        sa.Column("composure", sa.Integer(), nullable=False),
        sa.Column("dominance", sa.Integer(), nullable=False),
        sa.Column("destiny", sa.Integer(), nullable=False),
        sa.Column("command_reading", sa.String(length=1024), nullable=True),
        sa.Column("stuff_reading", sa.String(length=1024), nullable=True),
        sa.Column("composure_reading", sa.String(length=1024), nullable=True),
        sa.Column("dominance_reading", sa.String(length=1024), nullable=True),
        sa.Column("destiny_reading", sa.String(length=1024), nullable=True),
        sa.Column("daily_summary", sa.String(length=1024), nullable=True),
        sa.Column("lucky_inning", sa.Integer(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pitcher_id"], ["pitchers.pitcher_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("fortune_id"),
        sa.UniqueConstraint("pitcher_id", "game_date", name="uq_fortune_pitcher_date"),
    )
    op.create_index("ix_fortune_scores_pitcher_id", "fortune_scores", ["pitcher_id"])
    op.create_index("ix_fortune_scores_game_date", "fortune_scores", ["game_date"])

    op.create_table(
        "matchups",
        sa.Column("matchup_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("home_team", sa.String(length=8), nullable=False),
        sa.Column("away_team", sa.String(length=8), nullable=False),
        sa.Column("stadium", sa.String(length=64), nullable=True),
        sa.Column("home_pitcher_id", sa.Integer(), nullable=False),
        sa.Column("away_pitcher_id", sa.Integer(), nullable=False),
        sa.Column("chemistry_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("home_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("away_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("predicted_winner", sa.String(length=8), nullable=True),
        sa.Column("winner_comment", sa.String(length=512), nullable=True),
        sa.Column("actual_winner", sa.String(length=8), nullable=True),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["home_pitcher_id"], ["pitchers.pitcher_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["away_pitcher_id"], ["pitchers.pitcher_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("matchup_id"),
    )
    op.create_index("ix_matchups_game_date", "matchups", ["game_date"])

    op.create_table(
        "daily_schedules",
        sa.Column("schedule_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("home_team", sa.String(length=8), nullable=False),
        sa.Column("away_team", sa.String(length=8), nullable=False),
        sa.Column("stadium", sa.String(length=64), nullable=True),
        sa.Column("game_time", sa.Time(), nullable=True),
        sa.Column("home_starter", sa.String(length=64), nullable=True),
        sa.Column("away_starter", sa.String(length=64), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column(
            "crawled_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("schedule_id"),
    )
    op.create_index("ix_daily_schedules_game_date", "daily_schedules", ["game_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_schedules_game_date", table_name="daily_schedules")
    op.drop_table("daily_schedules")

    op.drop_index("ix_matchups_game_date", table_name="matchups")
    op.drop_table("matchups")

    op.drop_index("ix_fortune_scores_game_date", table_name="fortune_scores")
    op.drop_index("ix_fortune_scores_pitcher_id", table_name="fortune_scores")
    op.drop_table("fortune_scores")

    op.drop_index("ix_face_scores_pitcher_id", table_name="face_scores")
    op.drop_table("face_scores")

    op.drop_index("ix_pitchers_team", table_name="pitchers")
    op.drop_index("ix_pitchers_name", table_name="pitchers")
    op.drop_table("pitchers")
