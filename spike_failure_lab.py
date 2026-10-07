from __future__ import annotations

"""Prospective diagnostics for system spikes.

The lab evaluates only spikes that were frozen before kickoff in FacitCoupon
history.  It measures whether the probability assigned to the selected spike
was calibrated and compares that same selected outcome with the stored market
anchor when available.  It never changes a spike threshold or model weight.
"""

from collections import defaultdict
from math import isfinite
from typing import Iterable

from core import SIGNS

BINS = (
    (0.0, 0.50, "<50 %"),
    (0.50, 0.55, "50–55 %"),
    (0.55, 0.60, "55–60 %"),
    (0.60, 0.65, "60–65 %"),
    (0.65, 0.70, "65–70 %"),
    (0.70, 0.75, "70–75 %"),
    (0.75, 0.80, "75–80 %"),
    (0.80, 1.0000001, "80 %+")
)


def _complete(coupon) -> bool:
    matches = tuple(getattr(coupon, "matches", ()) or ())
    return len(matches) == 13 and all(getattr(m, "result", None) in SIGNS for m in matches)


def _norm(probs) -> tuple[float, float, float] | None:
    try:
        vals = [max(0.0, float(x)) for x in probs]
    except Exception:
        return None
    if len(vals) != 3 or not all(isfinite(x) for x in vals):
        return None
    total = sum(vals)
    if total <= 0:
        return None
    return tuple(x / total for x in vals)  # type: ignore[return-value]


def _band(p: float) -> str:
    for lo, hi, label in BINS:
        if lo <= p < hi:
            return label
    return "OKÄND"


def spike_rows(coupons: Iterable) -> list[dict]:
    rows: list[dict] = []
    for coupon in coupons:
        if not _complete(coupon):
            continue
        cid = str(getattr(coupon, "coupon_id", ""))
        for match in coupon.matches:
            selected = tuple(getattr(match, "selected", ()) or ())
            if len(selected) != 1 or selected[0] not in SIGNS:
                continue
            sign = selected[0]
            model = _norm(getattr(match, "model", ()))
            if model is None:
                continue
            idx = SIGNS.index(sign)
            p_model = model[idx]
            result = str(getattr(match, "result", ""))
            hit = result == sign
            model_top = SIGNS[max(range(3), key=lambda i: model[i])]
            market = _norm(getattr(match, "market", ())) if bool(getattr(match, "market_available", False)) else None
            p_market = market[idx] if market is not None else None
            rows.append({
                "Kupong": cid,
                "Match": int(getattr(match, "match_number", 0) or 0),
                "Möte": f"{getattr(match, 'home', '')} – {getattr(match, 'away', '')}",
                "Spik": sign,
                "Utfall": result,
                "Träff": hit,
                "Modell p(spik)": p_model,
                "Marknad p(spik)": p_market,
                "Intervall": _band(p_model),
                "Spiken var modellens förstaval": model_top == sign,
                "Miss trots annat modellförstaval": (not hit and model_top != sign),
            })
    return rows


def _binary_brier(rows: list[dict], key: str) -> float | None:
    vals = []
    for row in rows:
        p = row.get(key)
        if p is None:
            continue
        y = 1.0 if row["Träff"] else 0.0
        vals.append((float(p) - y) ** 2)
    return sum(vals) / len(vals) if vals else None


def spike_band_rows(coupons: Iterable, *, min_band_matches: int = 20, min_band_coupons: int = 5) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in spike_rows(coupons):
        grouped[row["Intervall"]].append(row)
    order = {label: i for i, (_, _, label) in enumerate(BINS)}
    out = []
    for label, rows in sorted(grouped.items(), key=lambda kv: order.get(kv[0], 99)):
        n = len(rows)
        coupons_n = len({r["Kupong"] for r in rows})
        mean_p = sum(float(r["Modell p(spik)"]) for r in rows) / n
        hit_rate = sum(int(r["Träff"]) for r in rows) / n
        gap = hit_rate - mean_p
        market_rows = [r for r in rows if r["Marknad p(spik)"] is not None]
        market_mean = (sum(float(r["Marknad p(spik)"]) for r in market_rows) / len(market_rows)) if market_rows else None
        mature = n >= int(min_band_matches) and coupons_n >= int(min_band_coupons)
        if not mature:
            status = "FÖR LITE DATA"
        elif gap <= -0.05:
            status = "ÖVERKONFIDENS ATT GRANSKA"
        elif gap >= 0.05:
            status = "UNDERKONFIDENS ATT GRANSKA"
        else:
            status = "INGEN STOR KALIBRERINGSAVVIKELSE"
        out.append({
            "Intervall": label,
            "Spikar": n,
            "Kuponger": coupons_n,
            "Snitt modell p": mean_p,
            "Faktisk träff": hit_rate,
            "Kalibreringsgap": gap,
            "Snitt marknad p": market_mean,
            "Moget segment": mature,
            "Status": status,
        })
    return out


def spike_failure_summary(
    coupons: Iterable,
    *,
    min_review_spikes: int = 100,
    min_review_coupons: int = 20,
    min_band_matches: int = 20,
    min_band_coupons: int = 5,
) -> dict:
    coupons = list(coupons)
    rows = spike_rows(coupons)
    spike_coupons = len({r["Kupong"] for r in rows})
    n = len(rows)
    hits = sum(int(r["Träff"]) for r in rows)
    misses = n - hits
    mean_p = (sum(float(r["Modell p(spik)"]) for r in rows) / n) if n else None
    hit_rate = (hits / n) if n else None
    gap = (hit_rate - mean_p) if n and hit_rate is not None and mean_p is not None else None
    non_top_misses = sum(int(r["Miss trots annat modellförstaval"]) for r in rows)
    market_rows = [r for r in rows if r["Marknad p(spik)"] is not None]
    model_brier_on_market_sample = _binary_brier(market_rows, "Modell p(spik)")
    market_brier = _binary_brier(market_rows, "Marknad p(spik)")
    bands = spike_band_rows(
        coupons,
        min_band_matches=min_band_matches,
        min_band_coupons=min_band_coupons,
    )
    mature_bands = [b for b in bands if b["Moget segment"]]
    overconfident_bands = [b for b in mature_bands if b["Kalibreringsgap"] <= -0.05]
    ready = n >= int(min_review_spikes) and spike_coupons >= int(min_review_coupons)

    if n == 0:
        status = "SAMLA SPIKFACIT"
        lesson = "Inga färdigspelade prospektivt sparade spikar finns att analysera."
    elif not ready:
        status = "SAMLA MER PROSPEKTIV SPIKHISTORIK"
        lesson = (
            f"{n} spikar över {spike_coupons} kuponger finns. Minst {min_review_spikes} spikar över "
            f"{min_review_coupons} kuponger krävs innan labbet får peka ut ett återkommande spikproblem."
        )
    elif len(overconfident_bands) >= 2:
        status = "GRANSKA SPIKÖVERKONFIDENS"
        lesson = (
            "Minst två mogna sannolikhetsintervall har faktisk spikträff minst 5 procentenheter under den frysta sannolikheten. "
            "Det motiverar ett separat prospektivt experiment om spikdisciplin eller kalibrering – inte en automatisk ny tröskel."
        )
    elif non_top_misses / n >= 0.10:
        status = "GRANSKA SYSTEMETS SPIKVAL"
        lesson = (
            "En märkbar andel av alla sparade spikar missade samtidigt som systemets spiktecken inte var modellens eget förstaval. "
            "Granska systemkonstruktionen innan prognosvikterna ändras."
        )
    elif market_brier is not None and model_brier_on_market_sample is not None and model_brier_on_market_sample > market_brier + 0.005:
        status = "GRANSKA MODELLJUSTERINGAR PÅ SPIKAR"
        lesson = (
            "På exakt samma spiktecken och matcher har bookmakerankaret lägre binär Brier score än Streckverkets frysta sannolikhet. "
            "Granska modelljusteringarna prospektivt innan spikarna görs mer aggressiva."
        )
    else:
        status = "INGET TYDLIGT ÅTERKOMMANDE SPIKPROBLEM"
        lesson = (
            "Det mogna underlaget visar inte ett tillräckligt tydligt återkommande spikfel enligt de förhandsbestämda diagnostikgränserna. "
            "Enskilda spikmissar är väntade även när sannolikheterna är rimliga."
        )

    return {
        "spikes": n,
        "spike_coupons": spike_coupons,
        "hits": hits,
        "misses": misses,
        "hit_rate": hit_rate,
        "mean_model_probability": mean_p,
        "calibration_gap": gap,
        "non_top_spike_misses": non_top_misses,
        "market_comparable_spikes": len(market_rows),
        "model_binary_brier": model_brier_on_market_sample,
        "market_binary_brier": market_brier,
        "review_ready": ready,
        "min_review_spikes": int(min_review_spikes),
        "min_review_coupons": int(min_review_coupons),
        "mature_bands": len(mature_bands),
        "overconfident_bands": len(overconfident_bands),
        "status": status,
        "lesson": lesson,
        "bands": bands,
        "automatic_spike_threshold_change": False,
        "automatic_model_change": False,
        "individual_miss_implies_bad_decision": False,
        "edge_claim_allowed": False,
    }
