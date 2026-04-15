"""
verify_srid.py — A-7 srId 라이브 검증 (세션 11).

crawler.py 의 현재 값 `0,1,3,4,5,7` (세션 11 에서 CLAUDE.md §5 에 문서화됨)
과 축약 variant 들을 실 KBO `POST /ws/Main.asmx/GetKboGameList` 로 호출해,
1군 정규시즌 경기 수 + SR_ID / LE_ID 분포 + 퓨처스 혼입 여부를 대조한다.
2026-04-15 에서는 세 variant 모두 동일 payload (SR_ID=0/LE_ID=1) 를 반환했다.

일회성 검증 스크립트이므로 결과를 stdout 에 덤프하고 종료.
사용법:
    python scripts/verify_srid.py [YYYYMMDD]
인자가 없으면 오늘(KST)을 사용.

NOTE: stdout contains real player names (T_PIT_P_NM / B_PIT_P_NM).
Dev-only tool — do NOT paste full output into PR descriptions, public
gists, or commit logs. Summarize (counts / SR_ID distribution) instead.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

KST = ZoneInfo("Asia/Seoul")
KBO_HOST = "https://www.koreabaseball.com"
URL = f"{KBO_HOST}/ws/Main.asmx/GetKboGameList"
REFERER = f"{KBO_HOST}/Schedule/GameCenter/Main.aspx"

HEADERS = {
    "User-Agent": "FACEMETRICS/0.1 (+research)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": REFERER,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

SR_VARIANTS = {
    "code_current (0,1,3,4,5,7)": "0,1,3,4,5,7",
    "claude_md_spec (0,9,6)": "0,9,6",
    "baseline (0)": "0",
}


def _unwrap(payload):
    """ASMX occasionally wraps in {'d': ...} or serialises as a JSON string."""
    if isinstance(payload, dict) and "d" in payload and not payload.get("game"):
        payload = payload["d"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    return payload


async def _one(client: httpx.AsyncClient, label: str, sr: str, yyyymmdd: str) -> dict:
    form = {"date": yyyymmdd, "leId": "1", "srId": sr}
    try:
        # Rate-limit BEFORE the first request too (not only between variants in main),
        # so back-to-back runs of this script stay ≤ 1 req/s per host.
        await asyncio.sleep(1.0)
        resp = await client.post(URL, data=form)
        status = resp.status_code
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text[:400]
    except Exception as exc:
        return {"label": label, "srId": sr, "error": repr(exc)}

    data = _unwrap(payload)
    games = data.get("game") if isinstance(data, dict) else None
    if not isinstance(games, list):
        return {
            "label": label,
            "srId": sr,
            "status": status,
            "game_count": 0,
            "raw_head": str(data)[:400] if data is not None else str(payload)[:400],
        }

    # summarise per game
    summary = []
    for g in games:
        summary.append(
            {
                "G_ID": g.get("G_ID"),
                "SR_ID": g.get("SR_ID"),
                "LE_ID": g.get("LE_ID"),
                "away": g.get("AWAY_ID"),
                "home": g.get("HOME_ID"),
                "away_pit": (g.get("T_PIT_P_NM") or "").strip(),
                "home_pit": (g.get("B_PIT_P_NM") or "").strip(),
                "cancel": g.get("CANCEL_SC_ID"),
                "start_ck": g.get("START_PIT_CK"),
            }
        )

    sr_values = sorted({str(g.get("SR_ID")) for g in games})
    le_values = sorted({str(g.get("LE_ID")) for g in games})
    return {
        "label": label,
        "srId": sr,
        "status": status,
        "game_count": len(games),
        "distinct_SR_ID_in_response": sr_values,
        "distinct_LE_ID_in_response": le_values,
        "games": summary,
    }


async def main() -> None:
    if len(sys.argv) > 1:
        yyyymmdd = sys.argv[1]
    else:
        yyyymmdd = datetime.now(KST).strftime("%Y%m%d")

    print(f"# A-7 srId live verification — date={yyyymmdd}")
    print(f"# endpoint: POST {URL}")
    print()

    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=False) as client:
        for label, sr in SR_VARIANTS.items():
            result = await _one(client, label, sr, yyyymmdd)
            print(f"=== {label}  (srId={sr}) ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print()
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
