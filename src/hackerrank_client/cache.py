"""Small in-memory cache: remember answers for an hour.

No Redis, no passwords, just a dict with expiry times so opening the same
profile twice doesn't hit HackerRank twice.
"""

from __future__ import annotations

import threading
import time


CACHE_TTL_SECONDS = 3600  # 1 hour


class TTLCache:
    """Thread-safe dict where every entry expires after ``ttl`` seconds."""

    def __init__(self, ttl: int = CACHE_TTL_SECONDS) -> None:
        self.ttl = ttl
        self._items: dict[str, tuple[float | None, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires, value = item
            if expires is not None and expires < time.monotonic():
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: object, ttl: int | None = None) -> None:
        expires = time.monotonic() + (ttl if ttl is not None else self.ttl)
        with self._lock:
            self._items[key] = (expires, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
