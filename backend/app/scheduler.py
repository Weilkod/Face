"""
backend/app/scheduler.py — APScheduler wiring for the daily FACEMETRICS pipeline.

Five cron jobs run in Asia/Seoul (KST), all on the current day:

  08:00  fetch_and_upsert_schedule       — crawl + upsert daily_schedules
  09:00  retry_missing_starters          — re-crawl only if any starter is NULL
  10:00  retry_missing_starters          — final retry before giving up
  10:30  analyze_and_score_matchups      — for every complete game, run
                                           score_matchup() and write matchups.
                                           FIRST real Claude API exercise.
  11:00  publish_matchups                — flip matchups.is_published = True

Every job function takes an optional `game_date` argument so tests and the
CLI `scripts/crawl_today.py --write` path can invoke them directly against an
arbitrary date. Scheduled triggers omit the argument and the job resolves
`today` in KST on each fire.

Each job opens its own AsyncSession — never share sessions across jobs.
Exceptions inside a job are caught and logged; a broken job should never
take down the scheduler or the FastAPI app.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal
from app.models.daily_schedule import DailySchedule
from app.models.matchup import Matchup
from app.models.pitcher import Pitcher
from app.services.chemistry_calculator import ChemistryBreakdown
from app.services.crawler import (
    fetch_today_schedule,
    match_pitcher_name,
    upsert_schedule,
)
from app.services.scoring_engine import score_matchup

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


def _today_kst() -> date:
    return datetime.now(KST).date()


# ---------------------------------------------------------------------------
# Job 1 — 08:00 KST: fetch + upsert schedule
# ---------------------------------------------------------------------------


async def fetch_and_upsert_schedule(game_date: Optional[date] = None) -> dict[str, int]:
    """08:00 KST: crawl today's KBO schedule and upsert daily_schedules."""
    gd = game_date or _today_kst()
    logger.info("[scheduler] 08:00 fetch_and_upsert_schedule for %s", gd)
    entries = await fetch_today_schedule(gd)
    if not entries:
        logger.warning("[scheduler] 08:00 — no entries returned for %s", gd)
        return {"inserted": 0, "updated": 0, "skipped": 0}

    async with SessionLocal() as session:
        return await upsert_schedule(session, entries)


# ---------------------------------------------------------------------------
# Jobs 2 & 3 — 09:00 / 10:00 KST: retry for missing starters
# ---------------------------------------------------------------------------


async def retry_missing_starters(game_date: Optional[date] = None) -> dict[str, int]:
    """
    09:00 / 10:00 KST: re-crawl ONLY if any row for today still has a NULL
    starter. Upsert is null-safe (see crawler.upsert_schedule) so this will
    fill blanks without overwriting confirmed names.

    Returns upsert counts, or {"skipped": ...} with reason if no retry needed.
    """
    gd = game_date or _today_kst()
    async with SessionLocal() as session:
        stmt = select(DailySchedule).where(
            DailySchedule.game_date == gd,
            (DailySchedule.home_starter.is_(None))
            | (DailySchedule.away_starter.is_(None)),
        )
        tbd_rows = list((await session.execute(stmt)).scalars().all())

    if not tbd_rows:
        logger.info("[scheduler] retry — no TBD starters for %s, skipping", gd)
        return {"inserted": 0, "updated": 0, "skipped": 0}

    logger.info(
        "[scheduler] retry — %d game(s) with TBD starter for %s, re-crawling",
        len(tbd_rows), gd,
    )
    entries = await fetch_today_schedule(gd)
    if not entries:
        logger.warning("[scheduler] retry — crawler still empty for %s", gd)
        return {"inserted": 0, "updated": 0, "skipped": 0}

    async with SessionLocal() as session:
        return await upsert_schedule(session, entries)


# ---------------------------------------------------------------------------
# Job 4 — 10:30 KST: score every complete matchup and write matchups rows
# ---------------------------------------------------------------------------


async def _get_pitcher(session: AsyncSession, pitcher_id: int) -> Optional[Pitcher]:
    stmt = select(Pitcher).where(Pitcher.pitcher_id == pitcher_id)
    return (await session.execute(stmt)).scalar_one_or_none()


def _build_chemistry_comment(
    home_pitcher: Pitcher,
    away_pitcher: Pitcher,
    breakdown: ChemistryBreakdown,
) -> str:
    """Rule-based one-liner summarizing the 상성 breakdown.

    No AI — just the labels and deltas from ChemistryBreakdown. Stable per
    `(home_zodiac, away_zodiac, home_element, away_element)`.
    """
    zodiac_phrase = {
        "삼합": f"{home_pitcher.chinese_zodiac}-{away_pitcher.chinese_zodiac} 삼합(三合)이 기운을 북돋운다",
        "육합": f"{home_pitcher.chinese_zodiac}-{away_pitcher.chinese_zodiac} 육합(六合) 궁합",
        "원진": f"{home_pitcher.chinese_zodiac}-{away_pitcher.chinese_zodiac} 원진(怨嗔) — 미묘한 거슬림",
        "충": f"{home_pitcher.chinese_zodiac}-{away_pitcher.chinese_zodiac} 충(沖) — 정면충돌",
        "중립": f"{home_pitcher.chinese_zodiac}-{away_pitcher.chinese_zodiac} 무색무취의 중립",
        "자기(동일 띠)": f"같은 {home_pitcher.chinese_zodiac}띠 동기 대결",
    }.get(breakdown.zodiac_label, f"{home_pitcher.chinese_zodiac}-{away_pitcher.chinese_zodiac}")

    element_phrase = {
        "동질": f"{home_pitcher.zodiac_element} 원소 동질로 흐름이 맞물린다",
        "상생": f"{home_pitcher.zodiac_element}-{away_pitcher.zodiac_element} 상생(相生) 에너지",
        "상극": f"{home_pitcher.zodiac_element}-{away_pitcher.zodiac_element} 상극(相克) 충돌",
        "중립": f"원소는 {home_pitcher.zodiac_element}·{away_pitcher.zodiac_element}로 무관",
    }.get(breakdown.element_label, "")

    final = breakdown.final
    if final >= 3.5:
        verdict = "오늘은 상성운이 매우 밝다"
    elif final >= 2.5:
        verdict = "상성운이 온기를 더한다"
    elif final >= 1.5:
        verdict = "상성은 한 박자 묵직하게 흐른다"
    else:
        verdict = "상성운은 거칠고 날 선 날"

    return f"{zodiac_phrase}. {element_phrase}. {verdict}."


def _derive_series_label(
    gd: date,
    home_team: str,
    away_team: str,
    schedule_rows_for_date: list[Any],
) -> Optional[str]:
    """Derive a cosmetic series tag from the same-date schedule set.

    Rules (cheap + deterministic):
      - If the SAME (home_team, away_team) pair appears ≥ 2x on this date
        → "더블헤더"
      - If the home team plays ≥ 2 games on this date (regardless of opp)
        → "더블헤더"
      - Weekend home games → "주말 홈경기" (Sat/Sun = 5,6)
      - Otherwise → None
    """
    same_pair = sum(
        1
        for r in schedule_rows_for_date
        if r.home_team == home_team and r.away_team == away_team
    )
    if same_pair >= 2:
        return "더블헤더"

    home_team_games = sum(
        1
        for r in schedule_rows_for_date
        if r.home_team == home_team or r.away_team == home_team
    )
    if home_team_games >= 2:
        return "더블헤더"

    # weekday(): Mon=0 … Sun=6
    if gd.weekday() >= 5:
        return "주말 홈경기"

    return None


async def _upsert_matchup_row(
    session: AsyncSession,
    gd: date,
    home_team: str,
    away_team: str,
    stadium: Optional[str],
    game_time: Optional[time],
    series_label: Optional[str],
    home_pitcher_id: int,
    away_pitcher_id: int,
    home_total: float,
    away_total: float,
    chemistry: float,
    chemistry_comment: Optional[str],
    predicted_winner: str,
    winner_comment: str,
) -> str:
    """Insert or update a matchups row. Returns 'inserted' | 'updated'."""
    stmt = select(Matchup).where(
        Matchup.game_date == gd,
        Matchup.home_pitcher_id == home_pitcher_id,
        Matchup.away_pitcher_id == away_pitcher_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        session.add(
            Matchup(
                game_date=gd,
                home_team=home_team,
                away_team=away_team,
                stadium=stadium,
                game_time=game_time,
                series_label=series_label,
                home_pitcher_id=home_pitcher_id,
                away_pitcher_id=away_pitcher_id,
                chemistry_score=chemistry,
                chemistry_comment=chemistry_comment,
                home_total=int(round(home_total)),
                away_total=int(round(away_total)),
                predicted_winner=predicted_winner,
                winner_comment=winner_comment,
                is_published=False,
            )
        )
        return "inserted"

    existing.home_team = home_team
    existing.away_team = away_team
    existing.stadium = stadium
    existing.game_time = game_time
    existing.series_label = series_label
    existing.chemistry_score = chemistry
    existing.chemistry_comment = chemistry_comment
    existing.home_total = int(round(home_total))
    existing.away_total = int(round(away_total))
    existing.predicted_winner = predicted_winner
    existing.winner_comment = winner_comment
    return "updated"


async def analyze_and_score_matchups(game_date: Optional[date] = None) -> dict[str, int]:
    """
    10:30 KST: run the scoring pipeline for every daily_schedules row whose
    starters have both been resolved to a pitcher_id.

    This is the first job that actually calls Claude — face_analyzer and
    fortune_generator will cache-miss on first contact and write-through to
    face_scores / fortune_scores. A second invocation on the same date
    should log only cache hits.
    """
    gd = game_date or _today_kst()
    counts = {"scored": 0, "inserted": 0, "updated": 0, "skipped": 0, "failed": 0}

    # Load schedule rows as plain Core tuples (not ORM instances) so the
    # identity map stays empty. A per-game rollback below would otherwise
    # expire every DailySchedule instance in the map, and reading an
    # expired ORM attribute on the next iteration triggers an implicit
    # lazy-load that raises MissingGreenlet under asyncio.
    async with SessionLocal() as session:
        stmt = select(
            DailySchedule.home_team,
            DailySchedule.away_team,
            DailySchedule.stadium,
            DailySchedule.game_time,
            DailySchedule.home_starter,
            DailySchedule.away_starter,
        ).where(DailySchedule.game_date == gd)
        schedule_rows = list((await session.execute(stmt)).all())

        for row in schedule_rows:
            home_team = row.home_team
            away_team = row.away_team
            stadium = row.stadium
            game_time = row.game_time
            home_starter = row.home_starter
            away_starter = row.away_starter

            series_label = _derive_series_label(gd, home_team, away_team, schedule_rows)

            if not home_starter or not away_starter:
                logger.info(
                    "[scheduler:score] skip %s@%s — starters still TBD",
                    away_team, home_team,
                )
                counts["skipped"] += 1
                continue

            home_pid = await match_pitcher_name(session, home_starter, home_team, gd)
            away_pid = await match_pitcher_name(session, away_starter, away_team, gd)
            if home_pid is None or away_pid is None:
                logger.warning(
                    "[scheduler:score] skip %s@%s — unresolved pitcher (home=%s, away=%s)",
                    away_team, home_team, home_pid, away_pid,
                )
                counts["skipped"] += 1
                continue

            home_pitcher = await _get_pitcher(session, home_pid)
            away_pitcher = await _get_pitcher(session, away_pid)
            if home_pitcher is None or away_pitcher is None:
                counts["skipped"] += 1
                continue

            # Per-game atomic boundary: score + upsert + commit are wrapped
            # together so an error on one game cannot roll back the rows
            # already committed for prior games in this pipeline run.
            try:
                score = await score_matchup(
                    session,
                    home_pitcher,
                    away_pitcher,
                    gd,
                    opponent_team_for_home=away_team,
                    opponent_team_for_away=home_team,
                    stadium=stadium or "",
                )
                chem_comment = _build_chemistry_comment(
                    home_pitcher, away_pitcher, score.chemistry
                )
                action = await _upsert_matchup_row(
                    session,
                    gd=gd,
                    home_team=home_team,
                    away_team=away_team,
                    stadium=stadium,
                    game_time=game_time,
                    series_label=series_label,
                    home_pitcher_id=home_pid,
                    away_pitcher_id=away_pid,
                    home_total=score.home.total,
                    away_total=score.away.total,
                    chemistry=score.chemistry.final,
                    chemistry_comment=chem_comment,
                    predicted_winner=score.predicted_winner,
                    winner_comment=score.winner_comment,
                )
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                await session.rollback()
                logger.exception(
                    "[scheduler:score] scoring/upsert failed for %s@%s: %s",
                    away_team, home_team, exc,
                )
                counts["failed"] += 1
                continue

            counts[action] += 1
            counts["scored"] += 1
            logger.info(
                "[scheduler:score] %s %s@%s home=%.1f away=%.1f winner=%s",
                action, away_team, home_team,
                score.home.total, score.away.total, score.predicted_winner,
            )

    logger.info("[scheduler:score] done: %s", counts)
    return counts


# ---------------------------------------------------------------------------
# Job 5 — 11:00 KST: publish matchups
# ---------------------------------------------------------------------------


async def publish_matchups(game_date: Optional[date] = None) -> int:
    """11:00 KST: flip is_published=True on today's matchups rows."""
    gd = game_date or _today_kst()
    async with SessionLocal() as session:
        stmt = select(Matchup).where(Matchup.game_date == gd)
        rows = list((await session.execute(stmt)).scalars().all())
        for r in rows:
            r.is_published = True
        await session.commit()
    logger.info("[scheduler:publish] %d matchup(s) published for %s", len(rows), gd)
    return len(rows)


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------


def _wrap(name: str, coro_fn):
    """Wrap a job coroutine so a raised exception only logs, never bubbles."""

    async def _runner() -> None:
        try:
            await coro_fn()
        except Exception as exc:  # noqa: BLE001
            logger.exception("[scheduler:%s] unhandled error: %s", name, exc)

    _runner.__name__ = f"job_{name}"
    return _runner


def build_scheduler() -> AsyncIOScheduler:
    """
    Construct the AsyncIOScheduler with the five daily jobs.

    The scheduler is NOT started here — the caller is responsible for
    .start() / .shutdown() (usually the FastAPI lifespan).
    """
    settings = get_settings()
    tz = ZoneInfo(settings.scheduler_timezone)
    scheduler = AsyncIOScheduler(timezone=tz)

    scheduler.add_job(
        _wrap("fetch", fetch_and_upsert_schedule),
        CronTrigger(hour=8, minute=0, timezone=tz),
        id="fetch_schedule_08",
        replace_existing=True,
    )
    scheduler.add_job(
        _wrap("retry_09", retry_missing_starters),
        CronTrigger(hour=9, minute=0, timezone=tz),
        id="retry_missing_09",
        replace_existing=True,
    )
    scheduler.add_job(
        _wrap("retry_10", retry_missing_starters),
        CronTrigger(hour=10, minute=0, timezone=tz),
        id="retry_missing_10",
        replace_existing=True,
    )
    scheduler.add_job(
        _wrap("score_1030", analyze_and_score_matchups),
        CronTrigger(hour=10, minute=30, timezone=tz),
        id="analyze_score_1030",
        replace_existing=True,
    )
    scheduler.add_job(
        _wrap("publish_11", publish_matchups),
        CronTrigger(hour=11, minute=0, timezone=tz),
        id="publish_11",
        replace_existing=True,
    )

    logger.info("[scheduler] built 5 jobs in timezone %s", tz)
    return scheduler
