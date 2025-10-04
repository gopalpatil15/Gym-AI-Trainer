from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Tuple


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300) -> None:
        self._store: OrderedDict[str, CacheItem] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def _purge_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._store.items() if v.expires_at < now]
        for k in expired_keys:
            self._store.pop(k, None)

    def get(self, key: str) -> Tuple[bool, Any | None]:
        self._purge_expired()
        if key in self._store:
            item = self._store.pop(key)
            # move to end (most recently used)
            self._store[key] = item
            return True, item.value
        return False, None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        self._store[key] = CacheItem(value=value, expires_at=time.time() + ttl)
        self._store.move_to_end(key)
        self._evict_if_needed()

    def clear(self) -> None:
        self._store.clear()
