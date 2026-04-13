from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class FaceScore(Base):
    __tablename__ = "face_scores"
    __table_args__ = (
        UniqueConstraint("pitcher_id", "season", name="uq_face_pitcher_season"),
    )

    face_score_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pitcher_id: Mapped[int] = mapped_column(
        ForeignKey("pitchers.pitcher_id", ondelete="CASCADE"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False)

    command: Mapped[int] = mapped_column(Integer, nullable=False)
    stuff: Mapped[int] = mapped_column(Integer, nullable=False)
    composure: Mapped[int] = mapped_column(Integer, nullable=False)
    dominance: Mapped[int] = mapped_column(Integer, nullable=False)
    destiny: Mapped[int] = mapped_column(Integer, nullable=False)

    command_detail: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    stuff_detail: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    composure_detail: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    dominance_detail: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    destiny_detail: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    overall_impression: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    pitcher: Mapped["Pitcher"] = relationship(back_populates="face_scores")  # noqa: F821
