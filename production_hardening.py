"""Production-hardening helpers for Streckverket.

Pure functions keep state-integrity and performance instrumentation testable
without requiring Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Iterable, Any


def coupon_fingerprint(matches: Iterable[Any]) -> str:
    """Stable fingerprint for the coupon identity and core market inputs.

    Includes match number, teams, public shares and market availability/odds so
    an analysis result cannot silently survive a materially changed coupon.
    """
    parts: list[str] = []
    for m in matches:
        public = tuple(round(float(x), 6) for x in getattr(m, "public", ()))
        odds = tuple(round(float(x), 6) for x in getattr(m, "odds", ()))
        parts.append("|".join([
            str(getattr(m, "number", "")),
            str(getattr(m, "home", "")).strip().casefold(),
            str(getattr(m, "away", "")).strip().casefold(),
            repr(public),
            repr(odds),
            str(bool(getattr(m, "market_available", True))),
        ]))
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()


def analysis_matches_coupon(saved_fingerprint: str | None, matches: Iterable[Any]) -> bool:
    return bool(saved_fingerprint) and saved_fingerprint == coupon_fingerprint(matches)


@dataclass(frozen=True)
class TimingResult:
    label: str
    seconds: float


class Timer:
    """Tiny context manager for measuring real wall-clock duration."""

    def __init__(self, label: str):
        self.label = label
        self._start = 0.0
        self.result: TimingResult | None = None

    def __enter__(self):
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.result = TimingResult(self.label, max(0.0, perf_counter() - self._start))
        return False
