from __future__ import annotations

"""Prospective audit of system-level P(13) efficiency.

The audit only uses counterfactual systems that were frozen before kickoff.
It never searches old coupons after seeing results.  Actual results are used
only as a secondary diagnostic after the pre-registered systems are fixed.
"""

from dataclasses import dataclass
from typing import Iterable

from core import SIGNS


@dataclass(frozen=True)
class P13AuditRow:
    coupon_id: str
    original_rows: int
    original_coverage: float
    best_label: str
    best_rows: int
    best_coverage: float
    coverage_delta_pp: float
    relative_uplift: float | None
    selections_changed: int
    completed: bool
    original_hits: int | None
    best_hits: int | None
    original_13: bool | None
    best_13: bool | None


def _variants(coupon):
    return tuple(getattr(coupon, "counterfactual_systems", ()) or ())


def _is_original(variant) -> bool:
    return str(getattr(variant, "origin", "")) == "current_system" or str(getattr(variant, "label", "")) == "ORIGINAL"


def _valid_variant(variant) -> bool:
    sels = tuple(getattr(variant, "selections", ()) or ())
    return (
        len(sels) == 13
        and all(sel and all(sign in SIGNS for sign in sel) for sel in sels)
        and int(getattr(variant, "rows", 0) or 0) >= 1
        and float(getattr(variant, "model_coverage", 0.0) or 0.0) > 0
    )


def _hits(coupon, selections) -> int | None:
    matches = tuple(getattr(coupon, "matches", ()) or ())
    if len(matches) != 13 or not all(getattr(m, "result", None) in SIGNS for m in matches):
        return None
    return sum(int(str(m.result) in tuple(sel)) for m, sel in zip(matches, selections))


def _changed(a, b) -> int:
    return sum(int(tuple(x) != tuple(y)) for x, y in zip(a, b))


def audit_coupon(coupon) -> P13AuditRow | None:
    """Compare frozen original with best frozen same-budget counterfactual.

    All variants originate from the prospective snapshot routine and therefore
    share the coupon's then-known matches, budget and user locks.  No new system
    is reconstructed here.
    """
    variants = [v for v in _variants(coupon) if _valid_variant(v)]
    original = next((v for v in variants if _is_original(v)), None)
    if original is None:
        return None

    # The snapshot generator creates alternatives under the same maximum budget
    # and locks.  Keep an additional row guard so malformed/imported history
    # cannot make a larger system look like a same-budget improvement.
    budget = int(getattr(coupon, "budget", 0) or 0)
    eligible = [v for v in variants if int(v.rows) <= budget] if budget > 0 else variants
    if not eligible:
        return None
    best = max(eligible, key=lambda v: (float(v.model_coverage), -int(v.rows), str(v.label)))

    oc = float(original.model_coverage)
    bc = float(best.model_coverage)
    delta = bc - oc
    rel = (delta / oc) if oc > 0 else None
    oh = _hits(coupon, original.selections)
    bh = _hits(coupon, best.selections)

    return P13AuditRow(
        coupon_id=str(getattr(coupon, "coupon_id", "")),
        original_rows=int(original.rows),
        original_coverage=oc,
        best_label=str(best.label),
        best_rows=int(best.rows),
        best_coverage=bc,
        coverage_delta_pp=100.0 * delta,
        relative_uplift=rel,
        selections_changed=_changed(original.selections, best.selections),
        completed=oh is not None,
        original_hits=oh,
        best_hits=bh,
        original_13=(oh == 13) if oh is not None else None,
        best_13=(bh == 13) if bh is not None else None,
    )


def audit_rows(coupons: Iterable) -> list[dict]:
    rows = []
    for coupon in coupons:
        a = audit_coupon(coupon)
        if a is None:
            continue
        rows.append({
            "Kupong": a.coupon_id,
            "Originalrader": a.original_rows,
            "Bästa frysta alternativ": a.best_label,
            "Alternativets rader": a.best_rows,
            "Original P(13)": a.original_coverage,
            "Bästa frysta P(13)": a.best_coverage,
            "P(13)-skillnad pp": a.coverage_delta_pp,
            "Relativ förbättring": a.relative_uplift,
            "Ändrade matcher": a.selections_changed,
            "Original träffar": a.original_hits,
            "Alternativ träffar": a.best_hits,
            "Alternativ räddade 13": bool(a.best_13 and not a.original_13) if a.completed else None,
        })
    return rows


def system_p13_summary(coupons: Iterable, *, min_review_coupons: int = 20, material_relative_uplift: float = 0.01) -> dict:
    coupons = list(coupons)
    audits = [a for c in coupons if (a := audit_coupon(c)) is not None]
    n = len(audits)
    with_headroom = [a for a in audits if (a.relative_uplift or 0.0) >= material_relative_uplift]
    completed = [a for a in audits if a.completed]
    rescues = [a for a in completed if a.best_13 and not a.original_13]
    harms = [a for a in completed if a.original_13 and not a.best_13]
    mean_delta = sum(a.coverage_delta_pp for a in audits) / n if n else None
    mean_rel = sum((a.relative_uplift or 0.0) for a in audits) / n if n else None

    review_ready = n >= int(min_review_coupons)
    if not n:
        status = "SAMLA PROSPEKTIVA SYSTEMALTERNATIV"
        lesson = "Inga kuponger med före-match frysta systemalternativ finns. Streckverket rekonstruerar inte gamla system i efterhand."
    elif not review_ready:
        status = "SAMLA MER PROSPEKTIV HISTORIK"
        lesson = f"{n} kuponger kan granskas. Minst {min_review_coupons} krävs innan systemallokeringen får pekas ut som ett återkommande problem."
    else:
        share = len(with_headroom) / n
        if share >= 0.25 and (mean_rel or 0.0) >= material_relative_uplift:
            status = "GRANSKA SYSTEM-/BUDGETALLOKERING"
            lesson = (
                "Före-match frysta alternativ visar återkommande modellbaserad P(13)-potential inom samma budgetram. "
                "Nästa experiment bör rikta sig mot systemkonstruktionen, inte automatiskt mot prognosvikterna."
            )
        else:
            status = "INGEN TYDLIG P(13)-ALLOKERINGSBRIST"
            lesson = (
                "De frysta alternativen visar inte tillräcklig återkommande P(13)-förbättring för att systemallokeringen ska pekas ut som huvudproblem."
            )

    return {
        "stored_coupons": len(coupons),
        "auditable_coupons": n,
        "legacy_without_frozen_variants": len(coupons) - n,
        "review_ready": review_ready,
        "min_review_coupons": int(min_review_coupons),
        "material_relative_uplift": float(material_relative_uplift),
        "coupons_with_material_headroom": len(with_headroom),
        "headroom_share": (len(with_headroom) / n) if n else None,
        "mean_p13_delta_pp": mean_delta,
        "mean_relative_p13_uplift": mean_rel,
        "completed_audits": len(completed),
        "counterfactual_13_rescues": len(rescues),
        "counterfactual_13_harms": len(harms),
        "status": status,
        "lesson": lesson,
        "optimization_uses_results": False,
        "result_comparison_is_secondary": True,
        "automatic_strategy_change": False,
        "edge_claim_allowed": False,
    }
