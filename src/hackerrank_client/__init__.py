"""Package front door: import from here, not from deeper files."""

from .cache import CACHE_TTL_SECONDS, TTLCache
from .client import HackerRankAPI, HackerRankError, UpstreamError, UserNotFound
from .schemas import Badge, ContestEntry, HackerRankProfile, HeatmapDay
from .service import get_badges, get_contests, get_full_profile, get_heatmap

__all__ = [
    "CACHE_TTL_SECONDS",
    "TTLCache",
    "HackerRankAPI",
    "HackerRankError",
    "UpstreamError",
    "UserNotFound",
    "Badge",
    "ContestEntry",
    "HackerRankProfile",
    "HeatmapDay",
    "get_badges",
    "get_contests",
    "get_full_profile",
    "get_heatmap",
]
