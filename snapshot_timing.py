from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class SnapshotTiming:
    hours_before_kickoff: float | None
    bucket: str
    label: str
    eligible_pre_match: bool


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def classify_snapshot_timing(captured_at: str | None, kickoff: str | None) -> SnapshotTiming:
    captured = _parse_dt(captured_at)
    start = _parse_dt(kickoff)
    if captured is None or start is None:
        return SnapshotTiming(None, "UNKNOWN", "Tid saknas", False)

    hours = (start - captured).total_seconds() / 3600.0
    if hours < 0:
        return SnapshotTiming(hours, "POST_KICKOFF", "Efter avspark", False)
    if hours <= 1:
        return SnapshotTiming(hours, "LE_1H", "Inom 1 h före avspark", True)
    if hours <= 3:
        return SnapshotTiming(hours, "1_3H", "1–3 h före avspark", True)
    if hours <= 12:
        return SnapshotTiming(hours, "3_12H", "3–12 h före avspark", True)
    if hours <= 24:
        return SnapshotTiming(hours, "12_24H", "12–24 h före avspark", True)
    if hours <= 72:
        return SnapshotTiming(hours, "24_72H", "24–72 h före avspark", True)
    return SnapshotTiming(hours, "GT_72H", "Mer än 72 h före avspark", True)


def summarize_snapshot_timing(coupons: Iterable[object]) -> dict[str, object]:
    rows = []
    for coupon in coupons:
        captured_at = getattr(coupon, "captured_at", None)
        for match in getattr(coupon, "matches", ()):
            rows.append(classify_snapshot_timing(captured_at, getattr(match, "kickoff", None)))

    known = [r for r in rows if r.hours_before_kickoff is not None]
    pre = [r for r in known if r.eligible_pre_match]
    buckets = {key: 0 for key in ("LE_1H", "1_3H", "3_12H", "12_24H", "24_72H", "GT_72H", "POST_KICKOFF", "UNKNOWN")}
    for row in rows:
        buckets[row.bucket] = buckets.get(row.bucket, 0) + 1

    return {
        "count": len(rows),
        "known": len(known),
        "unknown": sum(r.bucket == "UNKNOWN" for r in rows),
        "pre_match": len(pre),
        "within_1h": buckets["LE_1H"],
        "within_3h": buckets["LE_1H"] + buckets["1_3H"],
        "within_12h": buckets["LE_1H"] + buckets["1_3H"] + buckets["3_12H"],
        "post_kickoff": buckets["POST_KICKOFF"],
        "average_hours_before_kickoff": (sum(r.hours_before_kickoff for r in pre if r.hours_before_kickoff is not None) / len(pre)) if pre else None,
        "buckets": buckets,
    }
