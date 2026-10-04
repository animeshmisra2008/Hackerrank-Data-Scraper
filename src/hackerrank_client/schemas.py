"""Our own clean data format.

HackerRank answers use messy keys like ``badge_type``, ``track_id``,
``hacker_rank`` — none of those may leave this package. Everything outside
(FastAPI, Student-Analytics) only ever sees the simple boxes below.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Badge:
    track: str
    stars: int
    solved: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ContestEntry:
    name: str
    slug: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HeatmapDay:
    date: str
    count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HackerRankProfile:
    """The one clean profile shape the website shows."""

    username: str
    display_name: str
    badges: list[Badge] = field(default_factory=list)
    practice_score: int = 0
    total_solved: int = 0
    contests: list[ContestEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "badges": [b.to_dict() for b in self.badges],
            "practice_score": self.practice_score,
            "total_solved": self.total_solved,
            "contests": [c.to_dict() for c in self.contests],
        }
