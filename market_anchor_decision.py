from __future__ import annotations

"""Conservative gate for deciding whether a predictive experiment is justified.

The gate consumes only prospectively frozen model/market/result observations and
verified factor-ablation snapshots. It never changes model weights. Fixed sample
requirements are deliberately conservative to prevent small-sample tuning.
"""

from typing import Iterable

from model_market_validation import model_market_summary, paired_observations, DIVERGENCE_BINS
from signal_ablation import signal_ablation_scorecard

MIN_COUPONS = 20
MIN_MATCHES = 200
MIN_DIVERGENCE_BUCKET_MATCHES = 50
MIN_SIGNAL_OBSERVATIONS = 50
MIN_SIGNAL_COUPONS = 10


def _divergence_diagnostics(coupons: Iterable) -> list[dict]:
    rows = paired_observations(coupons)
    out: list[dict] = []
    for lo, hi, label in DIVERGENCE_BINS:
        bucket = [r for r in rows if lo <= float(r["divergence"]) < hi]
        n = len(bucket)
        if not n:
            continue
        brier_gain = sum(float(r["brier_gain"]) for r in bucket) / n
        ll_gain = sum(float(r["log_loss_gain"]) for r in bucket) / n
        out.append({
            "bucket": label,
            "matches": n,
            "review_ready": n >= MIN_DIVERGENCE_BUCKET_MATCHES,
            "brier_gain": brier_gain,
            "log_loss_gain": ll_gain,
            "direction": (
                "MODELL BÄTTRE" if brier_gain > 0 and ll_gain > 0 else
                "MARKNAD BÄTTRE" if brier_gain < 0 and ll_gain < 0 else
                "BLANDAD"
            ),
        })
    return out


def market_anchor_decision(coupons: Iterable) -> dict:
    coupons = list(coupons)
    mm = model_market_summary(coupons, min_coupons=MIN_COUPONS, min_matches=MIN_MATCHES)
    signals = signal_ablation_scorecard(
        coupons, min_observations=MIN_SIGNAL_OBSERVATIONS, min_coupons=MIN_SIGNAL_COUPONS
    )
    mature_signals = [r for r in signals if r["review_ready"]]
    positive_signals = [r for r in mature_signals if r["brier_contribution"] > 0 and r["log_loss_contribution"] > 0]
    negative_signals = [r for r in mature_signals if r["brier_contribution"] < 0 and r["log_loss_contribution"] < 0]
    divergence = _divergence_diagnostics(coupons)
    mature_divergence = [r for r in divergence if r["review_ready"]]
    harmful_large_moves = [
        r for r in mature_divergence
        if r["bucket"] in {"5–10 p.e.", "10+ p.e."}
        and r["brier_gain"] < 0 and r["log_loss_gain"] < 0
    ]

    if not mm["review_ready"]:
        status = "INGET PREDIKTIVT EXPERIMENT ÄNNU"
        action = "Samla mer prospektiv data. Behåll bookmakerankaret och nuvarande motorer oförändrade."
        experiment = None
    else:
        bg = float(mm["brier_gain"])
        lg = float(mm["log_loss_gain"])
        if bg < 0 and lg < 0:
            status = "MARKNADSANKARET SKA PRIORITERAS"
            action = (
                "Marknaden är bättre på både Brier score och log loss i det mogna parade samplet. "
                "Nästa tillåtna steg är ett separat, versionsregistrerat experiment som drar modellen närmare marknaden – inte en direkt produktionsändring."
            )
            experiment = "TESTA MINDRE MODELLJUSTERINGAR MOT MARKNADSANKARET"
        elif bg > 0 and lg > 0:
            if positive_signals:
                best = max(positive_signals, key=lambda r: float(r["brier_contribution"]))
                status = "PREDIKTIVT EXPERIMENT KAN MOTIVERAS"
                action = (
                    f"Modellen är bättre än marknaden på båda huvudmåtten och {best['name'].lower()} har positivt marginalbidrag i ett moget ablationssample. "
                    "Testa signalen eller dess vikt i en separat prospektiv kandidatversion; ändra inte produktionen automatiskt."
                )
                experiment = f"VALIDERA {str(best['name']).upper()} I SEPARAT KANDIDATMODELL"
            else:
                status = "MODELLEN SER LOVANDE UT – MEN SIGNALEN ÄR OKLAR"
                action = (
                    "Modellen slår marknaden på båda huvudmåtten, men ingen enskild verifierad signal har ännu ett moget positivt ablationsresultat. "
                    "Samla mer signalhistorik innan vikter ändras."
                )
                experiment = None
        else:
            status = "BLANDAD EVIDENS – ÄNDRA INGET"
            action = "Brier score och log loss pekar åt olika håll. Ingen prediktiv ändring är motiverad."
            experiment = None

    warnings: list[str] = []
    if harmful_large_moves:
        warnings.append(
            "Större modellavvikelser från marknaden (5+ procentenheter total sannolikhetsförflyttning) är sämre än marknaden i minst ett tillräckligt stort segment."
        )
    if negative_signals:
        names = ", ".join(str(r["name"]) for r in negative_signals[:3])
        warnings.append(f"Mogna ablationsdata visar negativt marginalbidrag för: {names}.")

    return {
        "status": status,
        "action": action,
        "candidate_experiment": experiment,
        "model_market": mm,
        "signals": signals,
        "positive_mature_signals": len(positive_signals),
        "negative_mature_signals": len(negative_signals),
        "divergence": divergence,
        "warnings": warnings,
        "automatic_model_change": False,
        "engine_change_allowed": False,
        "requirements": {
            "min_coupons": MIN_COUPONS,
            "min_matches": MIN_MATCHES,
            "min_divergence_bucket_matches": MIN_DIVERGENCE_BUCKET_MATCHES,
            "min_signal_observations": MIN_SIGNAL_OBSERVATIONS,
            "min_signal_coupons": MIN_SIGNAL_COUPONS,
        },
    }
