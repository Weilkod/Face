from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Time, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Matchup(Base):
    __tablename__ = "matchups"

    matchup_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    home_team: Mapped[str] = mapped_column(String(8), nullable=False)
    away_team: Mapped[str] = mapped_column(String(8), nullable=False)
    stadium: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Copied from DailySchedule when the matchup row is written so
    # /api/today and /api/history can return the face-value game time
    # without another join. Nullable because the crawl source may omit it.
    game_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Cosmetic series tag ("더블헤더", "개막전", "주말 홈경기" …) — derived
    # at scoring time and persisted so the FE badge is deterministic.
    series_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    home_pitcher_id: Mapped[int] = mapped_column(
        ForeignKey("pitchers.pitcher_id", ondelete="RESTRICT"), nullable=False
    )
    away_pitcher_id: Mapped[int] = mapped_column(
        ForeignKey("pitchers.pitcher_id", ondelete="RESTRICT"), nullable=False
    )

    chemistry_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # One-line playful Korean comment generated from the ChemistryBreakdown
    # at scoring time. Persisted so /api/matchup/{id} is deterministic and
    # cheap to serve.
    chemistry_comment: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    home_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    predicted_winner: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    winner_comment: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    actual_winner: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    # Set True by the 11:00 KST publish job once predictions are final and
    # safe to surface to users. Written rows are invisible to /api/today until
    # this flag flips.
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
