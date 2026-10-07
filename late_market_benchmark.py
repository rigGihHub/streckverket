"""Prospective benchmark for model disagreement versus later verified pre-kickoff market.

v3.61 starts an explicit linkage between each frozen FacitCoupon and the market
 timeline that existed for the same fixture set. Legacy coupons are never
 backfilled. The benchmark is diagnostic only: it does not measure ROI and does
 not change model or strategy weights.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

from core import normalize
from market_disagreement_validation import gap_bucket
from market_timeline import MarketPoint


@dataclass(frozen=True)
class LateMarketObservation:
    coupon_id: str
    match_number: int
    match: str
    snapshot_at: str
    late_market_at: str
    minutes_before_kickoff: float
    timing: str
    gap_bucket: str
    initial_gap_pp: float
    alignment_change_pp: float
    moved_toward_model: bool | None
    largest_market_move_pp: float
    bookmaker_count: int | None
    market_source: str


@dataclass(frozen=True)
class LateMarketSegment:
    gap_bucket: str
    matches: int
    coupons: int
    toward: int
    away: int
    neutral: int
    toward_rate: float | None
    mean_alignment_change_pp: float | None
    mean_abs_market_move_pp: float | None
    status: str


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


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    aa, bb = normalize(a), normalize(b)
    return 0.5 * sum(abs(float(aa[i]) - float(bb[i])) for i in range(3))


def _timing(minutes: float) -> str:
    if minutes <= 60:
        return "MYCKET NÄRA"
    if minutes <= 180:
        return "NÄRA"
    return "TIDIG"


def _latest_later_point(
    points: Sequence[MarketPoint], *, key: str, match_number: int,
    snapshot_at: str, kickoff: str | None,
) -> MarketPoint | None:
    snap_dt, kickoff_dt = _dt(snapshot_at), _dt(kickoff)
    if snap_dt is None or kickoff_dt is None or snap_dt > kickoff_dt:
        return None
    eligible: list[tuple[datetime, MarketPoint]] = []
    for p in points:
        if p.coupon_key != key or p.match_number != int(match_number) or not p.market_available:
            continue
        captured = _dt(p.captured_at)
        p_kickoff = _dt(p.kickoff) or kickoff_dt
        if captured is None or p_kickoff is None:
            continue
        # Strictly later than the frozen snapshot. The automatically stored point
        # at snapshot time is baseline provenance, not evidence of later movement.
        if captured <= snap_dt or captured > p_kickoff:
            continue
        eligible.append((captured, p))
    return max(eligible, key=lambda x: x[0])[1] if eligible else None


def prospective_observations(coupons: Sequence[object], market_points: Sequence[MarketPoint]) -> tuple[list[LateMarketObservation], dict[str, int]]:
    out: list[LateMarketObservation] = []
    excluded_legacy_coupons = 0
    excluded_no_later_point = 0
    excluded_bad_snapshot = 0

    for coupon in coupons:
        key = str(getattr(coupon, "market_timeline_key", "") or "").strip()
        if not key:
            excluded_legacy_coupons += 1
            continue
        snapshot_at = str(getattr(coupon, "captured_at", "") or "")
        coupon_id = str(getattr(coupon, "coupon_id", "") or "")
        for m in getattr(coupon, "matches", ()):
            if not bool(getattr(m, "market_available", False)):
                excluded_bad_snapshot += 1
                continue
            kickoff = getattr(m, "kickoff", None)
            snap_dt, kickoff_dt = _dt(snapshot_at), _dt(kickoff)
            if snap_dt is None or kickoff_dt is None or snap_dt > kickoff_dt:
                excluded_bad_snapshot += 1
                continue
            late = _latest_later_point(
                market_points, key=key, match_number=int(getattr(m, "match_number")),
                snapshot_at=snapshot_at, kickoff=kickoff,
            )
            if late is None:
                excluded_no_later_point += 1
                continue
            late_dt = _dt(late.captured_at)
            if late_dt is None:
                excluded_no_later_point += 1
                continue
            model = tuple(float(x) for x in normalize(getattr(m, "model")))
            snapshot_market = tuple(float(x) for x in normalize(getattr(m, "market")))
            late_market = tuple(float(x) for x in normalize(late.market))
            before = _distance(model, snapshot_market)
            after = _distance(model, late_market)
            change_pp = (before - after) * 100.0
            toward = True if change_pp > 1e-9 else (False if change_pp < -1e-9 else None)
            moves = [(late_market[i] - snapshot_market[i]) * 100.0 for i in range(3)]
            minutes = max(0.0, (kickoff_dt - late_dt).total_seconds() / 60.0)
            out.append(LateMarketObservation(
                coupon_id=coupon_id,
                match_number=int(getattr(m, "match_number")),
                match=f"{getattr(m, 'home')} – {getattr(m, 'away')}",
                snapshot_at=snapshot_at,
                late_market_at=late.captured_at,
                minutes_before_kickoff=minutes,
                timing=_timing(minutes),
                gap_bucket=gap_bucket(model, snapshot_market),
                initial_gap_pp=before * 100.0,
                alignment_change_pp=change_pp,
                moved_toward_model=toward,
                largest_market_move_pp=max(abs(x) for x in moves),
                bookmaker_count=late.bookmaker_count,
                market_source=str(late.market_source or ""),
            ))
    return out, {
        "excluded_legacy_coupons": excluded_legacy_coupons,
        "excluded_no_later_point": excluded_no_later_point,
        "excluded_bad_snapshot": excluded_bad_snapshot,
    }


def _mean(values: Iterable[float]) -> float | None:
    xs = list(values)
    return sum(xs) / len(xs) if xs else None


def _segment(rows: Sequence[LateMarketObservation], name: str, min_matches: int, min_coupons: int) -> LateMarketSegment:
    chosen = [r for r in rows if r.gap_bucket == name]
    coupon_ids = {r.coupon_id for r in chosen}
    toward = sum(r.moved_toward_model is True for r in chosen)
    away = sum(r.moved_toward_model is False for r in chosen)
    neutral = sum(r.moved_toward_model is None for r in chosen)
    directional = toward + away
    return LateMarketSegment(
        gap_bucket=name,
        matches=len(chosen),
        coupons=len(coupon_ids),
        toward=toward,
        away=away,
        neutral=neutral,
        toward_rate=(toward / directional) if directional else None,
        mean_alignment_change_pp=_mean(r.alignment_change_pp for r in chosen),
        mean_abs_market_move_pp=_mean(r.largest_market_move_pp for r in chosen),
        status="GRANSKNINGSBAR" if len(chosen) >= min_matches and len(coupon_ids) >= min_coupons else "SAMLA MER DATA",
    )


def late_market_benchmark(coupons: Sequence[object], market_points: Sequence[MarketPoint], *, min_matches: int = 100, min_coupons: int = 20) -> dict[str, object]:
    rows, exclusions = prospective_observations(coupons, market_points)
    segments = tuple(_segment(rows, name, min_matches, min_coupons) for name in ("LÅGT GAP", "NORMALT GAP", "HÖGT GAP"))
    coupon_ids = {r.coupon_id for r in rows}
    toward = sum(r.moved_toward_model is True for r in rows)
    away = sum(r.moved_toward_model is False for r in rows)
    neutral = sum(r.moved_toward_model is None for r in rows)
    directional = toward + away
    return {
        "observations": tuple(rows),
        "segments": segments,
        "prospective_matches": len(rows),
        "prospective_coupons": len(coupon_ids),
        "reviewable_segments": sum(s.status == "GRANSKNINGSBAR" for s in segments),
        "toward": toward,
        "away": away,
        "neutral": neutral,
        "toward_rate": (toward / directional) if directional else None,
        "mean_alignment_change_pp": _mean(r.alignment_change_pp for r in rows),
        "automatic_model_weight": False,
        "edge_claim_allowed": False,
        **exclusions,
    }


def observation_rows(rows: Sequence[LateMarketObservation]) -> list[dict[str, object]]:
    return [{
        "Kupong": r.coupon_id,
        "Nr": r.match_number,
        "Match": r.match,
        "Startgap": r.gap_bucket,
        "Gap": round(r.initial_gap_pp, 1),
        "Sen punkt": r.timing,
        "Min till avspark": round(r.minutes_before_kickoff),
        "Marknadsrörelse": round(r.largest_market_move_pp, 1),
        "Mot modellen": "JA" if r.moved_toward_model is True else "NEJ" if r.moved_toward_model is False else "NEUTRAL",
        "Gapförändring pp": round(r.alignment_change_pp, 2),
        "BM": r.bookmaker_count if r.bookmaker_count is not None else "–",
    } for r in rows]
