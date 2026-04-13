"""
Crawl KBO starting-pitcher profile images from two sources for local testing.

Sources:
  1. KBO official site (koreabaseball.com) — POSTs the ASP.NET search form,
     scrapes the resulting pitcher detail page for the profile image hosted on
     `6ptotvmi5753.edge.naverncp.com`.
  2. Namu Wiki (namu.wiki) — fetches the `/w/<title>` article, picks the first
     non-SVG `i.namu.wiki` image (the infobox main image). robots.txt allows
     `/w/` but may be subject to 429s.

Personal / local testing use only. Respects robots.txt at a coarse level:
Namu disallows everything except the explicitly-Allowed paths (we only hit
`/w/` and `i.namu.wiki`). KBO allows player pages.

CLAUDE.md §5 compliance: custom UA, <=1 req/sec per host, 1 retry on
transient errors, failures logged to manifest.
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

# --- config ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = PROJECT_ROOT / "data" / "pitcher_images"
KBO_DIR = OUT_ROOT / "kbo"
NAMU_DIR = OUT_ROOT / "namuwiki"
MANIFEST_PATH = OUT_ROOT / "manifest.json"

UA = "Mozilla/5.0 (compatible; Lucky-pocky-local-test/0.1; personal-use)"
TIMEOUT = 20.0
RATE_LIMIT_SEC = 1.05  # ≥1 req/sec per host

PITCHERS: list[str] = [
    "원태인",
    "곽빈",
    "네일",
    "카스타노",
    "손주영",
    "박세웅",
    "임찬규",
    "문동주",
    "양현종",
    "하트",
]

# Namu Wiki disambiguation: some short/common names hit the generic
# disambiguation page instead of the pitcher's article. Map them to the
# actual article title.
NAMU_TITLE_OVERRIDES: dict[str, str] = {
    "네일": "제임스 네일",
    "하트": "카일 하트",
    "카스타노": "다니엘 카스타노",
}

KBO_SEARCH_URL = "https://www.koreabaseball.com/Player/Search.aspx"
KBO_PROFILE_IMG_RE = re.compile(
    r"(?:https?:)?//6ptotvmi5753\.edge\.naverncp\.com/KBO_IMAGE/person/(?:middle|big|small)/\d+/\d+\.(?:jpg|jpeg|png|webp)",
    re.IGNORECASE,
)

# --- rate limiter ---------------------------------------------------------

class HostRateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        now = time.monotonic()
        last = self._last.get(host, 0.0)
        delay = self.min_interval - (now - last)
        if delay > 0:
            time.sleep(delay)
        self._last[host] = time.monotonic()


limiter = HostRateLimiter(RATE_LIMIT_SEC)


def throttled_request(client: httpx.Client, method: str, url: str, **kw) -> httpx.Response:
    host = httpx.URL(url).host
    limiter.wait(host)
    last_exc: Optional[Exception] = None
    for attempt in (1, 2):  # 1 retry on transient failure
        try:
            return client.request(method, url, **kw)
        except (httpx.TimeoutException, httpx.TransportError, httpx.NetworkError) as e:
            last_exc = e
            if attempt == 1:
                time.sleep(1.0)
                continue
            raise
    assert last_exc is not None  # unreachable
    raise last_exc


# --- manifest -------------------------------------------------------------

@dataclass
class ManifestEntry:
    index: int
    name: str
    source: str
    url: Optional[str]
    file: Optional[str]
    bytes: Optional[int]
    downloaded_at: str
    content_type: Optional[str] = None


@dataclass
class Manifest:
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)

    def ok(self, e: ManifestEntry) -> None:
        self.success.append(e.__dict__)

    def fail(self, index: int, name: str, source: str, reason: str, url: Optional[str] = None) -> None:
        self.failed.append({
            "index": index,
            "name": name,
            "source": source,
            "url": url,
            "reason": reason,
            "attempted_at": datetime.now(timezone.utc).isoformat(),
        })


# --- ext detection --------------------------------------------------------

_EXT_BY_CT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def detect_ext(url: str, content_type: Optional[str]) -> str:
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in _EXT_BY_CT:
            return _EXT_BY_CT[ct]
    m = re.search(r"\.(jpg|jpeg|png|webp|gif)(?:\?|$)", url, re.IGNORECASE)
    if m:
        e = m.group(1).lower()
        return ".jpg" if e == "jpeg" else f".{e}"
    return ".jpg"


# --- KBO ------------------------------------------------------------------

def _hidden(soup: BeautifulSoup, name: str) -> str:
    el = soup.find("input", {"name": name})
    return el.get("value", "") if el else ""


def kbo_image_candidates(middle_url: str) -> list[str]:
    """Given a KBO middle/big/small image URL, return fallback variants in order."""
    variants: list[str] = [middle_url]
    for size in ("big", "middle", "small"):
        alt = re.sub(r"/person/(middle|big|small)/", f"/person/{size}/", middle_url)
        if alt not in variants:
            variants.append(alt)
    return variants


def kbo_search_player(client: httpx.Client, name: str) -> Optional[str]:
    """Return the profile image URL for `name` from KBO official site, or None."""
    # step 1: GET search page to pull ASP.NET hidden state
    r = throttled_request(client, "GET", KBO_SEARCH_URL)
    if r.status_code != 200:
        raise RuntimeError(f"KBO search GET {r.status_code}")
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    prefix = "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$"
    data = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": _hidden(soup, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _hidden(soup, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _hidden(soup, "__EVENTVALIDATION"),
        f"{prefix}hfPage": "1",
        f"{prefix}ddlTeam": "",
        f"{prefix}ddlPosition": "",
        f"{prefix}txtSearchPlayerName": name,
        f"{prefix}btnSearch": "검색",
    }

    r2 = throttled_request(
        client, "POST", KBO_SEARCH_URL, data=data,
        headers={"Referer": KBO_SEARCH_URL, "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
    )
    if r2.status_code != 200:
        raise RuntimeError(f"KBO search POST {r2.status_code}")
    r2.encoding = "utf-8"
    soup2 = BeautifulSoup(r2.text, "html.parser")

    # find link with PitcherDetail for this name.
    # Priority:
    #   1. Active pitcher detail (PitcherDetail)
    #   2. Retired pitcher page (Retire/Pitcher) — KBO sometimes flags
    #      foreign pitchers who finished their contract as retired.
    #   3. Any other playerId link (skip Retire/Hitter — wrong position).
    pitcher_hits: list[str] = []
    retire_pitcher_hits: list[str] = []
    other_hits: list[str] = []
    for a in soup2.find_all("a", href=True):
        href = a["href"]
        if "playerId" not in href:
            continue
        if "PitcherDetail" in href:
            pitcher_hits.append(href)
        elif "Retire/Pitcher" in href:
            retire_pitcher_hits.append(href)
        elif "Retire" not in href:
            other_hits.append(href)
    candidates = pitcher_hits + retire_pitcher_hits + other_hits
    if not candidates:
        return None

    detail_url = urljoin("https://www.koreabaseball.com/", candidates[0])
    r3 = throttled_request(client, "GET", detail_url)
    if r3.status_code != 200:
        raise RuntimeError(f"KBO detail GET {r3.status_code}")
    r3.encoding = "utf-8"

    m = KBO_PROFILE_IMG_RE.search(r3.text)
    if not m:
        return None
    url = m.group(0)
    if url.startswith("//"):
        url = "https:" + url
    return url


# --- Namu Wiki ------------------------------------------------------------

def _unwrap_namu_src(raw: str) -> Optional[str]:
    if not raw:
        return None
    if raw.startswith("data:"):
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    if "i.namu.wiki" not in raw:
        return None
    if raw.lower().endswith(".svg"):
        return None  # skip vector placeholders/icons
    return raw


def namu_find_infobox_image(client: httpx.Client, title: str) -> Optional[str]:
    url = f"https://namu.wiki/w/{quote(title, safe='')}"
    r = throttled_request(
        client, "GET", url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
    )
    if r.status_code != 200:
        raise RuntimeError(f"namu GET {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")

    # Pick the first non-SVG i.namu.wiki image from the article — that's the
    # infobox main image in practice.
    for img in soup.find_all("img"):
        for attr in ("data-src", "src"):
            cand = _unwrap_namu_src(img.get(attr, ""))
            if cand:
                return cand
    return None


# --- downloader -----------------------------------------------------------

def download_image(client: httpx.Client, url: str, dest_dir: Path, stem: str, referer: Optional[str] = None) -> tuple[Path, int, str]:
    headers = {"Accept": "image/*,*/*;q=0.8"}
    if referer:
        headers["Referer"] = referer
    r = throttled_request(client, "GET", url, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"download {r.status_code}")
    ct = r.headers.get("Content-Type", "")
    ext = detect_ext(url, ct)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{stem}{ext}"
    path.write_bytes(r.content)
    return path, len(r.content), ct


# --- main -----------------------------------------------------------------

def main() -> int:
    # force utf-8 stdout on Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    KBO_DIR.mkdir(parents=True, exist_ok=True)
    NAMU_DIR.mkdir(parents=True, exist_ok=True)

    manifest = Manifest()

    with httpx.Client(
        timeout=TIMEOUT,
        headers={"User-Agent": UA},
        follow_redirects=True,
    ) as client:
        # --- KBO ---
        print("=" * 60)
        print("[KBO] searching via koreabaseball.com")
        print("=" * 60)
        for i, name in enumerate(PITCHERS, start=1):
            stem = f"{i:02d}_{name}"
            try:
                img_url = kbo_search_player(client, name)
                if not img_url:
                    print(f"  [{i:02d}] {name}: NOT FOUND in KBO search")
                    manifest.fail(i, name, "kbo", "no matching player or image in KBO search result")
                    continue
                path = None
                size = 0
                ct = ""
                used_url = img_url
                last_err: Optional[Exception] = None
                for cand in kbo_image_candidates(img_url):
                    try:
                        path, size, ct = download_image(
                            client, cand, KBO_DIR, stem,
                            referer="https://www.koreabaseball.com/",
                        )
                        used_url = cand
                        break
                    except Exception as e:
                        last_err = e
                        continue
                if path is None:
                    raise last_err if last_err else RuntimeError("no candidate succeeded")
                print(f"  [{i:02d}] {name}: OK ({size} bytes, {ct}) -> {path.name}")
                manifest.ok(ManifestEntry(
                    index=i, name=name, source="kbo",
                    url=used_url, file=str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    bytes=size, content_type=ct,
                    downloaded_at=datetime.now(timezone.utc).isoformat(),
                ))
            except Exception as e:
                print(f"  [{i:02d}] {name}: FAIL ({type(e).__name__}: {e})")
                manifest.fail(i, name, "kbo", f"{type(e).__name__}: {e}")

        # --- Namu Wiki ---
        print()
        print("=" * 60)
        print("[NAMU] fetching via namu.wiki/w/<name>")
        print("=" * 60)
        for i, name in enumerate(PITCHERS, start=1):
            stem = f"{i:02d}_{name}"
            namu_title = NAMU_TITLE_OVERRIDES.get(name, name)
            try:
                img_url = namu_find_infobox_image(client, namu_title)
                if not img_url:
                    print(f"  [{i:02d}] {name}: NO infobox image found (title={namu_title})")
                    manifest.fail(i, name, "namuwiki", f"no infobox image located in article (title={namu_title})")
                    continue
                path, size, ct = download_image(
                    client, img_url, NAMU_DIR, stem,
                    referer=f"https://namu.wiki/w/{quote(namu_title, safe='')}",
                )
                print(f"  [{i:02d}] {name}: OK ({size} bytes, {ct}) -> {path.name}")
                manifest.ok(ManifestEntry(
                    index=i, name=name, source="namuwiki",
                    url=img_url, file=str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    bytes=size, content_type=ct,
                    downloaded_at=datetime.now(timezone.utc).isoformat(),
                ))
            except Exception as e:
                print(f"  [{i:02d}] {name}: FAIL ({type(e).__name__}: {e})")
                manifest.fail(i, name, "namuwiki", f"{type(e).__name__}: {e}")

    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "generated_at": manifest.generated_at,
                "pitchers": PITCHERS,
                "success": manifest.success,
                "failed": manifest.failed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print(f"SUMMARY: success={len(manifest.success)} failed={len(manifest.failed)}")
    print(f"manifest -> {MANIFEST_PATH}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
