"""Small website: look up one HackerRank user at a time.

Run:  python -m uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fastapi import FastAPI

from hackerrank_client import HackerRankAPI, get_full_profile

app = FastAPI(title="hackerrank-fetcher", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> dict:
    return {
        "service": "hackerrank-fetcher",
        "endpoints": ["/{username}/profile"],
    }


@app.get("/{username}/profile")
async def profile(username: str) -> dict:
    api = HackerRankAPI()
    try:
        return (await get_full_profile(username, api)).to_dict()
    finally:
        await api.close()
