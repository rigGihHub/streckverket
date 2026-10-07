from __future__ import annotations

"""Prospective audit of frozen system structure under an identical row budget.

No historical search is performed here.  Only counterfactual systems that were
already frozen with the coupon are eligible, and the winner is selected solely
by frozen model P(13).  Results are secondary diagnostics only.
"""

from dataclasses import dataclass
from typing import Iterable
from core import SIGNS

@dataclass(frozen=True)
class OptimizerAudit:
    coupon_id: str
    rows: int
    original_coverage: float
    best_label: str
    best_coverage: float
    coverage_delta_pp: float
    relative_uplift: float | None
    changed_matches: int
    spike_to_guard: int
    guard_to_spike: int
    half_full_changes: int
    same_size_sign_changes: int
    completed: bool
    original_hits: int | None
    best_hits: int | None


def _variants(coupon):
    return tuple(getattr(coupon, "counterfactual_systems", ()) or ())


def _valid(v) -> bool:
    sels = tuple(getattr(v, "selections", ()) or ())
    return len(sels) == 13 and all(sel and all(s in SIGNS for s in sel) for sel in sels) and int(getattr(v, "rows", 0) or 0) > 0 and float(getattr(v, "model_coverage", 0.0) or 0.0) > 0


def _is_original(v) -> bool:
    return str(getattr(v, "origin", "")) == "current_system" or str(getattr(v, "label", "")).upper() == "ORIGINAL"


def _hits(coupon, selections) -> int | None:
    matches = tuple(getattr(coupon, "matches", ()) or ())
    if len(matches) != 13 or not all(getattr(m, "result", None) in SIGNS for m in matches):
        return None
    return sum(int(str(m.result) in tuple(sel)) for m, sel in zip(matches, selections))


def audit_coupon_optimizer(coupon) -> OptimizerAudit | None:
    variants = [v for v in _variants(coupon) if _valid(v)]
    original = next((v for v in variants if _is_original(v)), None)
    if original is None:
        return None
    alternatives = [v for v in variants if int(v.rows) == int(original.rows) and tuple(v.selections) != tuple(original.selections)]
    if not alternatives:
        return None
    best = max(alternatives, key=lambda v: (float(v.model_coverage), str(v.label)))
    oc, bc = float(original.model_coverage), float(best.model_coverage)
    delta = bc - oc
    rel = delta / oc if oc > 0 else None
    changed = s2g = g2s = hf = same = 0
    for old, new in zip(original.selections, best.selections):
        old, new = tuple(old), tuple(new)
        if old == new:
            continue
        changed += 1
        if len(old) == 1 and len(new) > 1:
            s2g += 1
        elif len(old) > 1 and len(new) == 1:
            g2s += 1
        elif {len(old), len(new)} == {2, 3}:
            hf += 1
        elif len(old) == len(new):
            same += 1
    oh, bh = _hits(coupon, original.selections), _hits(coupon, best.selections)
    return OptimizerAudit(str(getattr(coupon, "coupon_id", "")), int(original.rows), oc, str(best.label), bc, 100.0*delta, rel, changed, s2g, g2s, hf, same, oh is not None, oh, bh)


def optimizer_audit_rows(coupons: Iterable) -> list[dict]:
    out=[]
    for c in coupons:
        a=audit_coupon_optimizer(c)
        if a is None: continue
        out.append({
            "Kupong":a.coupon_id,"Rader":a.rows,"Original P(13)":a.original_coverage,"Bästa frysta kombination":a.best_label,
            "Alternativ P(13)":a.best_coverage,"P(13)-skillnad pp":a.coverage_delta_pp,"Relativ förbättring":a.relative_uplift,
            "Ändrade matcher":a.changed_matches,"Spik→gardering":a.spike_to_guard,"Gardering→spik":a.guard_to_spike,
            "Halv↔hel":a.half_full_changes,"Samma storlek, andra tecken":a.same_size_sign_changes,
            "Original träffar":a.original_hits,"Alternativ träffar":a.best_hits,
        })
    return out


def optimizer_audit_summary(coupons: Iterable, *, min_review_coupons: int=20, material_relative_uplift: float=.01, min_material_share: float=.25) -> dict:
    coupons=list(coupons)
    audits=[a for c in coupons if (a:=audit_coupon_optimizer(c)) is not None]
    n=len(audits)
    material=[a for a in audits if (a.relative_uplift or 0.0) >= material_relative_uplift]
    structural=[a for a in material if a.spike_to_guard or a.guard_to_spike or a.half_full_changes]
    completed=[a for a in audits if a.completed]
    result_better=[a for a in completed if (a.best_hits or 0) > (a.original_hits or 0)]
    ready=n >= min_review_coupons
    share=len(material)/n if n else None
    mean_rel=sum((a.relative_uplift or 0.0) for a in audits)/n if n else None
    mean_delta=sum(a.coverage_delta_pp for a in audits)/n if n else None
    if not n:
        status="SAMLA FRYSTA SAMMA-RAD-KANDIDATER"
        lesson="Inga kuponger har ett originalsystem och ett annat före-match fryst system med exakt samma radantal. Gamla system rekonstrueras inte."
    elif not ready:
        status="SAMLA MER PROSPEKTIV OPTIMERARHISTORIK"
        lesson=f"{n} kuponger kan granskas. Minst {min_review_coupons} krävs innan systemstrukturen får pekas ut som ett återkommande problem."
    elif (share or 0.0) >= min_material_share:
        status="GRANSKA COUNTERFACTUAL MAX-13-STRUKTUR"
        lesson="Samma radbudget hade återkommande ett redan fryst alternativ med materiellt högre modellbaserad P(13). Detta motiverar ett separat strategiexperiment, inte en automatisk ändring."
    else:
        status="INGEN TYDLIG STRUKTURELL P(13)-BRIST"
        lesson="De före-match frysta samma-rad-alternativen visar inte tillräckligt återkommande P(13)-headroom för att systemstrukturen ska pekas ut som huvudproblem."
    return {
        "stored_coupons":len(coupons),"auditable_coupons":n,"review_ready":ready,"min_review_coupons":min_review_coupons,
        "material_relative_uplift":material_relative_uplift,"min_material_share":min_material_share,
        "coupons_with_material_headroom":len(material),"material_headroom_share":share,"material_structural_changes":len(structural),
        "mean_p13_delta_pp":mean_delta,"mean_relative_p13_uplift":mean_rel,"completed_audits":len(completed),
        "secondary_result_better":len(result_better),"status":status,"lesson":lesson,
        "exact_same_rows_required":True,"selection_uses_results":False,"results_are_secondary":True,
        "automatic_strategy_change":False,"edge_claim_allowed":False,
    }
