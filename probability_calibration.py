from __future__ import annotations

"""Prospective probability-calibration diagnostics for frozen FacitCoupon snapshots.

This module is deliberately diagnostic only. It reads the probabilities that were
stored before kickoff and the later observed result. It never reconstructs missing
market data and it never changes model or strategy weights.
"""

from math import log
from typing import Iterable, Sequence

from core import SIGNS

BINS = ((0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70),
        (0.70, 0.75), (0.75, 0.80), (0.80, 1.0000001))


def _complete(coupon) -> bool:
    matches = tuple(getattr(coupon, "matches", ()) or ())
    return len(matches) == 13 and all(getattr(m, "result", None) in SIGNS for m in matches)


def _norm(probs: Sequence[float]) -> tuple[float, float, float]:
    vals = [max(0.0, float(x)) for x in probs]
    total = sum(vals)
    if total <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return tuple(x / total for x in vals)  # type: ignore[return-value]


def _bin_label(lo: float, hi: float) -> str:
    return "80 %+" if lo >= 0.80 else f"{int(lo*100)}–{int(hi*100)} %"


def _bucket(p: float):
    for lo, hi in BINS:
        if lo <= p < hi:
            return lo, hi
    return None


def _metrics(observations: list[tuple[tuple[float, float, float], str]]) -> dict:
    if not observations:
        return {"matches": 0, "brier": None, "log_loss": None}
    brier = 0.0
    ll = 0.0
    for probs, result in observations:
        y = SIGNS.index(result)
        brier += sum((probs[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(3))
        ll += -log(max(1e-12, probs[y]))
    n = len(observations)
    return {"matches": n, "brier": brier / n, "log_loss": ll / n}


def calibration_rows(coupons: Iterable, *, source: str = "model", spikes_only: bool = False) -> list[dict]:
    """Return top-confidence calibration bins (50%+) from frozen snapshots.

    A spike is a match where the actually saved system selection contained one sign.
    Market rows exclude matches where a verified bookmaker baseline was unavailable.
    """
    if source not in {"model", "market"}:
        raise ValueError("source must be 'model' or 'market'")
    buckets: dict[tuple[float, float], list[tuple[float, bool, str]]] = {b: [] for b in BINS}
    for coupon in coupons:
        if not _complete(coupon):
            continue
        for match in coupon.matches:
            if spikes_only and len(tuple(getattr(match, "selected", ()) or ())) != 1:
                continue
            if source == "market" and not bool(getattr(match, "market_available", False)):
                continue
            probs = _norm(getattr(match, source))
            idx = max(range(3), key=lambda i: probs[i])
            confidence = probs[idx]
            b = _bucket(confidence)
            if b is None:
                continue
            buckets[b].append((confidence, SIGNS[idx] == str(match.result), SIGNS[idx]))
    rows = []
    for lo, hi in BINS:
        obs = buckets[(lo, hi)]
        if not obs:
            continue
        n = len(obs)
        mean_p = sum(x[0] for x in obs) / n
        actual = sum(int(x[1]) for x in obs) / n
        rows.append({
            "Intervall": _bin_label(lo, hi), "Matcher": n,
            "Snittprognos": mean_p, "Faktisk träff": actual,
            "Kalibreringsgap": actual - mean_p,
            "1": sum(1 for x in obs if x[2] == "1"),
            "X": sum(1 for x in obs if x[2] == "X"),
            "2": sum(1 for x in obs if x[2] == "2"),
        })
    return rows


def outcome_calibration_rows(coupons: Iterable, *, source: str = "model") -> list[dict]:
    """Binary calibration per sign for probabilities in the decision-relevant 50%+ bins."""
    if source not in {"model", "market"}:
        raise ValueError("source must be 'model' or 'market'")
    data: dict[tuple[str, float, float], list[tuple[float, bool]]] = {}
    for sign in SIGNS:
        for lo, hi in BINS:
            data[(sign, lo, hi)] = []
    for coupon in coupons:
        if not _complete(coupon):
            continue
        for match in coupon.matches:
            if source == "market" and not bool(getattr(match, "market_available", False)):
                continue
            probs = _norm(getattr(match, source))
            for i, sign in enumerate(SIGNS):
                b = _bucket(probs[i])
                if b:
                    data[(sign, *b)].append((probs[i], str(match.result) == sign))
    rows = []
    for sign in SIGNS:
        for lo, hi in BINS:
            obs = data[(sign, lo, hi)]
            if obs:
                n = len(obs); mean_p = sum(x[0] for x in obs) / n; actual = sum(int(x[1]) for x in obs) / n
                rows.append({"Tecken": sign, "Intervall": _bin_label(lo, hi), "Matcher": n,
                             "Snittprognos": mean_p, "Faktisk frekvens": actual,
                             "Kalibreringsgap": actual - mean_p})
    return rows


def calibration_summary(coupons: Iterable, *, min_review_coupons: int = 20) -> dict:
    coupons = list(coupons)
    complete = [c for c in coupons if _complete(c)]
    model_obs = []
    market_obs = []
    spike_count = 0
    for coupon in complete:
        for match in coupon.matches:
            model_obs.append((_norm(match.model), str(match.result)))
            if len(tuple(getattr(match, "selected", ()) or ())) == 1:
                spike_count += 1
            if bool(getattr(match, "market_available", False)):
                market_obs.append((_norm(match.market), str(match.result)))
    model = _metrics(model_obs); market = _metrics(market_obs)
    ready = len(complete) >= min_review_coupons
    if not complete:
        status = "SAMLA FACIT"
        lesson = "Inga kompletta prospektivt sparade kuponger finns ännu. Kalibrering kan inte bedömas."
    elif not ready:
        status = "SAMLA MER PROSPEKTIV HISTORIK"
        lesson = f"Bara {len(complete)} kompletta kuponger finns. Visa avvikelserna, men ändra inte spikregel eller prognosmotor på detta underlag."
    else:
        status = "DIAGNOSTIK REDO"
        if market["brier"] is not None and model["brier"] is not None and model["brier"] > market["brier"]:
            lesson = "På detta prospektiva underlag har marknadsankaret lägre Brier score än Streckverkets frysta sannolikheter. Granska modelljusteringarna innan de ges större vikt."
        else:
            lesson = "Underlaget räcker för kalibreringsgranskning, men enskilda intervall måste fortfarande bedömas med sample size och utan automatiska tröskelregler."
    return {
        "complete_coupons": len(complete), "model": model, "market": market,
        "spike_matches": spike_count, "review_ready": ready,
        "min_review_coupons": min_review_coupons, "status": status, "lesson": lesson,
        "model_bins": calibration_rows(complete, source="model"),
        "market_bins": calibration_rows(complete, source="market"),
        "spike_bins": calibration_rows(complete, source="model", spikes_only=True),
        "model_outcome_bins": outcome_calibration_rows(complete, source="model"),
        "market_outcome_bins": outcome_calibration_rows(complete, source="market"),
        "automatic_threshold_change": False, "automatic_model_change": False,
    }
