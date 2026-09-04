from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any, Callable, Hashable


@dataclass(frozen=True)
class CachePolicy:
    name: str
    ttl_seconds: int


@dataclass(frozen=True)
class CacheStats:
    network_calls: int
    cache_hits: int
    cache_misses: int


_CACHE: dict[tuple[str, Hashable], tuple[float, Any]] = {}
_LOCK = RLock()
_NETWORK_CALLS = 0
_CACHE_HITS = 0
_CACHE_MISSES = 0


def cached_call(policy: CachePolicy, key: Hashable, loader: Callable[[], Any]) -> Any:
    """Small process-local TTL cache for external API reads.

    The cache is deliberately explicit: every caller chooses a policy and key.
    Failed loaders are never cached.
    """
    global _NETWORK_CALLS, _CACHE_HITS, _CACHE_MISSES
    cache_key = (policy.name, key)
    now = monotonic()
    with _LOCK:
        hit = _CACHE.get(cache_key)
        if hit is not None and now < hit[0]:
            _CACHE_HITS += 1
            return hit[1]
        if hit is not None:
            _CACHE.pop(cache_key, None)
        _CACHE_MISSES += 1
    value = loader()
    with _LOCK:
        _NETWORK_CALLS += 1
        _CACHE[cache_key] = (monotonic() + max(0, policy.ttl_seconds), value)
    return value


def cache_stats() -> CacheStats:
    with _LOCK:
        return CacheStats(_NETWORK_CALLS, _CACHE_HITS, _CACHE_MISSES)


def stats_delta(before: CacheStats, after: CacheStats) -> CacheStats:
    return CacheStats(
        after.network_calls - before.network_calls,
        after.cache_hits - before.cache_hits,
        after.cache_misses - before.cache_misses,
    )


def clear_cache() -> None:
    global _NETWORK_CALLS, _CACHE_HITS, _CACHE_MISSES
    with _LOCK:
        _CACHE.clear()
        _NETWORK_CALLS = _CACHE_HITS = _CACHE_MISSES = 0
