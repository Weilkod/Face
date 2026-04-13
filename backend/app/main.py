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
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("[main] APScheduler started with %d job(s)", len(scheduler.get_jobs()))
    try:
        yield
    finally:
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

    return app


app = create_app()
