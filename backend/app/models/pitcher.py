from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Pitcher(Base):
    __tablename__ = "pitchers"

    pitcher_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    team: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    chinese_zodiac: Mapped[str] = mapped_column(String(8), nullable=False)
    zodiac_sign: Mapped[str] = mapped_column(String(16), nullable=False)
    zodiac_element: Mapped[str] = mapped_column(String(8), nullable=False)
    blood_type: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    profile_photo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    face_scores: Mapped[list["FaceScore"]] = relationship(  # noqa: F821
        back_populates="pitcher", cascade="all, delete-orphan"
    )
    fortune_scores: Mapped[list["FortuneScore"]] = relationship(  # noqa: F821
        back_populates="pitcher", cascade="all, delete-orphan"
    )
