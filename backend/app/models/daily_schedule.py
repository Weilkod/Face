from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DailySchedule(Base):
    __tablename__ = "daily_schedules"

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    home_team: Mapped[str] = mapped_column(String(8), nullable=False)
    away_team: Mapped[str] = mapped_column(String(8), nullable=False)
    stadium: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    game_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    home_starter: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    away_starter: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # KBO 내부 playerId — A-5: ID-우선 매칭을 위해 크롤러가 함께 저장한다.
    home_starter_kbo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_starter_kbo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
