from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class FortuneScore(Base):
    __tablename__ = "fortune_scores"
    __table_args__ = (
        UniqueConstraint("pitcher_id", "game_date", name="uq_fortune_pitcher_date"),
    )

    fortune_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pitcher_id: Mapped[int] = mapped_column(
        ForeignKey("pitchers.pitcher_id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    command: Mapped[int] = mapped_column(Integer, nullable=False)
    stuff: Mapped[int] = mapped_column(Integer, nullable=False)
    composure: Mapped[int] = mapped_column(Integer, nullable=False)
    dominance: Mapped[int] = mapped_column(Integer, nullable=False)
    destiny: Mapped[int] = mapped_column(Integer, nullable=False)

    command_reading: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    stuff_reading: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    composure_reading: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    dominance_reading: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    destiny_reading: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    daily_summary: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    lucky_inning: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    pitcher: Mapped["Pitcher"] = relationship(back_populates="fortune_scores")  # noqa: F821
