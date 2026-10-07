from __future__ import annotations

"""Prospective shadow-mode experiments for Streckverket.

Candidate probabilities are frozen before results are known and stored alongside the
production forecast. Shadow candidates never affect system selections, budget,
readiness or production model weights.
"""

from dataclasses import dataclass
from math import log
from typing import Iterable, Sequence

from core import SIGNS

from experiment_registry import MARKET_PULL_EXPERIMENT_ID
MARKET_PULL_WEIGHT = 0.25
MIN_COMPLETED_MATCHES = 100
MIN_COMPLETED_COUPONS = 10


@dataclass(frozen=True)
class ShadowPrediction:
    experiment_id: str
    label: str
    probabilities: tuple[float, float, float]
    source_model_version: str
    candidate_rule: str


def _norm(values: Sequence[float]) -> tuple[float, float, float]:
    vals = [max(0.0, float(v)) for v in values]
    total = sum(vals)
    if total <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return tuple(v / total for v in vals)  # type: ignore[return-value]


def _mix(model: Sequence[float], market: Sequence[float], market_weight: float) -> tuple[float, float, float]:
    m = _norm(model)
    k = _norm(market)
    w = max(0.0, min(1.0, float(market_weight)))
    return _norm(tuple((1.0 - w) * m[i] + w * k[i] for i in range(3)))


def eligible_shadow_spec(history: Iterable) -> dict | None:
    """Return the registered candidate only while its lifecycle accepts new snapshots."""
    from experiment_registry import experiment_lifecycle, get_experiment

    data = list(history)
    life = experiment_lifecycle(data, experiment_id=MARKET_PULL_EXPERIMENT_ID)
    if not life.get("accepts_new_snapshots", False):
        return None
    definition = get_experiment(MARKET_PULL_EXPERIMENT_ID)
    if definition is None:
        return None
    return {
        "experiment_id": MARKET_PULL_EXPERIMENT_ID,
        "label": definition.label,
        "market_weight": MARKET_PULL_WEIGHT,
        "candidate_rule": definition.candidate_rule,
        "lifecycle_status": life.get("status"),
    }


def build_shadow_predictions(matches, history: Iterable, *, source_model_version: str) -> dict[int, tuple[ShadowPrediction, ...]]:
    """Create pre-result shadow predictions without changing production Match objects."""
    spec = eligible_shadow_spec(history)
    if spec is None:
        return {}
    out: dict[int, tuple[ShadowPrediction, ...]] = {}
    for match in matches:
        if not bool(getattr(match, "market_available", False)):
            continue
        probabilities = _mix(getattr(match, "model"), getattr(match, "market"), spec["market_weight"])
        pred = ShadowPrediction(
            experiment_id=spec["experiment_id"],
            label=spec["label"],
            probabilities=probabilities,
            source_model_version=str(source_model_version or ""),
            candidate_rule=spec["candidate_rule"],
        )
        out[int(getattr(match, "number"))] = (pred,)
    return out


def _scores(probs: Sequence[float], result: str) -> tuple[float, float]:
    p = _norm(probs)
    idx = SIGNS.index(result)
    brier = sum((p[i] - (1.0 if i == idx else 0.0)) ** 2 for i in range(3))
    return brier, -log(max(1e-12, p[idx]))


def shadow_experiment_summary(coupons: Iterable, *, experiment_id: str = MARKET_PULL_EXPERIMENT_ID) -> dict:
    rows = []
    coupon_ids: set[str] = set()
    pending = 0
    for coupon in coupons:
        for match in tuple(getattr(coupon, "matches", ()) or ()):
            predictions = tuple(getattr(match, "shadow_predictions", ()) or ())
            pred = next((p for p in predictions if getattr(p, "experiment_id", "") == experiment_id), None)
            if pred is None:
                continue
            if getattr(match, "result", None) not in SIGNS:
                pending += 1
                continue
            if not bool(getattr(match, "market_available", False)):
                continue
            result = str(match.result)
            cb, cl = _scores(pred.probabilities, result)
            bb, bl = _scores(match.model, result)
            kb, kl = _scores(match.market, result)
            rows.append((cb, cl, bb, bl, kb, kl))
            coupon_ids.add(str(getattr(coupon, "coupon_id", "")))

    n = len(rows)
    if n:
        candidate_brier = sum(r[0] for r in rows) / n
        candidate_ll = sum(r[1] for r in rows) / n
        baseline_brier = sum(r[2] for r in rows) / n
        baseline_ll = sum(r[3] for r in rows) / n
        market_brier = sum(r[4] for r in rows) / n
        market_ll = sum(r[5] for r in rows) / n
    else:
        candidate_brier = candidate_ll = baseline_brier = baseline_ll = market_brier = market_ll = None

    ready = n >= MIN_COMPLETED_MATCHES and len(coupon_ids) >= MIN_COMPLETED_COUPONS
    if not n:
        status = "INGA FÄRDIGA SHADOW-OBSERVATIONER"
        lesson = "Kandidatprognosen måste först frysas före match och därefter få riktigt facit. Ingen historisk backfill görs."
    elif not ready:
        status = "SHADOW-TEST PÅGÅR – FÖR LITE DATA"
        lesson = f"{n} färdiga matcher över {len(coupon_ids)} kuponger. Vänta på minst {MIN_COMPLETED_MATCHES} matcher och {MIN_COMPLETED_COUPONS} kuponger innan kandidaten bedöms."
    elif candidate_brier < baseline_brier and candidate_ll < baseline_ll:
        status = "KANDIDATEN SLÅR BASELINE I SHADOW-SAMPLET"
        lesson = "Kandidaten är bättre än produktionsprognosen på både Brier och log loss i det prospektiva shadow-samplet. Detta motiverar fortsatt validering, inte automatisk produktionssättning."
    elif candidate_brier > baseline_brier and candidate_ll > baseline_ll:
        status = "KANDIDATEN ÄR SÄMRE ÄN BASELINE"
        lesson = "Shadow-kandidaten försämrar både Brier och log loss mot produktionsprognosen och bör inte flyttas till produktion på detta underlag."
    else:
        status = "BLANDAD SHADOW-EVIDENS"
        lesson = "Brier och log loss pekar åt olika håll. Behåll produktionsmodellen oförändrad."

    return {
        "experiment_id": experiment_id,
        "label": "25 % närmare bookmakerankaret",
        "completed_matches": n,
        "completed_coupons": len(coupon_ids),
        "pending_matches": pending,
        "review_ready": ready,
        "min_matches": MIN_COMPLETED_MATCHES,
        "min_coupons": MIN_COMPLETED_COUPONS,
        "candidate_brier": candidate_brier,
        "baseline_brier": baseline_brier,
        "market_brier": market_brier,
        "candidate_log_loss": candidate_ll,
        "baseline_log_loss": baseline_ll,
        "market_log_loss": market_ll,
        "status": status,
        "lesson": lesson,
        "automatic_promotion": False,
        "affects_system": False,
    }
