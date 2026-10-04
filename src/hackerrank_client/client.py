"""Talk to HackerRank's public pages (no login needed).

Proven endpoint (from tashifkhan/hackerrank-stats-api):
  PROFILE  /rest/contests/master/hackers/{u}/profile  -> {"model": {...}}

First version: profile + scores + badges. More endpoints next.
"""

from __future__ import annotations

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

    async def fetch_profile(self, username: str) -> dict:
        """GET the profile -> the ``model`` dict.

        Unknown user raises UserNotFound, anything else bad raises UpstreamError.
        """
        url = f"{BASE_URL}/rest/contests/master/hackers/{username}/profile"
        response = await self._client.get(url)
        if response.status_code == 404:
            raise UserNotFound(f"user_not_found: {username}")
        if response.status_code != 200:
            raise UpstreamError("upstream_error", status=response.status_code)
        try:
            payload = response.json()
        except Exception as exc:
            raise UpstreamError("upstream_error") from exc
        model = payload.get("model") if isinstance(payload, dict) else None
        return model if isinstance(model, dict) else {}

    async def fetch_scores(self, username: str) -> list:
        """GET /rest/hackers/{u}/scores_elo -> list of per-track scores."""
        url = f"{BASE_URL}/rest/hackers/{username}/scores_elo"
        response = await self._client.get(url)
        if response.status_code == 404:
            raise UserNotFound(f"user_not_found: {username}")
        if response.status_code != 200:
            raise UpstreamError("upstream_error", status=response.status_code)
        try:
            payload = response.json()
        except Exception as exc:
            raise UpstreamError("upstream_error") from exc
        return payload if isinstance(payload, list) else []

    async def fetch_badges(self, username: str) -> list:
        """GET /rest/hackers/{u}/badges -> the ``models`` list."""
        url = f"{BASE_URL}/rest/hackers/{username}/badges"
        response = await self._client.get(url)
        if response.status_code == 404:
            raise UserNotFound(f"user_not_found: {username}")
        if response.status_code != 200:
            raise UpstreamError("upstream_error", status=response.status_code)
        try:
            payload = response.json()
        except Exception as exc:
            raise UpstreamError("upstream_error") from exc
        if isinstance(payload, dict):
            models = payload.get("models", [])
            return models if isinstance(models, list) else []
        return []
