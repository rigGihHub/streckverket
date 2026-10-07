from __future__ import annotations

"""Marginal signal ablation from prospectively frozen FactorSnapshots.

The stored counterfactual for each verified factor is the model without that one
factor. This supports a conservative leave-one-signal-out diagnostic. It does not
identify causal effects when signals interact and never changes weights automatically.
"""

from math import log
from typing import Iterable, Sequence

from core import SIGNS
from explainable_model import CATEGORY_NAMES


def _norm(values: Sequence[float]) -> tuple[float, float, float]:
    vals = [max(0.0, float(v)) for v in values]
    s = sum(vals)
    if s <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return tuple(v / s for v in vals)  # type: ignore[return-value]


def _brier(values: Sequence[float], result: str) -> float:
    p = _norm(values); y = SIGNS.index(result)
    return sum((p[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(3))


def _logloss(values: Sequence[float], result: str) -> float:
    p = _norm(values); y = SIGNS.index(result)
    return -log(max(1e-12, p[y]))


def ablation_observations(coupons: Iterable) -> list[dict]:
    rows: list[dict] = []
    for coupon in coupons:
        for match in getattr(coupon, "matches", ()) or ():
            result = getattr(match, "result", None)
            if result not in SIGNS or not bool(getattr(match, "market_available", False)):
                continue
            final_brier = _brier(match.model, result)
            final_ll = _logloss(match.model, result)
            market_brier = _brier(match.market, result)
            for factor in getattr(match, "factors", ()) or ():
                if not bool(getattr(factor, "verified", False)):
                    continue
                without_brier = _brier(factor.counterfactual, result)
                without_ll = _logloss(factor.counterfactual, result)
                rows.append({
                    "coupon_id": str(getattr(coupon, "coupon_id", "")),
                    "match_number": int(getattr(match, "match_number", 0)),
                    "category": str(factor.category),
                    "name": CATEGORY_NAMES.get(str(factor.category), str(getattr(factor, "name", factor.category))),
                    "with_brier": final_brier,
                    "without_brier": without_brier,
                    "market_brier": market_brier,
                    "brier_contribution": without_brier - final_brier,
                    "log_loss_contribution": without_ll - final_ll,
                })
    return rows


def signal_ablation_scorecard(coupons: Iterable, *, min_observations: int = 50, min_coupons: int = 10) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in ablation_observations(coupons):
        grouped.setdefault(row["category"], []).append(row)
    out: list[dict] = []
    for category, rows in grouped.items():
        n = len(rows)
        coupon_count = len({r["coupon_id"] for r in rows if r["coupon_id"]})
        brier_gain = sum(r["brier_contribution"] for r in rows) / n
        ll_gain = sum(r["log_loss_contribution"] for r in rows) / n
        help_rate = sum(1 for r in rows if r["brier_contribution"] > 0) / n
        model_vs_market = sum(r["market_brier"] - r["with_brier"] for r in rows) / n
        ready = n >= min_observations and coupon_count >= min_coupons
        if not ready:
            verdict = "För lite data"
        elif brier_gain > 0 and ll_gain > 0:
            verdict = "Bidrar positivt i detta sample"
        elif brier_gain < 0 and ll_gain < 0:
            verdict = "Försämrar i detta sample"
        else:
            verdict = "Blandad signal"
        out.append({
            "category": category,
            "name": rows[0]["name"],
            "observations": n,
            "coupons": coupon_count,
            "brier_contribution": brier_gain,
            "log_loss_contribution": ll_gain,
            "help_rate": help_rate,
            "model_vs_market_brier_gain": model_vs_market,
            "review_ready": ready,
            "verdict": verdict,
        })
    return sorted(out, key=lambda r: (not r["review_ready"], -float(r["brier_contribution"]), -int(r["observations"])))


def signal_ablation_summary(coupons: Iterable) -> dict:
    rows = signal_ablation_scorecard(coupons)
    mature = [r for r in rows if r["review_ready"]]
    if not rows:
        lesson = "Inga verifierade prospektiva faktorsnapshots med facit och bookmakerbaseline finns ännu."
    elif not mature:
        lesson = "Det finns faktorsnapshots, men ännu för få observationer över tillräckligt många kuponger för att rangordna signalernas marginalbidrag."
    else:
        best = max(mature, key=lambda r: float(r["brier_contribution"]))
        worst = min(mature, key=lambda r: float(r["brier_contribution"]))
        if float(worst["brier_contribution"]) < 0:
            lesson = f"{best['name']} har starkast marginalbidrag i detta sample, medan {worst['name'].lower()} bör granskas extra. Detta är leave-one-signal-out-diagnostik, inte ett kausalitetsbevis."
        else:
            lesson = f"{best['name']} har starkast marginalbidrag i detta sample. Ingen mogen signal är tydligt negativ, men validering på ny data krävs före viktändring."
    return {"rows": rows, "mature_signals": len(mature), "lesson": lesson, "automatic_weight_change": False}
