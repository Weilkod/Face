FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts
# Ships rule JSON (zodiac_compatibility, constellation_elements) + seed
# (pitchers_2026, pitcher_images/manifest) into the image. `.dockerignore`
# filters out *.db / *.sqlite / binary pitcher images. Without this COPY,
# `chemistry_calculator._load_zodiac_data()` raises FileNotFoundError on
# any matchup detail request in production (Railway has no bind mount).
# Locally, docker-compose bind-mounts ./data:/app/data which silently
# overrides this layer — that's why the bug only shows on Railway.
COPY data /app/data

RUN useradd -u 1000 -m app \
 && chown -R app:app /app
USER app

ENV PYTHONPATH=/app/backend

EXPOSE 8000

ENTRYPOINT ["tini", "-g", "--"]
CMD ["sh", "-c", "python scripts/init_db.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
