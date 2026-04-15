"""A-6 — kbo_profile_harvester unit tests.

Mocks httpx.AsyncClient so the tests run offline. Covers:

1. Happy path — a normal search result + detail page → (kbo_player_id, photo_url).
2. Retired-pitcher fallback — no `PitcherDetail`, yields a `Retire/Pitcher` link.
3. Ambiguous hits — multiple `PitcherDetail` links, harvester picks first + warns.
4. No candidates — search result has zero playerId links → returns None.
5. HTTP error on the search GET → returns None, fails soft (no raise).
6. HTTP error on the detail GET → returns HarvestResult with None photo (id still harvested).
7. Detail page missing the CDN image → HarvestResult(kbo_id, None).
8. Missing hidden form field → returns None (can't POST without VIEWSTATE).
9. Empty name input → returns None, no HTTP calls.

All tests monkey-patch `_robots_allows` to bypass the real robots.txt fetch
(we are not testing robots behavior here — that is covered in crawler tests
indirectly). The rate-limit `asyncio.sleep` is also patched to a no-op so
the suite runs fast.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import kbo_profile_harvester as harvester
from app.services.kbo_profile_harvester import HarvestResult, harvest_profile


# ---------------------------------------------------------------------------
# HTML fixtures — just enough markup for BeautifulSoup to find the right tags.
# ---------------------------------------------------------------------------


def _search_page_html(viewstate: str = "VS", gen: str = "VG", ev: str = "EV") -> str:
    return f"""
    <html><body>
      <form>
        <input type="hidden" name="__VIEWSTATE" value="{viewstate}" />
        <input type="hidden" name="__VIEWSTATEGENERATOR" value="{gen}" />
        <input type="hidden" name="__EVENTVALIDATION" value="{ev}" />
      </form>
    </body></html>
    """


def _search_result_html(links: list[str]) -> str:
    anchors = "".join(f'<a href="{href}">link</a>' for href in links)
    return f"<html><body><table>{anchors}</table></body></html>"


def _detail_page_html(
    image_url: str | None = "//6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2026/77250.jpg",
) -> str:
    img_tag = f'<img src="{image_url}" />' if image_url else ""
    return f"<html><body><div class='player-info'>{img_tag}</div></body></html>"


# ---------------------------------------------------------------------------
# Response helpers — build fake httpx.Response objects.
# ---------------------------------------------------------------------------


def _resp(status: int, text: str) -> MagicMock:
    """Minimal mock for the `httpx.Response` fields our code touches.

    `raise_for_status` raises an `HTTPStatusError` for non-2xx statuses.
    """
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status
    mock.text = text
    if 200 <= status < 300:
        mock.raise_for_status = MagicMock(return_value=None)
    else:
        err = httpx.HTTPStatusError(
            f"http {status}",
            request=MagicMock(),
            response=MagicMock(status_code=status),
        )
        mock.raise_for_status = MagicMock(side_effect=err)
    return mock


def _make_async_client_mock(
    get_responses: dict[str, MagicMock | Exception] | None = None,
    post_responses: dict[str, MagicMock | Exception] | None = None,
) -> AsyncMock:
    """Build an `AsyncMock` that routes .get/.post by URL to the right response."""
    client = AsyncMock(spec=httpx.AsyncClient)

    async def _get(url: str, **kwargs: Any) -> MagicMock:
        if not get_responses:
            raise AssertionError(f"unexpected GET: {url}")
        for pattern, resp in get_responses.items():
            if pattern in url:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"no GET mock matched: {url}")

    async def _post(url: str, **kwargs: Any) -> MagicMock:
        if not post_responses:
            raise AssertionError(f"unexpected POST: {url}")
        for pattern, resp in post_responses.items():
            if pattern in url:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"no POST mock matched: {url}")

    client.get = _get  # type: ignore[method-assign]
    client.post = _post  # type: ignore[method-assign]
    return client


# ---------------------------------------------------------------------------
# Autouse fixtures — bypass robots + rate-limit sleep in every test.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bypass_robots_and_sleep():
    async def _always_true(*_args: Any, **_kwargs: Any) -> bool:
        return True

    async def _no_sleep(*_args: Any, **_kwargs: Any) -> None:
        return None

    with (
        patch.object(harvester, "_robots_allows", _always_true),
        patch("app.services.kbo_profile_harvester.asyncio.sleep", _no_sleep),
    ):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_harvest_happy_path_returns_id_and_photo():
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, _search_page_html()),
            "PitcherDetail": _resp(200, _detail_page_html()),
        },
        post_responses={
            "Player/Search.aspx": _resp(
                200,
                _search_result_html(
                    ["/Record/Player/PitcherDetail/Basic.aspx?playerId=77250"]
                ),
            ),
        },
    )

    result = await harvest_profile(client, "원태인", "SAM")
    assert result == HarvestResult(
        kbo_player_id=77250,
        profile_photo_url="https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2026/77250.jpg",
    )


@pytest.mark.asyncio
async def test_harvest_retired_pitcher_fallback():
    """No active PitcherDetail — fall through to Retire/Pitcher link."""
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, _search_page_html()),
            "Retire/Pitcher": _resp(200, _detail_page_html()),
        },
        post_responses={
            "Player/Search.aspx": _resp(
                200,
                _search_result_html(
                    ["/Record/Player/Retire/Pitcher.aspx?playerId=99123"]
                ),
            ),
        },
    )

    result = await harvest_profile(client, "홍길동", "LG")
    assert result is not None
    assert result.kbo_player_id == 99123


@pytest.mark.asyncio
async def test_harvest_ambiguous_multiple_hits_picks_first(caplog):
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, _search_page_html()),
            "PitcherDetail": _resp(200, _detail_page_html()),
        },
        post_responses={
            "Player/Search.aspx": _resp(
                200,
                _search_result_html(
                    [
                        "/Record/Player/PitcherDetail/Basic.aspx?playerId=11111",
                        "/Record/Player/PitcherDetail/Basic.aspx?playerId=22222",
                    ]
                ),
            ),
        },
    )

    with caplog.at_level("WARNING", logger="app.services.kbo_profile_harvester"):
        result = await harvest_profile(client, "김철수", "KT")

    assert result is not None
    assert result.kbo_player_id == 11111
    assert any("ambiguous" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_harvest_no_candidates_returns_none():
    """Search result has zero playerId links → miss."""
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, _search_page_html()),
        },
        post_responses={
            "Player/Search.aspx": _resp(200, "<html><body>No results</body></html>"),
        },
    )

    result = await harvest_profile(client, "없는사람", "LG")
    assert result is None


@pytest.mark.asyncio
async def test_harvest_search_get_error_returns_none():
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": httpx.ConnectError("connection refused"),
        },
    )

    result = await harvest_profile(client, "원태인", "SAM")
    assert result is None


@pytest.mark.asyncio
async def test_harvest_detail_get_error_still_returns_id():
    """Detail page fails → HarvestResult with id but no photo."""
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, _search_page_html()),
            "PitcherDetail": httpx.TimeoutException("read timeout"),
        },
        post_responses={
            "Player/Search.aspx": _resp(
                200,
                _search_result_html(
                    ["/Record/Player/PitcherDetail/Basic.aspx?playerId=77250"]
                ),
            ),
        },
    )

    result = await harvest_profile(client, "원태인", "SAM")
    assert result is not None
    assert result.kbo_player_id == 77250
    assert result.profile_photo_url is None


@pytest.mark.asyncio
async def test_harvest_detail_missing_image_returns_id_only():
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, _search_page_html()),
            "PitcherDetail": _resp(200, _detail_page_html(image_url=None)),
        },
        post_responses={
            "Player/Search.aspx": _resp(
                200,
                _search_result_html(
                    ["/Record/Player/PitcherDetail/Basic.aspx?playerId=77250"]
                ),
            ),
        },
    )

    result = await harvest_profile(client, "원태인", "SAM")
    assert result is not None
    assert result.kbo_player_id == 77250
    assert result.profile_photo_url is None


@pytest.mark.asyncio
async def test_harvest_missing_viewstate_returns_none():
    """If the search page lacks __VIEWSTATE, the harvester can't POST → None."""
    client = _make_async_client_mock(
        get_responses={
            "Player/Search.aspx": _resp(200, "<html><body>No form</body></html>"),
        },
    )

    result = await harvest_profile(client, "원태인", "SAM")
    assert result is None


@pytest.mark.asyncio
async def test_harvest_empty_name_returns_none_without_http():
    """No name → don't touch the network at all."""
    client = AsyncMock(spec=httpx.AsyncClient)

    result = await harvest_profile(client, "", "SAM")
    assert result is None
    client.get.assert_not_called()
    client.post.assert_not_called()
