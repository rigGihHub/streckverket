from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Iterable, Sequence

from core import normalize
from snapshot_timing import classify_snapshot_timing


@dataclass(frozen=True)
class MarketPoint:
    coupon_key: str
    match_number: int
    home: str
    away: str
    captured_at: str
    kickoff: str | None
    market: tuple[float, float, float]
    market_available: bool
    market_source: str
    bookmaker_count: int | None = None
    market_last_update: str | None = None


def _iso_utc(value: str | None = None) -> str:
    if value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def coupon_market_key(matches: Sequence[object]) -> str:
    """Stable identity for one coupon fixture set, independent of prices/streck.

    The key deliberately excludes odds and public percentages so successive market
    captures for the same 13 fixtures end up in one timeline.
    """
    identity = [
        {
            "n": int(getattr(m, "number")),
            "home": str(getattr(m, "home")).strip().casefold(),
            "away": str(getattr(m, "away")).strip().casefold(),
            "kickoff": str(getattr(m, "kickoff", "") or ""),
        }
        for m in matches
    ]
    raw = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def make_market_points(matches: Sequence[object], *, captured_at: str | None = None) -> list[MarketPoint]:
    if len(matches) != 13:
        raise ValueError("En marknadstidslinje för Stryktipset kräver exakt 13 matcher")
    stamp = _iso_utc(captured_at)
    key = coupon_market_key(matches)
    points: list[MarketPoint] = []
    for m in matches:
        market = tuple(float(x) for x in normalize(getattr(m, "market")))
        points.append(MarketPoint(
            coupon_key=key,
            match_number=int(getattr(m, "number")),
            home=str(getattr(m, "home")),
            away=str(getattr(m, "away")),
            captured_at=stamp,
            kickoff=getattr(m, "kickoff", None),
            market=market,  # type: ignore[arg-type]
            market_available=bool(getattr(m, "market_available", False)),
            market_source=str(getattr(m, "market_source", "") or ""),
            bookmaker_count=getattr(m, "market_bookmaker_count", None),
            market_last_update=getattr(m, "market_last_update", None),
        ))
    return points


def _minutes_between(a: str, b: str) -> float:
    da = datetime.fromisoformat(a.replace("Z", "+00:00"))
    db = datetime.fromisoformat(b.replace("Z", "+00:00"))
    if da.tzinfo is None:
        da = da.replace(tzinfo=timezone.utc)
    if db.tzinfo is None:
        db = db.replace(tzinfo=timezone.utc)
    return abs((da - db).total_seconds()) / 60.0


def is_near_duplicate(new: MarketPoint, previous: MarketPoint, *, within_minutes: int = 5, tolerance: float = 1e-8) -> bool:
    if new.coupon_key != previous.coupon_key or new.match_number != previous.match_number:
        return False
    if new.market_available != previous.market_available or new.market_source != previous.market_source:
        return False
    if _minutes_between(new.captured_at, previous.captured_at) > within_minutes:
        return False
    return max(abs(a - b) for a, b in zip(new.market, previous.market)) <= tolerance


def deduplicate_points(existing: Iterable[MarketPoint], incoming: Sequence[MarketPoint], *, within_minutes: int = 5) -> list[MarketPoint]:
    latest: dict[tuple[str, int], MarketPoint] = {}
    for point in existing:
        key = (point.coupon_key, point.match_number)
        if key not in latest or point.captured_at > latest[key].captured_at:
            latest[key] = point
    accepted: list[MarketPoint] = []
    for point in incoming:
        prev = latest.get((point.coupon_key, point.match_number))
        if prev is not None and is_near_duplicate(point, prev, within_minutes=within_minutes):
            continue
        accepted.append(point)
        latest[(point.coupon_key, point.match_number)] = point
    return accepted


def market_movement_rows(points: Sequence[MarketPoint], *, coupon_key: str | None = None) -> list[dict[str, object]]:
    rows = [p for p in points if coupon_key is None or p.coupon_key == coupon_key]
    grouped: dict[tuple[str, int], list[MarketPoint]] = {}
    for p in rows:
        if not p.market_available:
            continue
        grouped.setdefault((p.coupon_key, p.match_number), []).append(p)

    out: list[dict[str, object]] = []
    for (_, _), series in grouped.items():
        series.sort(key=lambda p: p.captured_at)
        first, last = series[0], series[-1]
        timing = classify_snapshot_timing(last.captured_at, last.kickoff)
        out.append({
            "Nr": last.match_number,
            "Match": f"{last.home} – {last.away}",
            "Punkter": len(series),
            "Första 1": round(first.market[0] * 100, 1),
            "Senaste 1": round(last.market[0] * 100, 1),
            "Δ1 p.e.": round((last.market[0] - first.market[0]) * 100, 1),
            "ΔX p.e.": round((last.market[1] - first.market[1]) * 100, 1),
            "Δ2 p.e.": round((last.market[2] - first.market[2]) * 100, 1),
            "Senaste tidsläge": timing.label,
            "Källa": last.market_source or "Källa saknas",
        })
    return sorted(out, key=lambda r: int(r["Nr"]))


def timeline_summary(points: Sequence[MarketPoint], *, coupon_key: str | None = None) -> dict[str, object]:
    rows = [p for p in points if coupon_key is None or p.coupon_key == coupon_key]
    stamps = sorted({p.captured_at for p in rows})
    verified = [p for p in rows if p.market_available]
    return {
        "points": len(rows),
        "captures": len(stamps),
        "verified_points": len(verified),
        "verified_matches_latest": len({p.match_number for p in verified if p.captured_at == (stamps[-1] if stamps else "")}),
        "first_capture": stamps[0] if stamps else None,
        "last_capture": stamps[-1] if stamps else None,
    }


def dumps_market_points(points: Sequence[MarketPoint]) -> str:
    return json.dumps([asdict(p) for p in points], ensure_ascii=False, indent=2)


def loads_market_points(text: str) -> list[MarketPoint]:
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError("Marknadstidslinjen måste vara en lista")
    out: list[MarketPoint] = []
    for item in raw:
        out.append(MarketPoint(
            coupon_key=str(item["coupon_key"]),
            match_number=int(item["match_number"]),
            home=str(item["home"]),
            away=str(item["away"]),
            captured_at=str(item["captured_at"]),
            kickoff=item.get("kickoff"),
            market=tuple(float(x) for x in normalize(item["market"])),  # type: ignore[arg-type]
            market_available=bool(item.get("market_available", False)),
            market_source=str(item.get("market_source", "") or ""),
            bookmaker_count=(int(item["bookmaker_count"]) if item.get("bookmaker_count") is not None else None),
            market_last_update=item.get("market_last_update"),
        ))
    return out


def match_series_rows(points: Sequence[MarketPoint], coupon_key: str, match_number: int) -> list[dict[str, object]]:
    series = [
        p for p in points
        if p.coupon_key == coupon_key and p.match_number == int(match_number) and p.market_available
    ]
    series.sort(key=lambda p: p.captured_at)
    return [
        {
            "Tid": p.captured_at,
            "1": p.market[0] * 100,
            "X": p.market[1] * 100,
            "2": p.market[2] * 100,
        }
        for p in series
    ]
