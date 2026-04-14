"""B-3 — analyze_and_score_matchups 의 atomic rollback 검증.

목적:
    이전 (B-2 수정 전) 에는 face_analyzer / fortune_generator 가 자체 commit() 을
    호출했기 때문에 매치업 한 건을 처리하는 도중 fortune 단계에서 예외가 발생해도
    이미 commit 된 face_score 행이 DB 에 남는 "고아" 상태가 가능했다.

    B-2 에서 두 서비스를 caller-managed 로 전환했고, scheduler 의 외층
    try/except → rollback 이 매치업 단위로 atomic 하게 작동해야 한다.

    이 테스트는 fortune 경로를 양쪽 모두 실패시켜 (Claude Text raise + hash
    fallback 도 raise) → 외층 except 가 rollback 하면 face_scores / fortune_scores
    / matchups 어느 테이블에도 행이 남지 않아야 함을 확인한다.

happy path 도 함께 검증해서 mock 기반 파이프라인이 정상 동작함을 보장한다.
"""
from __future__ import annotations

from datetime import date, datetime, time
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

# conftest.py 가 DATABASE_URL 을 세팅했다는 가정 하에 import
from app.db import Base, SessionLocal, engine
from app.models import DailySchedule, FaceScore, FortuneScore, Matchup, Pitcher
from app.scheduler import analyze_and_score_matchups
from app.schemas.ai import AxisScore, FaceAnalysisResult, FortuneAxis, FortuneReadingResult


GAME_DATE = date(2026, 4, 14)


def _fake_face_result(pitcher_name: str) -> FaceAnalysisResult:
    return FaceAnalysisResult(
        pitcher_name=pitcher_name,
        command=AxisScore(score=7, detail="결단력 있는 입꼬리"),
        stuff=AxisScore(score=6, detail="단단한 광대"),
        composure=AxisScore(score=8, detail="안정적인 눈매"),
        dominance=AxisScore(score=5, detail="평범한 턱선"),
        destiny=AxisScore(score=6, detail="복있는 이마"),
        overall_impression="실력파 투수상",
    )


def _fake_fortune_result(pitcher_name: str, gd: date) -> FortuneReadingResult:
    return FortuneReadingResult(
        pitcher_name=pitcher_name,
        date=gd.isoformat(),
        command_fortune=FortuneAxis(score=6, reading="바람 잔잔"),
        stuff_fortune=FortuneAxis(score=7, reading="구위 상승"),
        composure_fortune=FortuneAxis(score=5, reading="평정"),
        dominance_fortune=FortuneAxis(score=6, reading="기세 있음"),
        destiny_fortune=FortuneAxis(score=7, reading="운명의 날"),
        daily_summary="좋은 하루",
        lucky_inning=5,
    )


@pytest_asyncio.fixture(scope="function")
async def fresh_db():
    """매 테스트마다 모든 테이블 drop+create 후 시드 데이터 삽입."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # 두 명의 투수 시드
        session.add_all([
            Pitcher(
                pitcher_id=1, name="원태인", team="SAM",
                birth_date=date(2000, 4, 6),
                chinese_zodiac="진", zodiac_sign="양자리", zodiac_element="불",
                profile_photo="https://example.com/face1.jpg",
            ),
            Pitcher(
                pitcher_id=2, name="곽빈", team="DS",
                birth_date=date(1999, 5, 28),
                chinese_zodiac="묘", zodiac_sign="쌍둥이자리", zodiac_element="바람",
                profile_photo="https://example.com/face2.jpg",
            ),
        ])
        # 매치업 1건 (양쪽 선발 확정)
        session.add(DailySchedule(
            game_date=GAME_DATE,
            home_team="SAM", away_team="DS",
            stadium="대구",
            game_time=time(18, 30),
            home_starter="원태인",
            away_starter="곽빈",
            crawled_at=datetime(2026, 4, 14, 8, 0, 0),
        ))
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _row_counts() -> tuple[int, int, int]:
    async with SessionLocal() as session:
        face = (await session.execute(select(FaceScore))).scalars().all()
        fortune = (await session.execute(select(FortuneScore))).scalars().all()
        matchup = (await session.execute(select(Matchup))).scalars().all()
        return len(face), len(fortune), len(matchup)


@pytest.mark.asyncio
async def test_happy_path_persists_all_rows(fresh_db):
    """모든 mock 이 성공할 때 face×2, fortune×2, matchup×1 이 DB 에 기록되어야 한다."""

    async def fake_call_vision(pitcher, temperature=0.3):
        return _fake_face_result(pitcher.name)

    async def fake_call_text(pitcher, game_date, opponent_team, stadium, temperature=0.7):
        return _fake_fortune_result(pitcher.name, game_date)

    with (
        patch("app.services.face_analyzer._call_claude_vision", side_effect=fake_call_vision),
        patch("app.services.fortune_generator._call_claude_text", side_effect=fake_call_text),
    ):
        counts = await analyze_and_score_matchups(game_date=GAME_DATE)

    assert counts["scored"] == 1, f"scored 가 1 이어야 함, 실제={counts}"
    assert counts["failed"] == 0, f"failed 가 0 이어야 함, 실제={counts}"

    face, fortune, matchup = await _row_counts()
    assert face == 2, f"face_scores 행이 2 여야 함, 실제={face}"
    assert fortune == 2, f"fortune_scores 행이 2 여야 함, 실제={fortune}"
    assert matchup == 1, f"matchups 행이 1 이어야 함, 실제={matchup}"


@pytest.mark.asyncio
async def test_fortune_failure_rolls_back_face_rows(fresh_db):
    """face 는 두 명 모두 성공했지만 fortune 의 Claude+fallback 이 둘 다 raise 하면,
    외층 try/except 가 rollback 해서 face / fortune / matchup 어느 행도 남지 않아야 한다.

    B-2 수정 전에는 face commit 이 inner 에서 일어나서 이 시나리오에서 face 행 2개가
    "고아" 상태로 남았었다. 그래서 단순히 "최종 행 0" 만 확인하면 face 가 아예 호출되지
    않는 회귀와 구분이 안 된다 — fortune mock 안에서 같은 세션으로 face_scores COUNT
    를 찍어 mid-transaction 에 face 행이 실제로 flush 되었음을 동시 검증한다.
    """

    mid_transaction_face_count: dict[str, int] = {"value": -1}

    async def fake_call_vision(pitcher, temperature=0.3):
        return _fake_face_result(pitcher.name)

    async def fake_call_text_always_raises(pitcher, game_date, opponent_team, stadium, temperature=0.7):
        # fortune 호출 시점이면 face 는 두 명 모두 이미 flush 되었어야 한다 (commit 전이지만
        # session 안에서는 SELECT 로 보임). 첫 호출 때 한 번 측정.
        if mid_transaction_face_count["value"] < 0:
            from app.db import SessionLocal as _SL
            async with _SL() as probe:
                # 다른 세션에서 본 row 수: commit 전이라 0 이어야 한다 (rollback 가능 상태)
                mid_transaction_face_count["other_session"] = len(  # type: ignore[index]
                    (await probe.execute(select(FaceScore))).scalars().all()
                )
            mid_transaction_face_count["value"] = 0
        raise RuntimeError("simulated Claude Text outage")

    def fake_hash_fortune_raises(pitcher_id, game_date):
        raise RuntimeError("simulated hash fallback failure")

    with (
        patch("app.services.face_analyzer._call_claude_vision", side_effect=fake_call_vision),
        patch("app.services.fortune_generator._call_claude_text", side_effect=fake_call_text_always_raises),
        patch("app.services.fortune_generator.hash_fortune_scores", side_effect=fake_hash_fortune_raises),
    ):
        counts = await analyze_and_score_matchups(game_date=GAME_DATE)

    assert counts["scored"] == 0, f"scored 가 0 이어야 함, 실제={counts}"
    assert counts["failed"] == 1, f"failed 가 1 이어야 함, 실제={counts}"

    # mid-transaction 에 다른 세션에서 face 가 0 으로 보였어야 한다
    # (그래야 caller-managed transaction 이 진짜로 작동중이라는 증거)
    assert mid_transaction_face_count.get("other_session", -1) == 0, (
        "fortune 단계에서 다른 세션에서 face_scores 가 보이면 안 됨 — "
        "B-2 회귀 (inner commit 부활) 의심"
    )

    face, fortune, matchup = await _row_counts()
    assert face == 0, f"face_scores 행이 rollback 되어 0 이어야 함, 실제={face} — B-2 회귀!"
    assert fortune == 0, f"fortune_scores 행이 0 이어야 함, 실제={fortune}"
    assert matchup == 0, f"matchups 행이 0 이어야 함, 실제={matchup}"


@pytest.mark.asyncio
async def test_face_failure_rolls_back_cleanly(fresh_db):
    """face 자체가 fallback 까지 실패하면 동일하게 atomic rollback."""

    async def fake_call_vision_raises(pitcher, temperature=0.3):
        raise RuntimeError("simulated Claude Vision outage")

    def fake_hash_face_raises(pitcher_id, season):
        raise RuntimeError("simulated hash face fallback failure")

    with (
        patch("app.services.face_analyzer._call_claude_vision", side_effect=fake_call_vision_raises),
        patch("app.services.face_analyzer.hash_face_scores", side_effect=fake_hash_face_raises),
    ):
        counts = await analyze_and_score_matchups(game_date=GAME_DATE)

    assert counts["scored"] == 0
    assert counts["failed"] == 1

    face, fortune, matchup = await _row_counts()
    assert face == 0, f"face_scores 행이 0 이어야 함, 실제={face}"
    assert fortune == 0
    assert matchup == 0
