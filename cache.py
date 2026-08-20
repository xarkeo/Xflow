
"""Thread-safe in-memory TTL cache used for idempotent API reads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CacheInfo:
    """A snapshot of cache usage counters."""

    hits: int
    misses: int
    size: int


@dataclass
class _Entry:
    expires_at: float
    value: object


class TTLCache:
    """A small, lock-protected in-memory TTL cache.

    Values are stored only for the lifetime of the Python process. The caller
    supplies cache keys that must not expose a token in observability output.
    """

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        self._hits = 0
        self._misses = 0
        self._lock = RLock()

    def get_or_set(self, key: str, ttl: float, factory: Callable[[], T]) -> T:
        """Return a non-expired cached value or create and cache it."""
        now = monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                self._hits += 1
                return entry.value  # type: ignore[return-value]
            if entry is not None:
                del self._entries[key]
            self._misses += 1

        value = factory()
        with self._lock:
            self._entries[key] = _Entry(expires_at=monotonic() + ttl, value=value)
        return value

    def clear(self) -> None:
        """Remove all cached values and reset usage counters."""
        with self._lock:
            self._entries.clear()
            self._hits = 0
            self._misses = 0

    def info(self) -> CacheInfo:
        """Return cache counters after removing expired entries."""
        now = monotonic()
        with self._lock:
            expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
            for key in expired:
                del self._entries[key]
            return CacheInfo(hits=self._hits, misses=self._misses, size=len(self._entries))
