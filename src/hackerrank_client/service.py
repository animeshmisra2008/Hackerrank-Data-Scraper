"""Turn messy HackerRank answers into our clean boxes.

Each helper takes one raw payload and returns simple dataclasses.
Bad entries are skipped, never crash — HackerRank changes shapes often.
"""

from __future__ import annotations

from typing import Any

from .schemas import Badge, ContestEntry, HeatmapDay


def _num(value: Any, default: float = 0.0) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    return n


def decode_badges(models: Any) -> list[Badge]:
    badges: list[Badge] = []
    if not isinstance(models, list):
        return badges
    for m in models:
        if not isinstance(m, dict):
            continue
        track = str(
            m.get("badge_name") or m.get("badge_type") or m.get("name") or ""
        ).strip()
        if not track:
            continue
        badges.append(
            Badge(
                track=track,
                stars=int(_num(m.get("stars"), 0)),
                solved=int(_num(m.get("solved"), 0)),
            )
        )
    return badges


def decode_scores(scores: Any) -> tuple[int, dict[str, float]]:
    """Return (practice_score, per-track scores). practice_score adds up the
    practice points from every topic."""
    if not isinstance(scores, list):
        return 0, {}
    total = 0.0
    per_track: dict[str, float] = {}
    for entry in scores:
        if not isinstance(entry, dict):
            continue
        slug = str(entry.get("slug") or entry.get("name") or "").strip()
        practice = entry.get("practice") or {}
        score = _num(practice.get("score") if isinstance(practice, dict) else 0)
        total += score
        if slug:
            per_track[slug] = score
    return int(total), per_track


def decode_total_solved(badges: list[Badge]) -> int:
    """Use the Problem Solving badge (avoids counting problems twice),
    otherwise add up everything."""
    for b in badges:
        if b.track.lower() == "problem solving":
            return b.solved
    return sum(b.solved for b in badges)


def decode_contests(payload: Any) -> list[ContestEntry]:
    if not isinstance(payload, dict):
        return []
    models = payload.get("models", [])
    if not isinstance(models, list):
        return []
    out: list[ContestEntry] = []
    for m in models:
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or m.get("slug") or "").strip()
        if not name:
            continue
        out.append(ContestEntry(name=name, slug=str(m.get("slug") or "")))
    return out


def decode_heatmap(submissions: Any) -> list[HeatmapDay]:
    """Date -> count map becomes a sorted day list ([] when no history)."""
    if not isinstance(submissions, dict):
        return []
    days = [
        HeatmapDay(date=str(date), count=int(_num(count)))
        for date, count in submissions.items()
        if isinstance(count, (int, float))
    ]
    days.sort(key=lambda d: d.date)
    return days


def decode_profile_model(model: Any, fallback_username: str) -> tuple[str, str]:
    """Return (username, display name), falling back safely."""
    if not isinstance(model, dict):
        return fallback_username, fallback_username
    username = str(model.get("username") or fallback_username).strip()
    display = str(
        model.get("name")
        or model.get("personal_first_name")
        or model.get("display_name")
        or username
    ).strip()
    return username or fallback_username, display or username
