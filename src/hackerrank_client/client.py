"""Raw HackerRank HTTP client (unofficial REST endpoints, no auth).

Proven endpoints (from tashifkhan/hackerrank-stats-api/services/client.py):
  PROFILE     /rest/contests/master/hackers/{u}/profile            -> {"model": {...}}
  SCORES      /rest/hackers/{u}/scores_elo                         -> [...]
  BADGES      /rest/hackers/{u}/badges                             -> {"models": [...]}
  CONTESTS    /rest/hackers/{u}/contest_participation?offset=&limit-> {"models": [...], "total": N}
  RATINGS     /rest/hackers/{u}/rating_histories_elo               -> {"models": [...]}
  SUBMISSIONS /rest/hackers/{u}/submission_histories                -> {"YYYY-MM-DD": count}
  RECENT      /rest/hackers/{u}/recent_challenges?limit=&response_version=v2 (cursor-paginated)

Error contract:
  404 on profile/scores/contests/ratings -> UserNotFound("user_not_found")
  404/500 on badges/submissions/recent   -> tolerated, caller gets a default
  any other >= 400                       -> UpstreamError("upstream_error")
  bad JSON on a required payload         -> UpstreamError("upstream_error")
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

BASE_URL = "https://www.hackerrank.com"
TIMEOUT = 20.0
CACHE_TTL_SECONDS = 3600
MAX_RECENT_PAGES = 25  # cursor pagination guard for /recent_challenges
MAX_RETRIES = 2
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

# Endpoints that may be empty for new/quiet accounts: a 404/500 here must
# never fail the whole profile — the service layer substitutes a default.
_TOLERANT_ENDPOINTS = {"badges", "submissions", "recent"}


class HackerRankError(RuntimeError):
    code = "upstream_error"


class UserNotFound(HackerRankError):
    code = "user_not_found"


class UpstreamError(HackerRankError):
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
    """Async raw client. One instance per process; cached TTL 3600."""

    def __init__(
        self,
        timeout: float = TIMEOUT,
        cache=None,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        from .cache import TTLCache

        self.timeout = timeout
        self.cache = cache or TTLCache(ttl=CACHE_TTL_SECONDS)
        self._client = httpx.AsyncClient(
            headers=HEADERS,
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "HackerRankAPI":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # -- internals ------------------------------------------------------

    def _profile_url(self, username: str) -> str:
        return f"{BASE_URL}/rest/contests/master/hackers/{username}/profile"

    def _url(self, username: str, kind: str, **kw: Any) -> str:
        if kind == "scores":
            return f"{BASE_URL}/rest/hackers/{username}/scores_elo"
        if kind == "badges":
            return f"{BASE_URL}/rest/hackers/{username}/badges"
        if kind == "contests":
            offset = kw.get("offset", 0)
            limit = kw.get("limit", 50)
            return (
                f"{BASE_URL}/rest/hackers/{username}/contest_participation"
                f"?offset={offset}&limit={limit}"
            )
        if kind == "ratings":
            return f"{BASE_URL}/rest/hackers/{username}/rating_histories_elo"
        if kind == "submissions":
            return f"{BASE_URL}/rest/hackers/{username}/submission_histories"
        if kind == "recent":
            limit = kw.get("limit", 100)
            cursor = kw.get("cursor")
            url = (
                f"{BASE_URL}/rest/hackers/{username}/recent_challenges"
                f"?limit={limit}&response_version=v2"
            )
            if cursor:
                url += f"&cursor={cursor}"
            return url
        raise ValueError(f"unknown endpoint kind: {kind}")

    async def _get_json(
        self,
        url: str,
        *,
        kind: str,
        default: Any = None,
    ) -> Any:
        """GET + cache + retries. Raises UserNotFound / UpstreamError."""
        cached = self.cache.get(url)
        if cached is not None:
            try:
                return json.loads(cached)
            except (TypeError, ValueError):
                pass  # corrupt entry — refetch

        last_status = 0
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._client.get(url)
            except httpx.TransportError as exc:
                if attempt >= MAX_RETRIES:
                    raise UpstreamError("upstream_error") from exc
                await asyncio.sleep(2**attempt)
                continue

            status = response.status_code
            last_status = status
            if status == 200:
                payload = _safe_json(response)
                if payload is None:
                    if kind in _TOLERANT_ENDPOINTS:
                        return default
                    raise UpstreamError("upstream_error", status=status)
                try:
                    self.cache.set(
                        url, json.dumps(payload, default=str), CACHE_TTL_SECONDS
                    )
                except (TypeError, ValueError):
                    pass
                return payload
            if status == 404:
                if kind in _TOLERANT_ENDPOINTS:
                    return default
                raise UserNotFound(f"user_not_found: {url}")
            if status == 500 and kind in _TOLERANT_ENDPOINTS:
                return default  # tolerated per spec
            if status in RETRYABLE_STATUS:
                if attempt >= MAX_RETRIES:
                    if kind in _TOLERANT_ENDPOINTS and status >= 500:
                        return default
                    raise UpstreamError("upstream_error", status=status)
                await asyncio.sleep(2**attempt)
                continue
            # Any other >= 400 is a definitive upstream error.
            raise UpstreamError("upstream_error", status=status)

        raise UpstreamError("upstream_error", status=last_status)

    # -- raw fetches (return decoded JSON, never httpx objects) --------

    async def fetch_profile(self, username: str) -> dict:
        payload = await self._get_json(
            self._profile_url(username), kind="profile"
        )
        model = payload.get("model") if isinstance(payload, dict) else None
        return model if isinstance(model, dict) else {}

    async def fetch_scores(self, username: str) -> list:
        payload = await self._get_json(
            self._url(username, "scores"), kind="scores"
        )
        return payload if isinstance(payload, list) else []

    async def fetch_badges(self, username: str) -> list:
        payload = await self._get_json(
            self._url(username, "badges"), kind="badges", default={"models": []}
        )
        if isinstance(payload, dict):
            models = payload.get("models", [])
            return models if isinstance(models, list) else []
        return []

    async def fetch_contests(self, username: str) -> dict:
        payload = await self._get_json(
            self._url(username, "contests"), kind="contests"
        )
        return payload if isinstance(payload, dict) else {"models": [], "total": 0}

    async def fetch_ratings(self, username: str) -> dict:
        payload = await self._get_json(
            self._url(username, "ratings"), kind="ratings"
        )
        return payload if isinstance(payload, dict) else {"models": []}

    async def fetch_submissions(self, username: str) -> dict:
        payload = await self._get_json(
            self._url(username, "submissions"),
            kind="submissions",
            default={},
        )
        # Date -> count map; empty history is normal for new accounts.
        if isinstance(payload, dict):
            return {
                str(k): v
                for k, v in payload.items()
                if isinstance(v, (int, float))
            }
        return {}

    async def fetch_recent(self, username: str, limit: int = 100) -> list:
        """Aggregate cursor-paginated recent challenges (max 25 pages)."""
        items: list[dict] = []
        cursor: str | None = None
        for _ in range(MAX_RECENT_PAGES):
            payload = await self._get_json(
                self._url(username, "recent", limit=limit, cursor=cursor),
                kind="recent",
                default={"models": []},
            )
            if not isinstance(payload, dict):
                break
            models = payload.get("models", [])
            if isinstance(models, list):
                items.extend(m for m in models if isinstance(m, dict))
            cursor = payload.get("cursor")
            last_page = payload.get("last_page", True)
            if last_page or not cursor:
                break
        return items
