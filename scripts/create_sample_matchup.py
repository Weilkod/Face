"""Create sample matchup rows for Wave 2 Track E smoke testing.

Inserts face_scores, fortune_scores, daily_schedules, and matchups rows
for two pairs of seeded pitchers using deterministic hash fallback scores.
No Claude API key required.

Usage (from repo root):
    python scripts/create_sample_matchup.py
    python scripts/create_sample_matchup.py --date 2026-04-16  # explicit date
    python scripts/create_sample_matchup.py --dry-run          # preview, no writes
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from datetime import date, datetime, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app import models  # noqa: E402,F401  — import side-effects register ORM
from app.models.pitcher import Pitcher  # noqa: E402
from app.models.face_score import FaceScore  # noqa: E402
from app.models.fortune_score import FortuneScore  # noqa: E402
from app.models.daily_schedule import DailySchedule  # noqa: E402
from app.models.matchup import Matchup  # noqa: E402
from app.services.chemistry_calculator import chemistry_for_pitchers  # noqa: E402
from app.services.hash_fallback import hash_face_scores, hash_fortune_scores  # noqa: E402

# The two matchup pairs we will create
# (home_pitcher_id, away_pitcher_id, home_team, away_team, stadium)
MATCHUP_PAIRS = [
    (1, 2, "SAM", "DS", "삼성라이온즈파크"),   # 원태인 vs 곽빈
    (5, 9, "LG", "KIA", "잠실야구장"),          # 손주영 vs 양현종
]


def _hash_score(seed: str) -> int:
    raw = hashlib.sha256(seed.encode()).digest()[0] % 11
    return min(raw + 2, 10)


async def main(args: argparse.Namespace) -> None:
    target_date: date = args.date or date.today()
    season = target_date.year

    async with SessionLocal() as session:
        # Load all required pitchers
        all_ids = set()
        for home_id, away_id, *_ in MATCHUP_PAIRS:
            all_ids.add(home_id)
            all_ids.add(away_id)

        pitchers: dict[int, Pitcher] = {
            p.pitcher_id: p
            for p in (
                await session.execute(
                    select(Pitcher).where(Pitcher.pitcher_id.in_(all_ids))
                )
            ).scalars().all()
        }

        if len(pitchers) < len(all_ids):
            missing = all_ids - set(pitchers.keys())
            print(f"[create_sample] ERROR: pitchers not found in DB: {missing}")
            print("  Run: python scripts/seed_pitchers.py first.")
            return

        inserted_face = 0
        inserted_fortune = 0
        inserted_schedule = 0
        inserted_matchup = 0

        for home_id, away_id, home_team, away_team, stadium in MATCHUP_PAIRS:
            home = pitchers[home_id]
            away = pitchers[away_id]

            # ----------------------------------------------------------------
            # face_scores (season-fixed, upsert)
            # ----------------------------------------------------------------
            for pitcher in (home, away):
                existing = (
                    await session.execute(
                        select(FaceScore).where(
                            FaceScore.pitcher_id == pitcher.pitcher_id,
                            FaceScore.season == season,
                        )
                    )
                ).scalar_one_or_none()

                if existing is None:
                    scores = hash_face_scores(pitcher.pitcher_id, season)
                    face_row = FaceScore(
                        pitcher_id=pitcher.pitcher_id,
                        season=season,
                        command=int(scores["command"]),
                        stuff=int(scores["stuff"]),
                        composure=int(scores["composure"]),
                        dominance=int(scores["dominance"]),
                        destiny=int(scores["destiny"]),
                        command_detail=str(scores["command_detail"]),
                        stuff_detail=str(scores["stuff_detail"]),
                        composure_detail=str(scores["composure_detail"]),
                        dominance_detail=str(scores["dominance_detail"]),
                        destiny_detail=str(scores["destiny_detail"]),
                        overall_impression=str(scores["overall_impression"]),
                        analyzed_at=datetime.utcnow(),
                    )
                    session.add(face_row)
                    inserted_face += 1
                    print(
                        f"[face] INSERT pitcher_id={pitcher.pitcher_id} ({pitcher.name}) "
                        f"cmd={scores['command']} stf={scores['stuff']} "
                        f"cmp={scores['composure']} dom={scores['dominance']} "
                        f"dst={scores['destiny']}"
                    )
                else:
                    print(
                        f"[face] SKIP  pitcher_id={pitcher.pitcher_id} ({pitcher.name}): "
                        "already exists"
                    )

            # ----------------------------------------------------------------
            # fortune_scores (daily, upsert)
            # ----------------------------------------------------------------
            for pitcher in (home, away):
                existing = (
                    await session.execute(
                        select(FortuneScore).where(
                            FortuneScore.pitcher_id == pitcher.pitcher_id,
                            FortuneScore.game_date == target_date,
                        )
                    )
                ).scalar_one_or_none()

                if existing is None:
                    scores = hash_fortune_scores(pitcher.pitcher_id, target_date)
                    fortune_row = FortuneScore(
                        pitcher_id=pitcher.pitcher_id,
                        game_date=target_date,
                        command=int(scores["command"]),
                        stuff=int(scores["stuff"]),
                        composure=int(scores["composure"]),
                        dominance=int(scores["dominance"]),
                        destiny=int(scores["destiny"]),
                        command_reading=str(scores["command_reading"]),
                        stuff_reading=str(scores["stuff_reading"]),
                        composure_reading=str(scores["composure_reading"]),
                        dominance_reading=str(scores["dominance_reading"]),
                        destiny_reading=str(scores["destiny_reading"]),
                        daily_summary=str(scores["daily_summary"]),
                        lucky_inning=int(scores["lucky_inning"]),
                    )
                    session.add(fortune_row)
                    inserted_fortune += 1
                    print(
                        f"[fortune] INSERT pitcher_id={pitcher.pitcher_id} ({pitcher.name}) "
                        f"date={target_date} "
                        f"cmd={scores['command']} stf={scores['stuff']} "
                        f"cmp={scores['composure']} dom={scores['dominance']} "
                        f"dst={scores['destiny']} lucky={scores['lucky_inning']}"
                    )
                else:
                    print(
                        f"[fortune] SKIP  pitcher_id={pitcher.pitcher_id} ({pitcher.name}) "
                        f"date={target_date}: already exists"
                    )

            # ----------------------------------------------------------------
            # face + fortune loaded, compute totals via hash scores
            # ----------------------------------------------------------------
            chemistry = chemistry_for_pitchers(home, away)
            chem_score = round(chemistry.final, 4)

            # Per-axis totals including chemistry on destiny
            face_h = hash_face_scores(home.pitcher_id, season)
            fortune_h = hash_fortune_scores(home.pitcher_id, target_date)
            face_a = hash_face_scores(away.pitcher_id, season)
            fortune_a = hash_fortune_scores(away.pitcher_id, target_date)

            axes = ("command", "stuff", "composure", "dominance", "destiny")
            home_total = sum(
                int(face_h[ax]) + int(fortune_h[ax]) for ax in axes
            ) + chem_score
            away_total = sum(
                int(face_a[ax]) + int(fortune_a[ax]) for ax in axes
            ) + chem_score

            # Round to int for home_total/away_total column (integer type)
            home_total_int = int(round(home_total))
            away_total_int = int(round(away_total))

            if home_total > away_total:
                predicted_winner = home.name
            elif away_total > home_total:
                predicted_winner = away.name
            else:
                predicted_winner = None

            winner_comment = (
                f"{predicted_winner} 근소한 우세 — 관상과 운세가 그 편"
                if predicted_winner else "완전한 균형 — 하늘도 결정을 못 내린 날"
            )

            # ----------------------------------------------------------------
            # daily_schedules row
            # ----------------------------------------------------------------
            existing_sched = (
                await session.execute(
                    select(DailySchedule).where(
                        DailySchedule.game_date == target_date,
                        DailySchedule.home_team == home_team,
                        DailySchedule.away_team == away_team,
                    )
                )
            ).scalar_one_or_none()

            if existing_sched is None:
                sched_row = DailySchedule(
                    game_date=target_date,
                    home_team=home_team,
                    away_team=away_team,
                    stadium=stadium,
                    game_time=time(18, 30),
                    home_starter=home.name,
                    away_starter=away.name,
                    home_starter_kbo_id=home.kbo_player_id,
                    away_starter_kbo_id=away.kbo_player_id,
                )
                session.add(sched_row)
                inserted_schedule += 1
                print(
                    f"[schedule] INSERT {home_team} vs {away_team} @ {stadium} "
                    f"home={home.name} away={away.name}"
                )
            else:
                print(
                    f"[schedule] SKIP  {home_team} vs {away_team} date={target_date}: "
                    "already exists"
                )

            # ----------------------------------------------------------------
            # matchups row (is_published=True so /api/today surfaces it)
            # ----------------------------------------------------------------
            existing_matchup = (
                await session.execute(
                    select(Matchup).where(
                        Matchup.game_date == target_date,
                        Matchup.home_team == home_team,
                        Matchup.away_team == away_team,
                    )
                )
            ).scalar_one_or_none()

            if existing_matchup is None:
                matchup_row = Matchup(
                    game_date=target_date,
                    home_team=home_team,
                    away_team=away_team,
                    stadium=stadium,
                    home_pitcher_id=home.pitcher_id,
                    away_pitcher_id=away.pitcher_id,
                    chemistry_score=chem_score,
                    home_total=home_total_int,
                    away_total=away_total_int,
                    predicted_winner=predicted_winner,
                    winner_comment=winner_comment,
                    is_published=True,
                )
                session.add(matchup_row)
                inserted_matchup += 1
                print(
                    f"[matchup] INSERT {home.name} ({home_total_int}) vs "
                    f"{away.name} ({away_total_int}) "
                    f"winner={predicted_winner} chem={chem_score} published=True"
                )
            else:
                print(
                    f"[matchup] SKIP  {home_team} vs {away_team} date={target_date}: "
                    "already exists"
                )

        # ----------------------------------------------------------------
        # Commit or rollback
        # ----------------------------------------------------------------
        if args.dry_run:
            await session.rollback()
            print("\n[create_sample] --dry-run: rolled back, nothing written")
        else:
            await session.commit()
            print(
                f"\n[create_sample] done — "
                f"face={inserted_face} fortune={inserted_fortune} "
                f"schedule={inserted_schedule} matchup={inserted_matchup} "
                f"date={target_date}"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed sample matchup data for Wave 2 Track E smoke testing."
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="Target game date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Roll back all writes at the end — preview mode.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    asyncio.run(main(parse_args()))
