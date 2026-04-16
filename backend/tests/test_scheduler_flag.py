"""I3 — SCHEDULER_ENABLED 플래그 가드.

multi-replica 배포 (Railway/Fly) 에서 lifespan 이 무조건 APScheduler 를 기동하면
크롤/분석/퍼블리시 잡이 중복 실행되어 fortune_scores 중복 write + Claude 토큰 2배
소모. SCHEDULER_ENABLED=false 로 추가 워커의 스케줄러를 끌 수 있어야 한다
(한 워커 / 전용 프로세스만 true).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings


def test_scheduler_enabled_default(monkeypatch):
    """default(SCHEDULER_ENABLED 미지정) 는 scheduler 를 기동하고 shutdown 까지 정상 호출."""
    monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
    get_settings.cache_clear()

    fake_scheduler = MagicMock()
    fake_scheduler.get_jobs.return_value = []

    with patch("app.main.build_scheduler", return_value=fake_scheduler) as build:
        from app.main import create_app

        app = create_app()
        with TestClient(app):
            assert build.called
            fake_scheduler.start.assert_called_once()
            assert app.state.scheduler is fake_scheduler

        fake_scheduler.shutdown.assert_called_once_with(wait=False)


def test_scheduler_disabled(monkeypatch):
    """SCHEDULER_ENABLED=false 면 build_scheduler 자체를 부르지 않고 state.scheduler is None."""
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    get_settings.cache_clear()

    with patch("app.main.build_scheduler") as build:
        from app.main import create_app

        app = create_app()
        with TestClient(app):
            build.assert_not_called()
            assert app.state.scheduler is None


def test_scheduler_enabled_explicit_true(monkeypatch):
    """SCHEDULER_ENABLED=true 명시적 세팅도 default 와 동일하게 동작."""
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    get_settings.cache_clear()

    fake_scheduler = MagicMock()
    fake_scheduler.get_jobs.return_value = []

    with patch("app.main.build_scheduler", return_value=fake_scheduler):
        from app.main import create_app

        app = create_app()
        with TestClient(app):
            fake_scheduler.start.assert_called_once()
            assert app.state.scheduler is fake_scheduler
