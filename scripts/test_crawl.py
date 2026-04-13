# -*- coding: utf-8 -*-
"""
KBO 크롤링 가이드 검증 스크립트
각 API 엔드포인트를 샘플로 테스트한다.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import httpx
import asyncio
from bs4 import BeautifulSoup
import re
from datetime import date

HEADERS = {
    "User-Agent": "FACEMETRICS/0.1 (+research)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "X-Requested-With": "XMLHttpRequest",
}

TODAY = "20260413"
SEASON = "2026"


# ─────────────────────────────────────────
# 1. GetTodayGames
# ─────────────────────────────────────────
async def test_today_games(client: httpx.AsyncClient):
    print("\n" + "="*60)
    print("▶ [1] GetTodayGames —", TODAY)
    print("="*60)

    resp = await client.post(
        "https://www.koreabaseball.com/ws/Schedule.asmx/GetTodayGames",
        data={
            "gameDate": TODAY,
            "leId": "1",
            "srId": "0,1,3,4,5,7",
            "headerCk": "0",
        },
    )
    print(f"  HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("  FAILED:", resp.text[:300])
        return []

    data = resp.json()
    games = data.get("gameList", [])
    print(f"  경기 수: {len(games)}")
    for g in games[:3]:  # 샘플 3개
        print(f"  [{g.get('awayCode')} @ {g.get('homeCode')}]  {g.get('gameTime')[:5]}  {g.get('stadiumFullName')}  gameId={g.get('gameId')}")
    return games


# ─────────────────────────────────────────
# 2. GetScheduleList (월간)
# ─────────────────────────────────────────
async def test_schedule_list(client: httpx.AsyncClient):
    print("\n" + "="*60)
    print("▶ [2] GetScheduleList — 2026-04")
    print("="*60)

    resp = await client.post(
        "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList",
        data={
            "leId": "1",
            "srIdList": "0,9,6",
            "seasonId": SEASON,
            "gameMonth": "04",
            "teamId": "",
        },
    )
    print(f"  HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("  FAILED:", resp.text[:300])
        return

    data = resp.json()
    rows = data.get("rows", [])
    print(f"  rows 수: {len(rows)}")

    # 날짜 파싱 샘플
    dates_found = 0
    for row_wrap in rows[:30]:
        cells = row_wrap.get("row", [])
        for cell in cells:
            if cell.get("Class") == "day":
                print(f"  날짜셀: {cell.get('Text')}  RowSpan={cell.get('RowSpan')}")
                dates_found += 1
                if dates_found >= 3:
                    break
        if dates_found >= 3:
            break


# ─────────────────────────────────────────
# 3. GameCenter HTML → 선발투수 추출
# ─────────────────────────────────────────
async def test_gamecenter(client: httpx.AsyncClient, game_id: str):
    print("\n" + "="*60)
    print(f"▶ [3] GameCenter HTML — gameId={game_id}")
    print("="*60)

    game_date = game_id[:8]
    url = (
        f"https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx"
        f"?gameDate={game_date}&gameId={game_id}&section=START_PIT"
    )
    resp = await client.get(url, headers={k: v for k, v in HEADERS.items() if k != "Content-Type"})
    print(f"  HTTP {resp.status_code}  (size: {len(resp.text)} chars)")
    if resp.status_code != 200:
        print("  FAILED")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    games_li = soup.select("li.game-cont")
    print(f"  li.game-cont 개수: {len(games_li)}")

    for li in games_li[:2]:
        away = li.get("away_id")
        home = li.get("home_id")
        away_pid = li.get("away_p_id")
        home_pid = li.get("home_p_id")
        stadium = li.get("s_nm")
        print(f"  {away}(원정) vs {home}(홈)  구장={stadium}  away_p_id={away_pid}  home_p_id={home_pid}")

    return games_li


# ─────────────────────────────────────────
# 4. 선수 프로필 (이름 + 생년월일 + 사진)
# ─────────────────────────────────────────
async def test_player_profile(client: httpx.AsyncClient, player_id: str):
    print("\n" + "="*60)
    print(f"▶ [4] Player Profile — playerId={player_id}")
    print("="*60)

    url = f"https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId={player_id}"
    resp = await client.get(url, headers={k: v for k, v in HEADERS.items() if k != "Content-Type"})
    print(f"  HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("  FAILED")
        return

    soup = BeautifulSoup(resp.text, "html.parser")

    # 이름 + 사진
    img = soup.select_one("div.photo img")
    name = img.get("alt", "") if img else "(없음)"
    photo_src = img.get("src", "") if img else ""
    if photo_src.startswith("//"):
        photo_src = "https:" + photo_src

    # 생년월일
    birthday_span = soup.find("span", id=re.compile(r"lblBirthday"))
    birthday_text = birthday_span.get_text(strip=True) if birthday_span else ""
    m = re.match(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", birthday_text)
    birthday = date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

    print(f"  이름: {name}")
    print(f"  생년월일: {birthday}")
    print(f"  사진 URL: {photo_src}")


# ─────────────────────────────────────────
# 5. GetPitcherRecordAnalysis
# ─────────────────────────────────────────
async def test_pitcher_analysis(client: httpx.AsyncClient, away_team: str, away_pid: str, home_team: str, home_pid: str):
    print("\n" + "="*60)
    print(f"▶ [5] GetPitcherRecordAnalysis — {away_team}({away_pid}) vs {home_team}({home_pid})")
    print("="*60)

    resp = await client.post(
        "https://www.koreabaseball.com/ws/Schedule.asmx/GetPitcherRecordAnalysis",
        data={
            "leId": "1",
            "srId": "0",
            "seasonId": SEASON,
            "awayTeamId": away_team,
            "awayPitId": away_pid,
            "homeTeamId": home_team,
            "homePitId": home_pid,
            "groupSc": "SEASON",
        },
    )
    print(f"  HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("  FAILED:", resp.text[:300])
        return

    data = resp.json()
    rows = data.get("rows", [])
    print(f"  rows 수: {len(rows)}")
    # 첫 두 행만 출력
    for rw in rows[:2]:
        cells = rw.get("row", [])
        texts = [c.get("Text", "") for c in cells]
        print(f"  row: {texts[:6]}")  # 처음 6개 셀만


# ─────────────────────────────────────────
# main
# ─────────────────────────────────────────
async def main():
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:

        # 1. 오늘 경기 목록
        games = await test_today_games(client)
        await asyncio.sleep(0.5)

        # 2. 월간 일정
        await test_schedule_list(client)
        await asyncio.sleep(0.5)

        # 3~5: 오늘 경기가 있으면 첫 번째 게임으로 테스트
        if games:
            first = games[0]
            game_id = first.get("gameId", "")
        else:
            # fallback: 어제 경기 고정 샘플
            game_id = "20260412LTLG0"

        games_li = await test_gamecenter(client, game_id)
        await asyncio.sleep(0.5)

        # 선발투수 ID 추출해서 프로필 조회
        away_pid = home_pid = None
        away_team = home_team = None
        if games_li:
            li = games_li[0]
            away_team = li.get("away_id", "")
            home_team = li.get("home_id", "")
            away_pid = li.get("away_p_id", "")
            home_pid = li.get("home_p_id", "")

        if away_pid and away_pid not in ("", "0"):
            await test_player_profile(client, away_pid)
            await asyncio.sleep(0.5)
        else:
            # fallback: 고영표 (KT)
            print("\n  (선발투수 미정 → fallback: playerId=64001 고영표)")
            await test_player_profile(client, "64001")
            away_team, home_team = "KT", "NC"
            away_pid, home_pid = "64001", "56928"
            await asyncio.sleep(0.5)

        if away_pid and home_pid:
            await test_pitcher_analysis(client, away_team, away_pid, home_team, home_pid)

    print("\n" + "="*60)
    print("✓ 크롤링 테스트 완료")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
