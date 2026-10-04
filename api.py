"""Small website: look up one HackerRank user at a time.

Pages:  GET /{username}/profile   -> clean profile (stable)
        GET /{username}/badges    -> stars per topic (stable)
        GET /{username}/contests  -> contests (new, data is thin)
        GET /{username}/heatmap   -> daily activity (new, data is thin)

Unknown user -> 404 {"error": "user_not_found"}.
HackerRank broken -> 502 {"error": "upstream_error"}.

Run:  python -m uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hackerrank_client import (
    HackerRankAPI,
    UpstreamError,
    UserNotFound,
    get_badges,
    get_contests,
    get_full_profile,
    get_heatmap,
)

app = FastAPI(title="hackerrank-fetcher", version="0.1.0")


@app.exception_handler(UserNotFound)
async def _not_found(_: Request, exc: UserNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "user_not_found"})


@app.exception_handler(UpstreamError)
async def _upstream(_: Request, exc: UpstreamError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": "upstream_error"})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> dict:
    return {
        "service": "hackerrank-fetcher",
        "endpoints": [
            "/{username}/profile",
            "/{username}/badges",
            "/{username}/contests",
            "/{username}/heatmap",
        ],
    }


def _api() -> HackerRankAPI:
    return HackerRankAPI()


@app.get("/{username}/profile")
async def profile(username: str) -> dict:
    api = _api()
    try:
        return (await get_full_profile(username, api)).to_dict()
    finally:
        await api.close()


@app.get("/{username}/badges")
async def badges(username: str) -> dict:
    api = _api()
    try:
        items = await get_badges(username, api)
        return {"username": username, "badges": [b.to_dict() for b in items]}
    finally:
        await api.close()


@app.get("/{username}/contests")
async def contests(username: str) -> dict:
    api = _api()
    try:
        items = await get_contests(username, api)
        return {
            "username": username,
            "contests": [c.to_dict() for c in items],
            "note": "experimental — upstream contest_participation is thin",
        }
    finally:
        await api.close()


@app.get("/{username}/heatmap")
async def heatmap(username: str) -> dict:
    api = _api()
    try:
        days = await get_heatmap(username, api)
        return {
            "username": username,
            "days": [d.to_dict() for d in days],
            "note": "experimental — derived from submission_histories",
        }
    finally:
        await api.close()
