from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Matchup(Base):
    __tablename__ = "matchups"

    matchup_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    home_team: Mapped[str] = mapped_column(String(8), nullable=False)
    away_team: Mapped[str] = mapped_column(String(8), nullable=False)
    stadium: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    home_pitcher_id: Mapped[int] = mapped_column(
        ForeignKey("pitchers.pitcher_id", ondelete="RESTRICT"), nullable=False
    )
    away_pitcher_id: Mapped[int] = mapped_column(
        ForeignKey("pitchers.pitcher_id", ondelete="RESTRICT"), nullable=False
    )

    chemistry_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
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
