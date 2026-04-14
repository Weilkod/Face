"""B-1 검증 스크립트 — Claude Vision/Text 캐시 미스→히트 경로 실검증.

목적:
  1. (캐시 미스) Claude Vision 1회 + Claude Text 1회 호출, DB write-through 확인
  2. (캐시 히트) 두번째 호출에서 DB만 읽고 Claude 호출 0회임을 logger 출력으로 확인
  3. score_matchup() end-to-end 통합으로 MatchupScore 객체 정상 생성

⚠️ DESTRUCTIVE — 이 스크립트는 dev DB 의 `pitchers.profile_photo` 컬럼을 manifest
   의 KBO URL 로 영구 덮어쓴다 (원래 값으로 복원하지 않음). 검증 후에 시드를
   다시 돌리고 싶으면 `python scripts/seed_pitchers.py` 로 photo 컬럼이 manifest
   에서 재주입된다.

사용:
  PYTHONPATH=backend .venv/Scripts/python.exe scripts/verify_ai_pipeline.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import FaceScore, FortuneScore, Pitcher  # noqa: E402
from app.services.face_analyzer import get_or_create_face_scores  # noqa: E402
from app.services.fortune_generator import get_or_create_fortune_scores  # noqa: E402
from app.services.scoring_engine import AXIS_ORDER, score_matchup  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("verify_ai_pipeline")


def _resolve_photo_url(pitcher_index: int) -> str | None:
    manifest_path = PROJECT_ROOT / "data" / "pitcher_images" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in data.get("success", []):
        if row.get("index") == pitcher_index and row.get("source") == "kbo":
            return row.get("url")
    return None


async def _override_profile_photos_with_urls() -> dict[int, str]:
    """프로필 사진 경로를 manifest 의 KBO URL 로 교체. (기존 경로는 git ignored 로 로컬에 없음)"""
    overrides: dict[int, str] = {}
    async with SessionLocal() as session:
        stmt = select(Pitcher).order_by(Pitcher.pitcher_id).limit(2)
        pitchers = (await session.execute(stmt)).scalars().all()
        for idx, p in enumerate(pitchers, start=1):
            url = _resolve_photo_url(idx)
            if url is None:
                logger.error("manifest 에 index=%d KBO URL 없음", idx)
                continue
            old = p.profile_photo
            p.profile_photo = url
            overrides[p.pitcher_id] = old or ""
            logger.info(
                "pitcher_id=%d name=%s photo: %r -> %s",
                p.pitcher_id, p.name, old, url,
            )
        await session.commit()
    return overrides


async def _count_score_rows() -> tuple[int, int]:
    async with SessionLocal() as session:
        face_count = (await session.execute(select(FaceScore))).scalars().all()
        fortune_count = (await session.execute(select(FortuneScore))).scalars().all()
        return len(face_count), len(fortune_count)


async def _step_face_first_call(pitcher_id: int) -> FaceScore:
    logger.info("=" * 60)
    logger.info("[FACE 1차] pitcher_id=%d 캐시 미스 경로 — Claude Vision 호출 예상", pitcher_id)
    async with SessionLocal() as session:
        pitcher = await session.get(Pitcher, pitcher_id)
        result = await get_or_create_face_scores(session, pitcher, season=2026)
        await session.commit()  # caller-managed commit (B-2)
        logger.info(
            "[FACE 1차] 결과 command=%d stuff=%d composure=%d dominance=%d destiny=%d",
            result.command, result.stuff, result.composure, result.dominance, result.destiny,
        )
        return result


async def _step_face_second_call(pitcher_id: int) -> FaceScore:
    logger.info("[FACE 2차] pitcher_id=%d — DB 캐시 히트 예상 (Claude 호출 0회)", pitcher_id)
    async with SessionLocal() as session:
        pitcher = await session.get(Pitcher, pitcher_id)
        result = await get_or_create_face_scores(session, pitcher, season=2026)
        await session.commit()  # no-op write but keeps the pattern symmetric
        return result


async def _step_fortune_first_call(pitcher_id: int, gd: date, opp: str) -> FortuneScore:
    logger.info("=" * 60)
    logger.info("[FORTUNE 1차] pitcher_id=%d date=%s 캐시 미스 — Claude Text 호출 예상", pitcher_id, gd)
    async with SessionLocal() as session:
        pitcher = await session.get(Pitcher, pitcher_id)
        result = await get_or_create_fortune_scores(
            session, pitcher, gd, opponent_team=opp, stadium="잠실"
        )
        await session.commit()  # caller-managed commit (B-2)
        logger.info(
            "[FORTUNE 1차] 결과 command=%d stuff=%d composure=%d dominance=%d destiny=%d daily=%r",
            result.command, result.stuff, result.composure, result.dominance, result.destiny,
            result.daily_summary[:60],
        )
        return result


async def _step_fortune_second_call(pitcher_id: int, gd: date, opp: str) -> FortuneScore:
    logger.info("[FORTUNE 2차] pitcher_id=%d — DB 캐시 히트 예상 (Claude 호출 0회)", pitcher_id)
    async with SessionLocal() as session:
        pitcher = await session.get(Pitcher, pitcher_id)
        result = await get_or_create_fortune_scores(
            session, pitcher, gd, opponent_team=opp, stadium="잠실"
        )
        await session.commit()
        return result


async def _step_score_matchup(home_id: int, away_id: int, gd: date) -> None:
    logger.info("=" * 60)
    logger.info("[SCORE_MATCHUP] home=%d vs away=%d date=%s — 캐시 hit 만으로 통합 검증",
                home_id, away_id, gd)
    async with SessionLocal() as session:
        home = await session.get(Pitcher, home_id)
        away = await session.get(Pitcher, away_id)
        m = await score_matchup(session, home, away, gd, season=2026)
    logger.info(
        "[SCORE_MATCHUP] %s(home) total=%.1f vs %s(away) total=%.1f predicted=%s",
        m.home.name, m.home.total, m.away.name, m.away.total, m.predicted_winner,
    )
    logger.info("[SCORE_MATCHUP] winner_comment=%s", m.winner_comment)
    for axis in AXIS_ORDER:
        ha = m.home.axes[axis]
        aa = m.away.axes[axis]
        logger.info(
            "  axis=%s home(face=%d fortune=%d chem=%.1f tot=%.1f) away(face=%d fortune=%d chem=%.1f tot=%.1f)",
            axis, ha.face, ha.fortune, ha.chemistry, ha.total,
            aa.face, aa.fortune, aa.chemistry, aa.total,
        )


async def main() -> int:
    logger.info("##### B-1 verify_ai_pipeline START #####")

    overrides = await _override_profile_photos_with_urls()
    if len(overrides) < 2:
        logger.error("프로필 URL 오버라이드 실패 — 2명 미만")
        return 1
    pitcher_ids = sorted(overrides.keys())
    home_id, away_id = pitcher_ids[0], pitcher_ids[1]
    gd = date(2026, 4, 14)

    face_n0, fortune_n0 = await _count_score_rows()
    logger.info("[BEFORE] face_scores rows=%d fortune_scores rows=%d", face_n0, fortune_n0)

    await _step_face_first_call(home_id)
    await _step_face_first_call(away_id)
    face_n1, fortune_n1 = await _count_score_rows()
    logger.info("[AFTER FACE-MISS] face_scores rows=%d (delta=%d)", face_n1, face_n1 - face_n0)
    assert face_n1 == face_n0 + 2, "face_scores 가 +2 안됨"

    await _step_face_second_call(home_id)
    await _step_face_second_call(away_id)
    face_n2, _ = await _count_score_rows()
    assert face_n2 == face_n1, "face_scores 가 두번째 호출 후 증가함 — 캐시 히트 실패"
    logger.info("[FACE 캐시 히트 검증] OK — rows 변동 없음 (%d)", face_n2)

    await _step_fortune_first_call(home_id, gd, "DS")
    await _step_fortune_first_call(away_id, gd, "SAM")
    _, fortune_n2 = await _count_score_rows()
    logger.info("[AFTER FORTUNE-MISS] fortune_scores rows=%d (delta=%d)",
                fortune_n2, fortune_n2 - fortune_n0)
    assert fortune_n2 == fortune_n0 + 2, "fortune_scores 가 +2 안됨"

    await _step_fortune_second_call(home_id, gd, "DS")
    await _step_fortune_second_call(away_id, gd, "SAM")
    _, fortune_n3 = await _count_score_rows()
    assert fortune_n3 == fortune_n2, "fortune_scores 가 두번째 호출 후 증가함 — 캐시 히트 실패"
    logger.info("[FORTUNE 캐시 히트 검증] OK — rows 변동 없음 (%d)", fortune_n3)

    await _step_score_matchup(home_id, away_id, gd)

    logger.info("##### B-1 verify_ai_pipeline DONE — 모든 검증 통과 #####")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    raise SystemExit(asyncio.run(main()))
