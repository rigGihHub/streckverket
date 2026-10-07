"""Prospective validation of bookmaker disagreement as a diagnostic context.

v3.59 deliberately does not feed market disagreement into the predictive model.
Only snapshots created after market-consensus provenance existed (v3.58+) are used.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Sequence

from core import SIGNS, normalize
from facit import is_validation_eligible
from market_intelligence_architecture import market_confidence


@dataclass(frozen=True)
class MarketDisagreementSegment:
    segment: str
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
    mean_model_market_gap: float | None
    status: str


@dataclass(frozen=True)
class GapContextSegment:
    market_context: str
    gap_bucket: str
    matches: int
    coupons: int
    brier_gain: float | None
    status: str


def _version_tuple(raw: str) -> tuple[int, int, int] | None:
    try:
        parts = str(raw or "").strip().split(".")
        if len(parts) < 2:
            return None
        vals = [int("".join(ch for ch in p if ch.isdigit()) or "0") for p in parts[:3]]
        while len(vals) < 3:
            vals.append(0)
        return tuple(vals[:3])
    except Exception:
        return None


def _prospective_coupon(coupon: object) -> bool:
    v = _version_tuple(getattr(coupon, "model_version", ""))
    return v is not None and v >= (3, 58, 0)


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


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _gap(model, market) -> float:
    return 0.5 * sum(abs(float(model[i]) - float(market[i])) for i in range(3))


def gap_bucket(model, market) -> str:
    g = _gap(model, market)
    if g <= 0.04:
        return "LÅGT GAP"
    if g >= 0.08 - 1e-12:
        return "HÖGT GAP"
    return "NORMALT GAP"


def _eligible_rows(coupons: Sequence[object]):
    rows = []
    excluded_legacy = 0
    excluded_no_diagnostics = 0
    for coupon in coupons:
        if not _prospective_coupon(coupon):
            excluded_legacy += 1
            continue
        for match in getattr(coupon, "matches", ()):
            if not is_validation_eligible(match):
                continue
            count = int(getattr(match, "market_bookmaker_count", 0) or 0)
            dispersion = getattr(match, "market_dispersion", None)
            if dispersion is None or count < 2:
                excluded_no_diagnostics += 1
                continue
            confidence = market_confidence(count, float(dispersion))
            if confidence == "OTILLRÄCKLIG DATA":
                excluded_no_diagnostics += 1
                continue
            rows.append((str(getattr(coupon, "coupon_id", "")), match, confidence))
    return rows, excluded_legacy, excluded_no_diagnostics


def _segment(rows, name: str, min_matches: int, min_coupons: int) -> MarketDisagreementSegment:
    selected = [(cid, m) for cid, m, segment in rows if segment == name]
    coupon_ids = {cid for cid, _ in selected}
    model_b = [_brier(m.model, m.result) for _, m in selected]
    market_b = [_brier(m.market, m.result) for _, m in selected]
    model_ll = [_logloss(m.model, m.result) for _, m in selected]
    market_ll = [_logloss(m.market, m.result) for _, m in selected]
    n = len(selected)
    status = "GRANSKNINGSBAR" if n >= min_matches and len(coupon_ids) >= min_coupons else "SAMLA MER DATA"
    return MarketDisagreementSegment(
        segment=name,
        matches=n,
        coupons=len(coupon_ids),
        model_brier=_mean(model_b),
        market_brier=_mean(market_b),
        brier_gain=_mean([kb - mb for mb, kb in zip(model_b, market_b)]),
        model_log_loss=_mean(model_ll),
        market_log_loss=_mean(market_ll),
        logloss_gain=_mean([kl - ml for ml, kl in zip(model_ll, market_ll)]),
        model_pick_accuracy=(sum(_pick(m.model) == m.result for _, m in selected) / n if n else None),
        market_pick_accuracy=(sum(_pick(m.market) == m.result for _, m in selected) / n if n else None),
        mean_model_market_gap=_mean([_gap(m.model, m.market) for _, m in selected]),
        status=status,
    )


def _gap_context(rows, min_matches: int, min_coupons: int) -> list[GapContextSegment]:
    result = []
    for context in ("HÖG", "NORMAL", "OENIG"):
        for bucket in ("LÅGT GAP", "NORMALT GAP", "HÖGT GAP"):
            selected = [(cid, m) for cid, m, seg in rows if seg == context and gap_bucket(m.model, m.market) == bucket]
            cids = {cid for cid, _ in selected}
            gains = [_brier(m.market, m.result) - _brier(m.model, m.result) for _, m in selected]
            status = "GRANSKNINGSBAR" if len(selected) >= min_matches and len(cids) >= min_coupons else "EXPLORATIV / SAMLA MER DATA"
            result.append(GapContextSegment(context, bucket, len(selected), len(cids), _mean(gains), status))
    return result


def market_disagreement_validation(
    coupons: Sequence[object], *, min_matches: int = 100, min_coupons: int = 20
) -> dict[str, object]:
    rows, excluded_legacy, excluded_no_diagnostics = _eligible_rows(coupons)
    segments = [_segment(rows, s, int(min_matches), int(min_coupons)) for s in ("HÖG", "NORMAL", "OENIG")]
    reviewable = sum(s.status == "GRANSKNINGSBAR" for s in segments)
    high = next(s for s in segments if s.segment == "HÖG")
    disagree = next(s for s in segments if s.segment == "OENIG")
    contrast = None
    contrast_status = "SAMLA MER DATA"
    if high.status == "GRANSKNINGSBAR" and disagree.status == "GRANSKNINGSBAR":
        contrast_status = "KONTRAST GRANSKNINGSBAR"
        if high.brier_gain is not None and disagree.brier_gain is not None:
            contrast = disagree.brier_gain - high.brier_gain
    return {
        "prospective_matches": len(rows),
        "prospective_coupons": len({cid for cid, _, _ in rows}),
        "excluded_legacy_coupons": excluded_legacy,
        "excluded_without_diagnostics": excluded_no_diagnostics,
        "segments": segments,
        "reviewable_segments": reviewable,
        "gap_context": _gap_context(rows, int(min_matches), int(min_coupons)),
        "high_vs_disagree_brier_gain_delta": contrast,
        "contrast_status": contrast_status,
        "min_matches": int(min_matches),
        "min_coupons": int(min_coupons),
        "automatic_model_weight": False,
        "edge_claim_allowed": False,
    }
