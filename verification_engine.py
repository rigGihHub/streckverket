"""Independent historical verification of Streckverket against the bookmaker baseline.

This module deliberately does not tune the model. It only evaluates forecasts that
were saved before results were known and for which a real market baseline existed.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from typing import Sequence

from core import SIGNS, normalize
from facit import is_validation_eligible, observation_quality_for_match
from snapshot_timing import classify_snapshot_timing


@dataclass(frozen=True)
class BenchmarkReport:
    matches: int
    coupons: int
    model_brier: float | None
    market_brier: float | None
    brier_gain: float | None
    model_log_loss: float | None
    market_log_loss: float | None
    logloss_gain: float | None
    model_pick_accuracy: float | None
    market_pick_accuracy: float | None
    recent_matches: int
    recent_brier_gain: float | None
    ci_low: float | None
    ci_high: float | None
    verdict: str
    plain_summary: str
    coupon_diversity_ok: bool
    min_coupons_required: int


def _idx(result: str) -> int:
    return SIGNS.index(result)


def _brier(probs, result: str) -> float:
    p = normalize(probs)
    y = _idx(result)
    return sum((p[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(3))


def _logloss(probs, result: str) -> float:
    p = normalize(probs)
    return -log(max(1e-12, p[_idx(result)]))


def _pick(probs) -> str:
    return SIGNS[max(range(3), key=lambda i: float(probs[i]))]


def _eligible(coupons, *, min_quality_score: int | None = None, max_hours_before_kickoff: float | None = None):
    rows = []
    coupon_ids = set()
    for coupon in sorted(coupons, key=lambda c: c.captured_at):
        for match in coupon.matches:
            if not is_validation_eligible(match):
                continue
            if min_quality_score is not None:
                quality = observation_quality_for_match(match, coupon.captured_at)
                if quality.score < int(min_quality_score):
                    continue
            if max_hours_before_kickoff is not None:
                timing = classify_snapshot_timing(coupon.captured_at, getattr(match, "kickoff", None))
                if not timing.eligible_pre_match or timing.hours_before_kickoff is None or timing.hours_before_kickoff > float(max_hours_before_kickoff):
                    continue
            rows.append((coupon.coupon_id, match))
            coupon_ids.add(coupon.coupon_id)
    return rows, coupon_ids


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _mean_ci95(xs):
    """Approximate 95% interval for paired per-match score gains.

    Diagnostic only: football matches are not guaranteed independent, so the UI must
    not present this as formal proof of edge.
    """
    n = len(xs)
    if n < 30:
        return None, None
    avg = sum(xs) / n
    if n == 1:
        return avg, avg
    var = sum((x - avg) ** 2 for x in xs) / (n - 1)
    half = 1.96 * sqrt(var / n)
    return avg - half, avg + half


def benchmark_against_market(coupons: Sequence, *, min_sample: int = 100, min_coupons: int = 20, min_quality_score: int | None = None, max_hours_before_kickoff: float | None = None) -> BenchmarkReport:
    rows, coupon_ids = _eligible(coupons, min_quality_score=min_quality_score, max_hours_before_kickoff=max_hours_before_kickoff)
    n = len(rows)
    if not rows:
        return BenchmarkReport(0, 0, None, None, None, None, None, None, None, None, 0, None, None, None,
                               "INGET UNDERLAG", "Inga färdiga matcher med användbar marknadsbas finns ännu.", False, int(min_coupons))

    model_b = [_brier(m.model, m.result) for _, m in rows]
    market_b = [_brier(m.market, m.result) for _, m in rows]
    gains = [kb - mb for mb, kb in zip(model_b, market_b)]
    model_ll = [_logloss(m.model, m.result) for _, m in rows]
    market_ll = [_logloss(m.market, m.result) for _, m in rows]
    ll_gains = [kl - ml for ml, kl in zip(model_ll, market_ll)]
    model_acc = sum(_pick(m.model) == m.result for _, m in rows) / n
    market_acc = sum(_pick(m.market) == m.result for _, m in rows) / n
    ci_low, ci_high = _mean_ci95(gains)

    recent_n = max(1, int(round(n * 0.30))) if n >= 30 else 0
    recent_gain = _mean(gains[-recent_n:]) if recent_n else None
    gain = _mean(gains)
    ll_gain = _mean(ll_gains)

    coupon_diversity_ok = len(coupon_ids) >= int(min_coupons)
    if n < min_sample or not coupon_diversity_ok:
        verdict = "FÖR LITE OBEROENDE HISTORIK"
        summary = (f"{n} matcher från {len(coupon_ids)} kuponger är verifierade. "
                   f"Streckverket kräver minst {min_sample} matcher och {min_coupons} separata kuponger innan ett positivt mönster får lyftas.")
    elif ci_low is not None and ci_low > 0 and ll_gain is not None and ll_gain > 0 and recent_gain is not None and recent_gain > 0:
        verdict = "LOVANDE MÖNSTER"
        summary = "Modellen har hittills slagit marknadsbasen på Brier och log loss, och mönstret syns även i den nyare delen. Det är fortfarande inte bevisad edge."
    elif ci_high is not None and ci_high < 0 and ll_gain is not None and ll_gain < 0:
        verdict = "MARKNADEN BÄTTRE"
        summary = "Marknadsbasen har hittills varit bättre. Modellens extra justeringar bör förenklas eller omprövas innan fler signaler läggs till."
    else:
        verdict = "INGEN BEVISAD EDGE"
        summary = "Skillnaden mot marknaden är ännu för osäker eller inkonsekvent för att kalla den en edge."

    return BenchmarkReport(
        matches=n, coupons=len(coupon_ids), model_brier=_mean(model_b), market_brier=_mean(market_b),
        brier_gain=gain, model_log_loss=_mean(model_ll), market_log_loss=_mean(market_ll), logloss_gain=ll_gain,
        model_pick_accuracy=model_acc, market_pick_accuracy=market_acc, recent_matches=recent_n,
        recent_brier_gain=recent_gain, ci_low=ci_low, ci_high=ci_high, verdict=verdict, plain_summary=summary,
        coupon_diversity_ok=coupon_diversity_ok, min_coupons_required=int(min_coupons),
    )
