from __future__ import annotations

"""Governance for prospective shadow experiments.

This module never changes the production model. It decides only whether a frozen
shadow candidate should be rejected, keep collecting evidence, or become eligible
for a separately reviewed production-candidate experiment.
"""

from math import log
from typing import Iterable, Sequence

from core import SIGNS
from experiment_registry import MARKET_PULL_EXPERIMENT_ID
from predictive_experiment import _norm

MIN_REVIEW_MATCHES = 100
MIN_REVIEW_COUPONS = 10
MIN_PROMOTION_MATCHES = 200
MIN_PROMOTION_COUPONS = 20
MIN_COUPON_WIN_RATE = 0.60
MAX_SINGLE_COUPON_GAIN_SHARE = 0.25
MIN_RELATIVE_BRIER_GAIN = 0.005   # 0.5%, fixed ex ante guard against noise
MIN_RELATIVE_LOGLOSS_GAIN = 0.005


def _scores(probs: Sequence[float], result: str) -> tuple[float, float]:
    p = _norm(probs)
    idx = SIGNS.index(result)
    return (
        sum((p[i] - (1.0 if i == idx else 0.0)) ** 2 for i in range(3)),
        -log(max(1e-12, p[idx])),
    )


def _rows(coupons: Iterable, experiment_id: str) -> list[dict]:
    rows: list[dict] = []
    for coupon in coupons:
        cid = str(getattr(coupon, "coupon_id", ""))
        for match in tuple(getattr(coupon, "matches", ()) or ()):
            pred = next((p for p in tuple(getattr(match, "shadow_predictions", ()) or ())
                         if getattr(p, "experiment_id", "") == experiment_id), None)
            result = getattr(match, "result", None)
            if pred is None or result not in SIGNS or not bool(getattr(match, "market_available", False)):
                continue
            cb, cl = _scores(pred.probabilities, result)
            bb, bl = _scores(match.model, result)
            kb, kl = _scores(match.market, result)
            rows.append({"coupon_id": cid, "candidate_brier": cb, "candidate_ll": cl,
                         "baseline_brier": bb, "baseline_ll": bl,
                         "market_brier": kb, "market_ll": kl,
                         "brier_gain": bb-cb, "ll_gain": bl-cl})
    return rows


def shadow_governance(coupons: Iterable, *, experiment_id: str = MARKET_PULL_EXPERIMENT_ID) -> dict:
    rows = _rows(coupons, experiment_id)
    coupon_ids = sorted({r["coupon_id"] for r in rows})
    n, c = len(rows), len(coupon_ids)

    def mean(key: str):
        return sum(float(r[key]) for r in rows) / n if n else None

    cb, cl = mean("candidate_brier"), mean("candidate_ll")
    bb, bl = mean("baseline_brier"), mean("baseline_ll")
    kb, kl = mean("market_brier"), mean("market_ll")
    bg = (bb-cb) if n else None
    lg = (bl-cl) if n else None
    rel_bg = (bg / bb) if n and bb and bg is not None else None
    rel_lg = (lg / bl) if n and bl and lg is not None else None

    coupon_stats = []
    for cid in coupon_ids:
        cr = [r for r in rows if r["coupon_id"] == cid]
        gb = sum(float(r["brier_gain"]) for r in cr) / len(cr)
        gl = sum(float(r["ll_gain"]) for r in cr) / len(cr)
        coupon_stats.append({"coupon_id": cid, "matches": len(cr), "brier_gain": gb, "log_loss_gain": gl,
                             "wins_both": gb > 0 and gl > 0})
    win_rate = (sum(1 for x in coupon_stats if x["wins_both"]) / c) if c else None

    abs_coupon_brier = [abs(x["brier_gain"] * x["matches"]) for x in coupon_stats]
    gain_share = (max(abs_coupon_brier) / sum(abs_coupon_brier)) if abs_coupon_brier and sum(abs_coupon_brier) > 0 else 0.0

    review_ready = n >= MIN_REVIEW_MATCHES and c >= MIN_REVIEW_COUPONS
    promotion_ready = n >= MIN_PROMOTION_MATCHES and c >= MIN_PROMOTION_COUPONS
    beats_baseline = bool(n and cb < bb and cl < bl)
    loses_baseline = bool(n and cb > bb and cl > bl)
    material_gain = bool(rel_bg is not None and rel_lg is not None and rel_bg >= MIN_RELATIVE_BRIER_GAIN and rel_lg >= MIN_RELATIVE_LOGLOSS_GAIN)
    broad_gain = bool(win_rate is not None and win_rate >= MIN_COUPON_WIN_RATE)
    concentration_ok = gain_share <= MAX_SINGLE_COUPON_GAIN_SHARE

    if not n:
        decision = "INGEN BEDÖMNING"
        action = "Samla verkliga shadow-resultat. Ingen historisk backfill och ingen produktionsändring."
    elif not review_ready:
        decision = "FORTSÄTT SAMLA DATA"
        action = f"Shadow-samplet är för litet ({n} matcher/{c} kuponger). Minst {MIN_REVIEW_MATCHES}/{MIN_REVIEW_COUPONS} krävs för första bedömning."
    elif loses_baseline:
        decision = "FÖRKASTA KANDIDATEN"
        action = "Kandidaten är sämre än produktionen på både Brier och log loss i moget shadow-sample. Stoppa nya snapshots för denna kandidat; ändra inte produktionen."
    elif not beats_baseline:
        decision = "FORTSÄTT – BLANDAD EVIDENS"
        action = "Huvudmåtten pekar inte åt samma håll. Ingen promotion eller modelländring är motiverad."
    elif not promotion_ready:
        decision = "LOVANDE – FORTSÄTT SHADOW"
        action = f"Kandidaten slår baseline på båda måtten men promotion-grinden kräver minst {MIN_PROMOTION_MATCHES} matcher över {MIN_PROMOTION_COUPONS} kuponger."
    elif not material_gain:
        decision = "FÖR LITEN FÖRBÄTTRING"
        action = "Kandidaten är bättre, men den förhandsbestämda miniminivån 0,5 % relativ förbättring på både Brier och log loss nås inte. Behåll produktionen."
    elif not broad_gain:
        decision = "FÖRBÄTTRINGEN ÄR INTE BRED NOG"
        action = f"Förbättringen finns totalt men kandidaten vinner på båda måtten i mindre än {int(MIN_COUPON_WIN_RATE*100)} % av kupongerna. Fortsätt shadow eller förkasta."
    elif not concentration_ok:
        decision = "FÖRBÄTTRINGEN ÄR FÖR KONCENTRERAD"
        action = "En enskild kupong står för för stor del av den absoluta Brier-förbättringen. Ingen promotion."
    else:
        decision = "GODKÄND FÖR SEPARAT PRODUKTIONSKANDIDAT-GRANSKNING"
        action = "Kandidaten har klarat shadow-grinden. Nästa steg får vara en separat versionsregistrerad produktionskandidat och manuell granskning – aldrig automatisk promotion."

    return {
        "experiment_id": experiment_id, "completed_matches": n, "completed_coupons": c,
        "candidate_brier": cb, "baseline_brier": bb, "market_brier": kb,
        "candidate_log_loss": cl, "baseline_log_loss": bl, "market_log_loss": kl,
        "relative_brier_gain": rel_bg, "relative_log_loss_gain": rel_lg,
        "coupon_win_rate": win_rate, "largest_coupon_gain_share": gain_share,
        "review_ready": review_ready, "promotion_ready": promotion_ready,
        "beats_baseline_both": beats_baseline, "material_gain": material_gain,
        "broad_gain": broad_gain, "concentration_ok": concentration_ok,
        "decision": decision, "action": action,
        "coupon_stats": coupon_stats,
        "automatic_promotion": False, "engine_change_allowed": False,
        "requirements": {"review_matches": MIN_REVIEW_MATCHES, "review_coupons": MIN_REVIEW_COUPONS,
                         "promotion_matches": MIN_PROMOTION_MATCHES, "promotion_coupons": MIN_PROMOTION_COUPONS,
                         "min_coupon_win_rate": MIN_COUPON_WIN_RATE,
                         "max_single_coupon_gain_share": MAX_SINGLE_COUPON_GAIN_SHARE,
                         "min_relative_brier_gain": MIN_RELATIVE_BRIER_GAIN,
                         "min_relative_logloss_gain": MIN_RELATIVE_LOGLOSS_GAIN},
    }
