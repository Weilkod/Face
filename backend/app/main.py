from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.scheduler import build_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.scheduler_enabled:
        scheduler = build_scheduler()
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("[main] APScheduler started with %d job(s)", len(scheduler.get_jobs()))
    else:
        # Multi-replica deploy path: only one worker (or a dedicated scheduler
        # process) sets SCHEDULER_ENABLED=true so crawl/analyze/publish jobs
        # don't double-fire. WARNING so misconfigured prod shows up in logs.
        app.state.scheduler = None
        logger.warning("[main] SCHEDULER_ENABLED=false — APScheduler not started")
    try:
        yield
    finally:
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("[main] APScheduler stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FACEMETRICS API",
        version="0.1.0",
        description="KBO 선발투수 관상×운세 Head-to-Head API (entertainment only).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    # Client-facing routers
    from app.routers import accuracy, history, matchup, pitcher, today

    app.include_router(today.router, prefix="/api")
    app.include_router(matchup.router, prefix="/api")
    app.include_router(pitcher.router, prefix="/api")
    app.include_router(history.router, prefix="/api")
    app.include_router(accuracy.router, prefix="/api")

    # Admin routers
    from app.routers import admin

    app.include_router(admin.router, prefix="/admin")

    return app


app = create_app()
