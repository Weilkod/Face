# KBO 공식 사이트 크롤링 가이드

> Playwright 불필요. httpx (또는 requests) POST/GET만으로 전부 가능.
> KBO 공식 사이트는 ASP.NET Web Forms 기반이지만, 내부적으로 JSON API (ASMX 웹서비스)를 사용한다.
> 브라우저 DevTools → Network → Fetch/XHR 필터로 발견함 (2026-04-13 확인).

---

## 1. 월간 일정 — GetScheduleList

### 엔드포인트
```
POST https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList
Content-Type: application/x-www-form-urlencoded
```

### 파라미터
| Key | 값 예시 | 설명 |
|---|---|---|
| `leId` | `1` | KBO 리그 |
| `srIdList` | `0,9,6` | 시리즈 종류 (0=정규시즌, 9/6=기타) |
| `seasonId` | `2026` | 시즌 연도 |
| `gameMonth` | `04` | 월 (2자리) |
| `teamId` | (빈값) | 빈값 = 전체팀, 특정팀 필터 가능 |

### 응답 구조 (JSON)
```json
{
  "rows": [
    {
      "row": [
        { "Text": "04.01(수)", "Class": "day", "RowSpan": "5" },   // 날짜 (RowSpan = 그날 경기 수)
        { "Text": "<b>18:30</b>", "Class": "time" },                // 경기 시간
        { "Text": "<span>KIA</span><em>...</em><span>LG</span>", "Class": "play" },  // 팀 매칭
        { "Text": "<a href='...gameId=20260401HTLG0...'...", "Class": "relay" },      // gameId 포함
        { "Text": "...", "Class": null },                            // 하이라이트 링크
        { "Text": "KN-T", "Class": null },                          // 중계 채널
        { "Text": "", "Class": null },                               // (빈칸)
        { "Text": "잠실", "Class": null },                           // 구장
        { "Text": "-", "Class": null }                               // 상태 ("-" 또는 "우천취소")
      ]
    }
  ]
}
```

### 파싱 방법
- `Class: "day"` → 날짜. `RowSpan`으로 해당 날짜의 경기 수 파악
- `Class: "time"` → `<b>18:30</b>`에서 시간 추출
- `Class: "play"` → HTML 파싱: 첫 `<span>` = 원정팀, 두 번째 `<span>` = 홈팀. 점수는 `<span class="win">` / `<span class="lose">`
- `Class: "relay"` → href에서 `gameId` 추출 (예: `20260401HTLG0`)
- 뒤에서 두 번째 셀 → 구장명
- 마지막 셀 → `"우천취소"` 또는 `"-"` (정상)

### 주의사항
- **선발투수 정보 없음** — 이 API는 일정/결과만 제공
- 팀 코드는 gameId 안에 KBO 내부 코드로 들어감 (HT=KIA, OB=두산, SK=SSG 등)

---

## 2. 오늘 경기 목록 — GetTodayGames ⭐ (가장 유용)

### 엔드포인트
```
POST https://www.koreabaseball.com/ws/Schedule.asmx/GetTodayGames
Content-Type: application/x-www-form-urlencoded
```

### 파라미터
| Key | 값 예시 | 설명 |
|---|---|---|
| `gameDate` | `20260414` | 조회 날짜 (YYYYMMDD) |
| `leId` | `1` | KBO 리그 |
| `srId` | `0,1,3,4,5,7` | 시리즈 ID 목록 |
| `headerCk` | `0` | 헤더 체크 (고정값) |

### 응답 구조 (JSON) — 깔끔한 구조화 데이터
```json
{
  "dateDiff": 1,
  "gameList": [
    {
      "stadium": "JS",
      "stadiumFullName": "잠실야구장",
      "homeCode": "LG",
      "homeName": "LG 트윈스",
      "awayCode": "LT",
      "awayName": "롯데 자이언츠",
      "gameTime": "18:30:00",
      "gameSc": 0,
      "cancelSc": 0,
      "icon": "2",
      "iconName": "구름조금",
      "temp": 25.0,
      "rain": 20,
      "gameId": "20260414LTLG0",
      "dust": "",
      "dustCode": ""
    }
  ]
}
```

### 팀 코드 매핑 (KBO 내부 코드 → 서비스 코드)
```
LG → LG        SK → SSG       OB → DS (두산)
HT → KIA       WO → KW (키움)  SS → SAM (삼성)
LT → LOT (롯데) NC → NC        KT → KT
HH → HH (한화)
```

### 주의사항
- **선발투수 정보 없음** — gameId를 이용해 별도 조회 필요
- `cancelSc: 1` → 경기 취소
- `gameSc: 0` = 경기 전, 값이 있으면 진행/종료

---

## 3. 선발투수 정보 — GameCenter HTML 파싱

### 방법
GetTodayGames에서 받은 `gameId`로 GameCenter 메인 페이지를 GET 요청한 뒤,
HTML 안의 `<li class="game-cont">` 요소에서 선발투수 ID를 추출한다.

### 엔드포인트
```
GET https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx?gameDate={YYYYMMDD}&gameId={gameId}&section=START_PIT
```

예시:
```
GET https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx?gameDate=20260414&gameId=20260414LTLG0&section=START_PIT
```

### HTML에서 추출할 속성
`<li>` 태그 (class="game-cont") 안에 다음 속성이 있음:

```html
<li class="game-cont"
    game_sc="1"
    le_id="1"
    sr_id="0"
    season="2026"
    g_dt="20260414"
    s_nm="창원"              <!-- 구장 약칭 -->
    vs_game_cn="1"
    away_id="KT"             <!-- 원정팀 코드 -->
    home_id="NC"             <!-- 홈팀 코드 -->
    away_p_id="64001"        <!-- ⭐ 원정 선발투수 KBO ID -->
    home_p_id="56928"        <!-- ⭐ 홈 선발투수 KBO ID -->
    entry_ck="0"
    start_ck="..."
    vod_ck="0"
    kbot_se="0">
```

### 파싱 코드 (Python + BeautifulSoup)
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
games = soup.select("li.game-cont")
for game in games:
    away_team = game.get("away_id")       # "KT"
    home_team = game.get("home_id")       # "NC"
    away_pitcher_id = game.get("away_p_id")  # "64001"
    home_pitcher_id = game.get("home_p_id")  # "56928"
    game_date = game.get("g_dt")          # "20260414"
    stadium = game.get("s_nm")            # "창원"
```

### 주의사항
- 선발투수가 미정이면 `away_p_id` / `home_p_id`가 빈값 또는 "0"일 수 있음
- 투수 ID로 이름을 알려면 선수 프로필 API를 별도 조회하거나, 시즌 초 시드 시 ID↔이름 매핑 테이블 구축 필요
- 이 페이지는 일반 GET 요청으로 HTML이 오므로 httpx.get()으로 충분

---

## 4. 선발투수 상세 기록 — GetPitcherRecordAnalysis

### 엔드포인트
```
POST https://www.koreabaseball.com/ws/Schedule.asmx/GetPitcherRecordAnalysis
Content-Type: application/x-www-form-urlencoded
```

### 파라미터
| Key | 값 예시 | 설명 |
|---|---|---|
| `leId` | `1` | 리그 ID |
| `srId` | `0` | 시리즈 ID |
| `seasonId` | `2026` | 시즌 |
| `awayTeamId` | `KT` | 원정팀 코드 |
| `awayPitId` | `64001` | 원정 선발투수 ID (away_p_id) |
| `homeTeamId` | `NC` | 홈팀 코드 |
| `homePitId` | `56928` | 홈 선발투수 ID (home_p_id) |
| `groupSc` | `SEASON` | 그룹 (SEASON / HOMEAWAY / VS) |

### 응답
투수 성적 비교 테이블 (ERA, WAR, 경기수, QS, WHIP 등) — GetScheduleList와 같은 rows 형태.

---

## 5. 추천 크롤링 파이프라인

### 일일 스케줄러 (매일 08:00, 09:00, 10:00 KST)

```
1. GetTodayGames (POST)
   → gameDate=오늘, leId=1, srId=0,1,3,4,5,7, headerCk=0
   → 오늘 경기 5개의 homeCode, awayCode, stadium, gameTime, gameId 획득

2. 각 gameId로 GameCenter 페이지 GET
   → li.game-cont에서 away_p_id, home_p_id 추출
   → 빈값이면 선발 미정 (09:00/10:00에 재시도)

3. pitcher_id로 DB 매칭 또는 선수 프로필 조회
   → 이름, 생년월일 등 확보
```

### 시즌 초 1회성 시드 (선수 DB 구축)

```
1. KBO 선수 목록 페이지에서 전체 투수 ID/이름/팀 수집
2. 각 선수 프로필 페이지에서 생년월일, 사진 URL 등 수집
3. pitchers 테이블에 upsert
```

---

## 6. HTTP 요청 시 필수 헤더

```python
headers = {
    "User-Agent": "FACEMETRICS/0.1 (+research)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "X-Requested-With": "XMLHttpRequest",  # ASMX가 이걸 체크할 수 있음
}
```

### Rate Limit
- CLAUDE.md §5 준수: ≤1 req/sec per host
- robots.txt 프리체크 (`_robots_allows()` 함수 사용)

---

## 7. 선수 프로필 (이름, 사진, 생년월일) — Player Detail 페이지

### 엔드포인트
```
GET https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId={playerId}
```

예시:
```
GET https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=64001
→ 고영표 (KT 위즈) 프로필 페이지
```

### playerId 획득 방법
- GameCenter HTML의 `<li class="game-cont">`에서 `away_p_id` / `home_p_id` 속성 (§3 참조)
- 시즌 초 선수 목록 페이지에서 일괄 수집

### HTML에서 추출할 데이터

#### 선수 사진
```html
<div class="player_basic">
  <div class="photo">
    <img id="cphContents_cphContents_cphContents_playerProfile_imgProfile"
         src="//6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2026/64001.jpg"
         alt="고영표"
         onerror="this.src='//6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/KBOHome/resources/images/common/no-image.png'">
  </div>
</div>
```

**사진 URL 패턴:**
```
https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/{시즌}/{playerId}.jpg
```
→ playerId만 알면 페이지를 파싱하지 않고 직접 이미지 URL을 조립할 수도 있음!

**선수 이름:** `<img>` 태그의 `alt` 속성에서 추출 (`alt="고영표"`)

#### 생년월일
```html
<li class="odd">
  <strong>생년월일: </strong>
  <span id="cphContents_cphContents_cphContents_playerProfile_lblBirthday">1991년 09월 16일</span>
</li>
```

#### 팀 엠블럼 (보너스)
```
https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/emblem/regular/2026/emblem_KT.png
```

### 파싱 코드 (Python + BeautifulSoup)
```python
import httpx
from bs4 import BeautifulSoup
import re
from datetime import date

async def get_pitcher_profile(player_id: int) -> dict:
    url = f"https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId={player_id}"
    async with httpx.AsyncClient(headers=UA_HEADER, timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 이름 + 사진
    img = soup.select_one("div.photo img")
    name = img.get("alt", "") if img else ""
    photo_url = img.get("src", "") if img else ""
    if photo_url.startswith("//"):
        photo_url = "https:" + photo_url

    # 생년월일
    birthday_span = soup.find("span", id=re.compile(r"lblBirthday"))
    birthday_text = birthday_span.get_text(strip=True) if birthday_span else ""
    # "1991년 09월 16일" → date(1991, 9, 16)
    m = re.match(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", birthday_text)
    birthday = date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

    return {
        "player_id": player_id,
        "name": name,
        "photo_url": photo_url,
        "birthday": birthday,
    }
```

### 사진 URL 직접 조립 (페이지 파싱 없이)
```python
def pitcher_photo_url(player_id: int, season: int = 2026) -> str:
    return f"https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/{season}/{player_id}.jpg"
```
→ 이미지가 없으면 404가 올 수 있으므로 HEAD 요청으로 존재 여부 확인 후 폴백 처리

### 시즌 초 전체 투수 시드 파이프라인
```
1. KBO 투수 기록 페이지에서 전체 투수 목록 수집
   GET https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic.aspx
   (Network 탭에서 페이지네이션 XHR 확인 필요)

2. 각 투수의 playerId로 프로필 페이지 GET
   → 이름, 생년월일, 사진 URL 추출

3. 생년월일에서 별자리(constellation) + 띠(zodiac) 자동 계산
   → pitchers 테이블에 upsert

4. 사진은 URL만 DB에 저장 (CDN 직접 링크)
   또는 로컬에 다운로드해서 서빙
```

---

## 8. 이전 시도에서 401이 났던 이유

이전 세션에서 `/ws/Schedule.asmx/GetScheduleList`에 401이 난 이유:
- `Content-Type`이 `application/json`이었음 (ASMX는 `application/x-www-form-urlencoded` 필요)
- `X-Requested-With: XMLHttpRequest` 헤더 누락 가능
- `Referer` 헤더 누락 (일부 ASMX 서비스가 체크)

위 헤더를 정확히 설정하면 httpx POST로 정상 200 응답.

---

## 9. 팀 코드 전체 매핑

| KBO 내부 코드 | 팀 이름 | 서비스 코드 |
|---|---|---|
| `LG` | LG 트윈스 | `LG` |
| `SK` | SSG 랜더스 | `SSG` |
| `OB` | 두산 베어스 | `DS` |
| `HT` | KIA 타이거즈 | `KIA` |
| `WO` | 키움 히어로즈 | `KW` |
| `SS` | 삼성 라이온즈 | `SAM` |
| `LT` | 롯데 자이언츠 | `LOT` |
| `NC` | NC 다이노스 | `NC` |
| `KT` | KT 위즈 | `KT` |
| `HH` | 한화 이글스 | `HH` |
