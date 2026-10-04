"""Tests for the translators: clean format, empty history, no raw-key leaks."""

from __future__ import annotations

import asyncio
import json

import httpx

from hackerrank_client import HackerRankAPI, get_full_profile
from hackerrank_client.service import (
    decode_badges,
    decode_contests,
    decode_heatmap,
    decode_scores,
    decode_total_solved,
)


def run(coro):
    return asyncio.run(coro)


PROFILE_MODEL = {"username": "shashank21j", "name": "Shashank Sharma"}
SCORES = [
    {"slug": "algorithms", "practice": {"score": 6498.51, "rank": 2569}},
    {"slug": "python", "practice": {"score": 2305.0, "rank": 1}},
]
BADGE_MODELS = [
    {"badge_name": "Problem Solving", "badge_type": "problem-solving", "stars": 6, "solved": 202},
    {"badge_name": "Python", "badge_type": "python", "stars": 5, "solved": 115},
]
CONTESTS = {"models": [{"name": "Week 4", "slug": "w4"}], "total": 1}
SUBMISSIONS = {"2024-01-01": 3, "2024-01-02": 1}
RECENT = {"models": [], "cursor": None, "last_page": True}


def _router(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/profile"):
        payload: object = {"model": PROFILE_MODEL}
    elif "scores_elo" in path:
        payload = SCORES
    elif "/badges" in path:
        payload = {"status": True, "models": BADGE_MODELS}
    elif "contest_participation" in path:
        payload = CONTESTS
    elif "submission_histories" in path:
        payload = SUBMISSIONS
    elif "recent_challenges" in path:
        payload = RECENT
    else:
        payload = {}
    return httpx.Response(200, content=json.dumps(payload), request=request)


def test_full_profile_matches_stable_schema_only():
    api = HackerRankAPI(transport=httpx.MockTransport(_router))
    try:
        profile = run(get_full_profile("shashank21j", api))
        data = profile.to_dict()
        assert set(data.keys()) == {
            "username",
            "display_name",
            "badges",
            "practice_score",
            "total_solved",
            "contests",
        }
        assert data["username"] == "shashank21j"
        assert data["display_name"] == "Shashank Sharma"
        assert data["badges"] == [
            {"track": "Problem Solving", "stars": 6, "solved": 202},
            {"track": "Python", "stars": 5, "solved": 115},
        ]
        assert data["practice_score"] == int(6498.51 + 2305.0)
        assert data["total_solved"] == 202  # Problem Solving badge wins
        assert data["contests"] == [{"name": "Week 4", "slug": "w4"}]
        # Raw HackerRank keys must never leak into the clean format.
        blob = json.dumps(data)
        for raw in ("badge_type", "track_id", "hacker_rank", "ch_slug", "current_points"):
            assert raw not in blob
    finally:
        run(api.close())


def test_empty_history_yields_zeroes_and_empty_heatmap():
    assert decode_scores([]) == (0, {})
    assert decode_scores(None) == (0, {})
    assert decode_badges([]) == []
    assert decode_total_solved([]) == 0
    assert decode_heatmap({}) == []
    assert decode_contests({"models": []}) == []


def test_decode_tolerates_malformed_entries():
    badges = decode_badges([None, "x", {}, {"badge_name": "", "stars": "NaN"}])
    assert badges == []
    score, _ = decode_scores([None, {"practice": {"score": "bad"}}])
    assert score == 0
    assert decode_contests({"models": [None, {"name": ""}]}) == []
    days = decode_heatmap({"2024-01-01": "bad", "2024-01-02": 2})
    assert [(d.date, d.count) for d in days] == [("2024-01-02", 2)]
