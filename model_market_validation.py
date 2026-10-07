from __future__ import annotations

"""Prospective, paired model-vs-market validation.

Only frozen matches with a completed result and a verified bookmaker baseline are
eligible. Positive metric gains mean Streckverket scored better than the market on
the exact same observations. This module is diagnostic only and never changes
model or strategy weights.
"""

from math import log
from typing import Iterable, Sequence

from core import SIGNS

DIVERGENCE_BINS = (
    (0.00, 0.025, "0–2.5 p.e."),
    (0.025, 0.05, "2.5–5 p.e."),
    (0.05, 0.10, "5–10 p.e."),
    (0.10, 10.0, "10+ p.e."),
)


def _norm(values: Sequence[float]) -> tuple[float, float, float]:
    vals = [max(0.0, float(v)) for v in values]
    total = sum(vals)
    if total <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return tuple(v / total for v in vals)  # type: ignore[return-value]


def _scores(probs: Sequence[float], result: str) -> tuple[float, float]:
    p = _norm(probs)
    idx = SIGNS.index(result)
    brier = sum((p[i] - (1.0 if i == idx else 0.0)) ** 2 for i in range(3))
    log_loss = -log(max(1e-12, p[idx]))
    return brier, log_loss


def _eligible(match) -> bool:
    return getattr(match, "result", None) in SIGNS and bool(getattr(match, "market_available", False))


def paired_observations(coupons: Iterable) -> list[dict]:
    rows: list[dict] = []
    for coupon in coupons:
        for match in getattr(coupon, "matches", ()) or ():
            if not _eligible(match):
                continue
            result = str(match.result)
            model = _norm(match.model)
            market = _norm(match.market)
            mb, ml = _scores(model, result)
            kb, kl = _scores(market, result)
            divergence = 0.5 * sum(abs(model[i] - market[i]) for i in range(3))
            rows.append({
                "coupon_id": str(getattr(coupon, "coupon_id", "")),
                "match_number": int(getattr(match, "match_number", 0)),
                "result": result,
                "model_brier": mb,
                "market_brier": kb,
                "brier_gain": kb - mb,
                "model_log_loss": ml,
                "market_log_loss": kl,
                "log_loss_gain": kl - ml,
                "divergence": divergence,
                "model_pick": SIGNS[max(range(3), key=lambda i: model[i])],
                "market_pick": SIGNS[max(range(3), key=lambda i: market[i])],
            })
    return rows


def _aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {
            "matches": 0, "model_brier": None, "market_brier": None, "brier_gain": None,
            "model_log_loss": None, "market_log_loss": None, "log_loss_gain": None,
            "model_better_rate": None,
        }
    return {
        "matches": n,
        "model_brier": sum(r["model_brier"] for r in rows) / n,
        "market_brier": sum(r["market_brier"] for r in rows) / n,
        "brier_gain": sum(r["brier_gain"] for r in rows) / n,
        "model_log_loss": sum(r["model_log_loss"] for r in rows) / n,
        "market_log_loss": sum(r["market_log_loss"] for r in rows) / n,
        "log_loss_gain": sum(r["log_loss_gain"] for r in rows) / n,
        "model_better_rate": sum(1 for r in rows if r["brier_gain"] > 0) / n,
    }


def divergence_rows(coupons: Iterable) -> list[dict]:
    observations = paired_observations(coupons)
    out: list[dict] = []
    for lo, hi, label in DIVERGENCE_BINS:
        bucket = [r for r in observations if lo <= float(r["divergence"]) < hi]
        if not bucket:
            continue
        agg = _aggregate(bucket)
        out.append({"Avvikelse modell–marknad": label, **agg})
    return out


def model_market_summary(coupons: Iterable, *, min_coupons: int = 20, min_matches: int = 200) -> dict:
    coupons = list(coupons)
    observations = paired_observations(coupons)
    coupon_ids = {r["coupon_id"] for r in observations if r["coupon_id"]}
    agg = _aggregate(observations)
    ready = len(coupon_ids) >= min_coupons and len(observations) >= min_matches

    if not observations:
        status = "SAKNAR PARAD MARKNADSDATA"
        lesson = "Det finns ännu inga färdiga matcher där både fryst Streckverket-prognos och verifierat bookmakerankare kan jämföras på samma observation."
    elif not ready:
        status = "SAMLA MER PROSPEKTIV DATA"
        lesson = (
            f"Det finns {len(coupon_ids)} kuponger och {len(observations)} parade matcher. "
            "Visa skillnaderna, men ändra inte modellvikter innan underlaget är större och tidsmässigt separat."
        )
    elif float(agg["brier_gain"]) > 0 and float(agg["log_loss_gain"]) > 0:
        status = "MODELLEN SLÅR MARKNADEN I DETTA SAMPLE"
        lesson = (
            "Streckverkets frysta sannolikheter har lägre genomsnittlig Brier score och log loss än bookmakerankaret på exakt samma prospektiva matcher. "
            "Det är lovande diagnostik, inte bevisad framtida edge; nästa steg är att kontrollera vilka signaler som bär förbättringen på ny data."
        )
    elif float(agg["brier_gain"]) < 0 and float(agg["log_loss_gain"]) < 0:
        status = "MARKNADEN ÄR STARKARE I DETTA SAMPLE"
        lesson = (
            "Bookmakerankaret har lägre genomsnittlig Brier score och log loss än Streckverkets justerade sannolikheter. "
            "Det talar för att granska eller minska modelljusteringar, men först genom separata prospektiva experiment."
        )
    else:
        status = "BLANDAD SIGNAL"
        lesson = "Brier score och log loss pekar inte åt samma håll. Ingen modellvikt bör ändras på detta underlag."

    return {
        **agg,
        "eligible_coupons": len(coupon_ids),
        "review_ready": ready,
        "min_coupons": min_coupons,
        "min_matches": min_matches,
        "status": status,
        "lesson": lesson,
        "divergence_rows": divergence_rows(coupons),
        "automatic_model_change": False,
    }
