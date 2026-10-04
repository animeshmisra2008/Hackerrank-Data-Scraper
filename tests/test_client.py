"""Tests with fake HackerRank answers (no internet needed).

Covers: unknown user -> user_not_found, quiet accounts get empty defaults,
broken answers -> upstream_error, recent list page merging (25-page guard).
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from hackerrank_client import HackerRankAPI, UpstreamError, UserNotFound


def make_api(handler) -> HackerRankAPI:
    return HackerRankAPI(transport=httpx.MockTransport(handler))


def run(coro):
    return asyncio.run(coro)


def _json_response(request: httpx.Request, status: int, payload) -> httpx.Response:
    body = payload if isinstance(payload, (bytes, str)) else json.dumps(payload)
    return httpx.Response(status, content=body, request=request)


def test_profile_404_raises_user_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(request, 404, {"error": "Not Found"})

    api = make_api(handler)
    try:
        with pytest.raises(UserNotFound):
            run(api.fetch_profile("ghost_user_xyz"))
    finally:
        run(api.close())


def test_unknown_user_maps_to_user_not_found_contract():
    """404 body must surface as user_not_found, never as upstream_error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(request, 404, {"error": "Not Found"})

    api = make_api(handler)
    try:
        with pytest.raises(UserNotFound) as exc:
            run(api.fetch_scores("ghost_user_xyz"))
        assert exc.value.code == "user_not_found"
    finally:
        run(api.close())


def test_badges_404_tolerated_with_default():
    def handler(request: httpx.Request) -> httpx.Response:
        if "badges" in request.url.path:
            return _json_response(request, 404, {"error": "Not Found"})
        return _json_response(request, 200, {"model": {"username": "u"}})

    api = make_api(handler)
    try:
        assert run(api.fetch_badges("quiet_user")) == []
    finally:
        run(api.close())


def test_badges_500_tolerated_with_default():
    def handler(request: httpx.Request) -> httpx.Response:
        if "badges" in request.url.path:
            return httpx.Response(500, content=b"boom", request=request)
        return _json_response(request, 200, {"model": {"username": "u"}})

    api = make_api(handler)
    try:
        assert run(api.fetch_badges("quiet_user")) == []
    finally:
        run(api.close())


def test_submissions_and_recent_tolerate_404_500():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "submission_histories" in path:
            return _json_response(request, 404, {"error": "Not Found"})
        if "recent_challenges" in path:
            return httpx.Response(500, content=b"boom", request=request)
        return _json_response(request, 200, {"model": {"username": "u"}})

    api = make_api(handler)
    try:
        assert run(api.fetch_submissions("quiet_user")) == {}
        assert run(api.fetch_recent("quiet_user")) == []
    finally:
        run(api.close())


def test_empty_history_decodes_to_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(request, 200, {})

    api = make_api(handler)
    try:
        assert run(api.fetch_submissions("new_user")) == {}
    finally:
        run(api.close())


def test_profile_bad_json_raises_upstream_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>", request=request)

    api = make_api(handler)
    try:
        with pytest.raises(UpstreamError) as exc:
            run(api.fetch_profile("someone"))
        assert exc.value.code == "upstream_error"
    finally:
        run(api.close())


def test_scores_403_raises_upstream_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(request, 403, {"error": "forbidden"})

    api = make_api(handler)
    try:
        with pytest.raises(UpstreamError):
            run(api.fetch_scores("someone"))
    finally:
        run(api.close())


def test_recent_pagination_aggregates_until_last_page():
    pages = {
        None: {"models": [{"name": "A"}], "cursor": "c1", "last_page": False},
        "c1": {"models": [{"name": "B"}], "cursor": None, "last_page": True},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("cursor")
        assert request.url.params.get("response_version") == "v2"
        return _json_response(request, 200, pages[cursor])

    api = make_api(handler)
    try:
        items = run(api.fetch_recent("u", limit=1))
        assert [m["name"] for m in items] == ["A", "B"]
    finally:
        run(api.close())


def test_recent_pagination_guard_stops_at_25_pages():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return _json_response(
            request,
            200,
            {"models": [{"name": f"C{calls['n']}"}], "cursor": f"next{calls['n']}", "last_page": False},
        )

    api = make_api(handler)
    try:
        items = run(api.fetch_recent("u", limit=1))
        assert len(items) == 25
        assert calls["n"] == 25
    finally:
        run(api.close())
