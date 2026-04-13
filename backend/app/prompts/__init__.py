"""
Prompt loader for FACEMETRICS.

Usage:
    from app.prompts import load_prompt
    system, user_template = load_prompt("face_analysis")
    system, user_template = load_prompt("fortune_reading")

Each .txt file uses ===SYSTEM=== / ===USER=== delimiters.
Results are cached with lru_cache — files are read once at startup.
"""

from __future__ import annotations

import functools
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent
_SYSTEM_DELIMITER = "===SYSTEM==="
_USER_DELIMITER = "===USER==="


@functools.lru_cache(maxsize=16)
def load_prompt(name: str) -> tuple[str, str]:
    """Read <name>.txt, split on delimiters, return (system_text, user_template).

    The system_text is cache-stable (no variables).
    The user_template may contain {placeholder} strings for str.format().

    Raises FileNotFoundError if the prompt file does not exist.
    Raises ValueError if the delimiters are missing or malformed.
    """
    path = _PROMPTS_DIR / f"{name}.txt"
    raw = path.read_text(encoding="utf-8")

    if _SYSTEM_DELIMITER not in raw:
        raise ValueError(f"Prompt '{name}' missing {_SYSTEM_DELIMITER!r} delimiter")
    if _USER_DELIMITER not in raw:
        raise ValueError(f"Prompt '{name}' missing {_USER_DELIMITER!r} delimiter")

    # Strip comment lines (start with #) before parsing delimiters
    lines = raw.splitlines()
    filtered = "\n".join(line for line in lines if not line.startswith("#"))

    sys_start = filtered.index(_SYSTEM_DELIMITER) + len(_SYSTEM_DELIMITER)
    user_start = filtered.index(_USER_DELIMITER)
    user_content_start = user_start + len(_USER_DELIMITER)

    system_text = filtered[sys_start:user_start].strip()
    user_template = filtered[user_content_start:].strip()

    if not system_text:
        raise ValueError(f"Prompt '{name}' has empty SYSTEM block")
    if not user_template:
        raise ValueError(f"Prompt '{name}' has empty USER block")

    return system_text, user_template
