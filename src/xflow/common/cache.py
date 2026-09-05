"""XFlow 缓存层：内存 TTL 缓存 + 磁盘持久化。"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CacheInfo:
    """缓存使用计数快照。"""

    hits: int
    misses: int
    size: int


@dataclass
class _Entry:
    expires_at: float
    value: object


class TTLCache:
    """线程安全的内存 TTL 缓存。

    幂等 GET 才缓存。缓存 key 不含 token（用 token 哈希隔离）。
    """

    def __init__(self, disk_dir: str | None = None) -> None:
        self._entries: dict[str, _Entry] = {}
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()
        self._disk_dir = disk_dir

    def get_or_set(self, key: str, ttl: float, factory: Callable[[], T]) -> T:
        """返回未过期的缓存值，否则创建并缓存。"""
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                self._hits += 1
                return entry.value  # type: ignore[return-value]
            if entry is not None:
                del self._entries[key]
            self._misses += 1

        # 磁盘缓存查找
        if self._disk_dir:
            disk_value = self._load_disk(key)
            if disk_value is not None:
                with self._lock:
                    self._entries[key] = _Entry(expires_at=now + ttl, value=disk_value)
                return disk_value  # type: ignore[return-value]

        value = factory()
        with self._lock:
            self._entries[key] = _Entry(expires_at=time.monotonic() + ttl, value=value)
        if self._disk_dir:
            self._save_disk(key, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def info(self) -> CacheInfo:
        with self._lock:
            return CacheInfo(hits=self._hits, misses=self._misses, size=len(self._entries))

    def _disk_path(self, key: str) -> Path:
        import hashlib

        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return Path(self._disk_dir) / f"{digest}.json"

    def _load_disk(self, key: str) -> Any | None:
        try:
            path = self._disk_path(key)
            if not path.exists():
                return None
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_disk(self, key: str, value: Any) -> None:
        try:
            os.makedirs(self._disk_dir, exist_ok=True)
            path = self._disk_path(key)
            with path.open("w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
        except Exception:
            pass
