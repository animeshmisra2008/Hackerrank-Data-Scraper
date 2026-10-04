"""Talk to HackerRank's public pages (no login needed).

Proven endpoints (from tashifkhan/hackerrank-stats-api):
  PROFILE  /rest/contests/master/hackers/{u}/profile  -> {"model": {...}}
  SCORES   /rest/hackers/{u}/scores_elo               -> [...]
  BADGES   /rest/hackers/{u}/badges                   -> {"models": [...]}

One shared request helper. A missing user is UserNotFound; a quiet account
with no badges yet just gets [] instead of an error.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://www.hackerrank.com"
TIMEOUT = 20.0

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

# Endpoints allowed to be empty: a 404/500 or broken answer here returns an
# empty default instead of failing the whole profile.
_TOLERANT_ENDPOINTS = {"badges"}


class HackerRankError(RuntimeError):
    code = "upstream_error"


class UserNotFound(HackerRankError):
    """HackerRank said 404: this username does not exist."""

    code = "user_not_found"


class UpstreamError(HackerRankError):
    """HackerRank answered with an error, or something else went wrong."""

    code = "upstream_error"

    def __init__(self, message: str = "upstream_error", status: int = 0) -> None:
        super().__init__(message)
        self.status = status


def _safe_json(response: httpx.Response) -> Any | None:
    try:
        return response.json()
    except Exception:
        return None


class HackerRankAPI:
    """Small wrapper around httpx. One instance, close it when done."""

    def __init__(self, timeout: float = TIMEOUT, transport=None) -> None:
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            headers=HEADERS,
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get_json(self, url: str, *, kind: str, default: Any = None) -> Any:
        """GET url and return its JSON.

        Unknown user -> UserNotFound. Anything else bad -> UpstreamError,
        except endpoints in _TOLERANT_ENDPOINTS which quietly return
        ``default`` on 404/500/broken answers.
        """
        response = await self._client.get(url)
        status = response.status_code
        if status == 404:
            if kind in _TOLERANT_ENDPOINTS:
                return default
            raise UserNotFound(f"user_not_found: {url}")
        if status != 200:
            if status == 500 and kind in _TOLERANT_ENDPOINTS:
                return default
            raise UpstreamError("upstream_error", status=status)
        payload = _safe_json(response)
        if payload is None:
            if kind in _TOLERANT_ENDPOINTS:
                return default
            raise UpstreamError("upstream_error", status=status)
        return payload

    async def fetch_profile(self, username: str) -> dict:
        """GET the profile -> the ``model`` dict."""
        payload = await self._get_json(
            f"{BASE_URL}/rest/contests/master/hackers/{username}/profile",
            kind="profile",
        )
        model = payload.get("model") if isinstance(payload, dict) else None
        return model if isinstance(model, dict) else {}

    async def fetch_scores(self, username: str) -> list:
        """GET /rest/hackers/{u}/scores_elo -> list of per-track scores."""
        payload = await self._get_json(
            f"{BASE_URL}/rest/hackers/{username}/scores_elo", kind="scores"
        )
        return payload if isinstance(payload, list) else []

    async def fetch_badges(self, username: str) -> list:
        """GET /rest/hackers/{u}/badges -> the ``models`` list ([] if none)."""
        payload = await self._get_json(
            f"{BASE_URL}/rest/hackers/{username}/badges",
            kind="badges",
            default={"models": []},
        )
        if isinstance(payload, dict):
            models = payload.get("models", [])
            return models if isinstance(models, list) else []
        return []
