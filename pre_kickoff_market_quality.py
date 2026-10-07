"""Verified pre-kickoff market quality diagnostics (v3.60).

This module never calls a market point a closing line.  It compares a frozen
snapshot with the latest *actually stored and verified* market point before
kickoff.  The output is diagnostic only and does not alter prediction weights.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from core import SIGNS, normalize
from market_timeline import MarketPoint


@dataclass(frozen=True)
class PreKickoffMarketQuality:
    match_number: int
    match: str
    snapshot_at: str
    latest_at: str
    minutes_before_kickoff: float
    timing: str
    snapshot_market: tuple[float, float, float]
    latest_market: tuple[float, float, float]
    deltas_pp: tuple[float, float, float]
    largest_sign: str
    largest_move_pp: float
    bookmaker_count: int | None
    market_source: str
    moved_toward_model: bool | None
    model_alignment_change_pp: float | None


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def pre_kickoff_timing(minutes: float | None) -> str:
    if minutes is None or minutes < 0:
        return "OKÄND"
    if minutes <= 60:
        return "MYCKET NÄRA"
    if minutes <= 180:
        return "NÄRA"
    return "TIDIG"


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Total-variation distance; returned as a probability, not percentage."""
    aa, bb = normalize(a), normalize(b)
    return 0.5 * sum(abs(float(aa[i]) - float(bb[i])) for i in range(3))


def latest_verified_pre_kickoff(points: Sequence[MarketPoint], *, coupon_key: str, match_number: int) -> MarketPoint | None:
    eligible: list[tuple[datetime, MarketPoint]] = []
    for p in points:
        if p.coupon_key != coupon_key or p.match_number != int(match_number) or not p.market_available:
            continue
        captured, kickoff = _dt(p.captured_at), _dt(p.kickoff)
        if captured is None or kickoff is None or captured > kickoff:
            continue
        eligible.append((captured, p))
    return max(eligible, key=lambda x: x[0])[1] if eligible else None


def compare_snapshot_to_late_market(
    snapshot: MarketPoint,
    points: Sequence[MarketPoint],
    *,
    model: Sequence[float] | None = None,
) -> PreKickoffMarketQuality | None:
    if not snapshot.market_available:
        return None
    snap_dt, kickoff = _dt(snapshot.captured_at), _dt(snapshot.kickoff)
    if snap_dt is None or kickoff is None or snap_dt > kickoff:
        return None
    latest = latest_verified_pre_kickoff(
        points, coupon_key=snapshot.coupon_key, match_number=snapshot.match_number
    )
    if latest is None:
        return None
    latest_dt = _dt(latest.captured_at)
    if latest_dt is None or latest_dt < snap_dt:
        return None
    snap = tuple(float(x) for x in normalize(snapshot.market))
    late = tuple(float(x) for x in normalize(latest.market))
    deltas = tuple((late[i] - snap[i]) * 100.0 for i in range(3))
    idx = max(range(3), key=lambda i: abs(deltas[i]))
    minutes = max(0.0, (kickoff - latest_dt).total_seconds() / 60.0)
    toward = None
    alignment_change = None
    if model is not None:
        before = _distance(model, snap)
        after = _distance(model, late)
        alignment_change = (before - after) * 100.0
        # Tiny numerical changes are treated as neutral rather than evidence of direction.
        toward = True if alignment_change > 1e-9 else (False if alignment_change < -1e-9 else None)
    return PreKickoffMarketQuality(
        match_number=snapshot.match_number,
        match=f"{snapshot.home} – {snapshot.away}",
        snapshot_at=snapshot.captured_at,
        latest_at=latest.captured_at,
        minutes_before_kickoff=minutes,
        timing=pre_kickoff_timing(minutes),
        snapshot_market=snap,
        latest_market=late,
        deltas_pp=deltas,
        largest_sign=SIGNS[idx],
        largest_move_pp=deltas[idx],
        bookmaker_count=latest.bookmaker_count,
        market_source=latest.market_source,
        moved_toward_model=toward,
        model_alignment_change_pp=alignment_change,
    )


def quality_rows(points: Sequence[MarketPoint], *, coupon_key: str, models: dict[int, Sequence[float]] | None = None) -> list[PreKickoffMarketQuality]:
    """Use each match's earliest verified pre-kickoff point as the frozen baseline.

    For historical forecast snapshots, callers should use compare_snapshot_to_late_market
    with the actual frozen snapshot instead.  This helper is for the live timeline UI.
    """
    out: list[PreKickoffMarketQuality] = []
    for match_number in sorted({p.match_number for p in points if p.coupon_key == coupon_key}):
        candidates = [p for p in points if p.coupon_key == coupon_key and p.match_number == match_number and p.market_available]
        candidates = [p for p in candidates if _dt(p.captured_at) is not None and _dt(p.kickoff) is not None and _dt(p.captured_at) <= _dt(p.kickoff)]
        if not candidates:
            continue
        snapshot = min(candidates, key=lambda p: _dt(p.captured_at))
        row = compare_snapshot_to_late_market(snapshot, points, model=(models or {}).get(match_number))
        if row is not None:
            out.append(row)
    return out


def display_rows(rows: Sequence[PreKickoffMarketQuality]) -> list[dict[str, object]]:
    return [{
        "Nr": r.match_number,
        "Match": r.match,
        "Sen marknad": r.timing,
        "Min till avspark": round(r.minutes_before_kickoff),
        "Δ1 pp": round(r.deltas_pp[0], 1),
        "ΔX pp": round(r.deltas_pp[1], 1),
        "Δ2 pp": round(r.deltas_pp[2], 1),
        "Störst": f"{r.largest_sign} {r.largest_move_pp:+.1f} pp",
        "BM": r.bookmaker_count if r.bookmaker_count is not None else "–",
        "Mot modellen": ("JA" if r.moved_toward_model is True else "NEJ" if r.moved_toward_model is False else "–"),
    } for r in rows]


def texttv_562_html(rows: Sequence[PreKickoffMarketQuality]) -> str:
    if not rows:
        body = "INGEN VERIFIERAD FÖRMARKNAD ATT JÄMFÖRA ÄNNU"
    else:
        lines = []
        for r in rows[:13]:
            snap_i = max(range(3), key=lambda i: r.snapshot_market[i])
            late_i = max(range(3), key=lambda i: r.latest_market[i])
            lines.append(
                f"{r.match_number:02d} {r.match[:25]:25} "
                f"{SIGNS[snap_i]} {100*r.snapshot_market[snap_i]:4.1f}% → "
                f"{SIGNS[late_i]} {100*r.latest_market[late_i]:4.1f}%  "
                f"MAX {r.largest_sign} {r.largest_move_pp:+4.1f}  {r.timing}"
            )
        body = "\n".join(lines)
    return (
        '<div class="texttv-market"><b>562 RÖRELSER</b><pre>' + body +
        '\n\nSENASTE VERIFIERADE FÖRMARKNAD · INTE CLOSING LINE\n'
        'RÖRELSE MOT MODELLEN ÄR DIAGNOSTIK · INTE BEVIS PÅ POSITIVT EV</pre></div>'
    )
