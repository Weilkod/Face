"""테스트 셋업 — app 모듈을 import 하기 BEFORE 에 DATABASE_URL 을 임시 파일로 고정.

`app.config.get_settings()` 는 lru_cache 로 한 번만 평가되므로, 어떤 app.* import
보다도 먼저 환경 변수가 세팅되어 있어야 한다. conftest.py 는 pytest 가 가장 먼저
로드하므로 여기가 적절한 위치다.

PID 를 파일명에 섞어서 `pytest -n auto` 등의 병렬 실행에서도 워커 간 충돌이 없도록
한다. 그리고 방어적으로 `get_settings.cache_clear()` 를 호출해 다른 conftest 나
plugin 이 먼저 app.config 를 import 했더라도 우리의 DATABASE_URL 이 이긴다.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_TMP_DB_PATH = Path(tempfile.gettempdir()) / f"facemetrics_b3_test_{os.getpid()}.db"
if _TMP_DB_PATH.exists():
    _TMP_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB_PATH.as_posix()}"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used-by-mocks")

# Defensive: 누군가 이미 app.config 를 import 했더라도 lru_cache 를 비워서
# 다음 get_settings() 호출이 우리의 환경 변수로 새로 평가되도록 한다.
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()
