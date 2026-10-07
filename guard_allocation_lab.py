from __future__ import annotations

"""Prospective diagnostics for where guard budget is placed.

Only counterfactual systems frozen before kickoff are eligible.  To isolate
allocation from stake size, comparisons are restricted to variants with the
exact same row count as the original system.  Actual results are never used to
choose the alternative; they are secondary diagnostics only.
"""

from dataclasses import dataclass
from typing import Iterable

from core import SIGNS


@dataclass(frozen=True)
class GuardAllocationAudit:
    coupon_id: str
    rows: int
    original_coverage: float
    best_label: str
    best_coverage: float
    relative_uplift: float | None
    coverage_delta_pp: float
    guard_additions: int
    guard_removals: int
    same_size_changes: int
    changed_matches: int
    completed: bool
    original_hits: int | None
    best_hits: int | None


def _variants(coupon):
    return tuple(getattr(coupon, "counterfactual_systems", ()) or ())


def _valid(v) -> bool:
    sels = tuple(getattr(v, "selections", ()) or ())
    return (
        len(sels) == 13
        and all(sel and all(sign in SIGNS for sign in sel) for sel in sels)
        and int(getattr(v, "rows", 0) or 0) > 0
        and float(getattr(v, "model_coverage", 0.0) or 0.0) > 0
    )


def _is_original(v) -> bool:
    return str(getattr(v, "label", "")).upper() == "ORIGINAL" or str(getattr(v, "origin", "")) == "current_system"


def _hits(coupon, selections) -> int | None:
    matches = tuple(getattr(coupon, "matches", ()) or ())
    if len(matches) != 13 or not all(getattr(m, "result", None) in SIGNS for m in matches):
        return None
    return sum(int(str(m.result) in tuple(sel)) for m, sel in zip(matches, selections))


def audit_coupon_guard_allocation(coupon) -> GuardAllocationAudit | None:
    """Compare original with best *same-row* frozen alternative.

    Same row count is deliberate: otherwise an apparent guard-allocation gain
    could simply come from spending more of the available budget.
    """
    variants = [v for v in _variants(coupon) if _valid(v)]
    original = next((v for v in variants if _is_original(v)), None)
    if original is None:
        return None

    same_rows = [v for v in variants if int(v.rows) == int(original.rows)]
    alternatives = [v for v in same_rows if tuple(v.selections) != tuple(original.selections)]
    if not alternatives:
        return None

    best = max(alternatives, key=lambda v: (float(v.model_coverage), str(v.label)))
    oc = float(original.model_coverage)
    bc = float(best.model_coverage)
    delta = bc - oc
    rel = (delta / oc) if oc > 0 else None

    adds = removes = same_size = changed = 0
    for old, new in zip(original.selections, best.selections):
        old_t, new_t = tuple(old), tuple(new)
        if old_t == new_t:
            continue
        changed += 1
        if len(new_t) > len(old_t):
            adds += 1
        elif len(new_t) < len(old_t):
            removes += 1
        else:
            same_size += 1

    oh = _hits(coupon, original.selections)
    bh = _hits(coupon, best.selections)
    return GuardAllocationAudit(
        coupon_id=str(getattr(coupon, "coupon_id", "")),
        rows=int(original.rows),
        original_coverage=oc,
        best_label=str(best.label),
        best_coverage=bc,
        relative_uplift=rel,
        coverage_delta_pp=100.0 * delta,
        guard_additions=adds,
        guard_removals=removes,
        same_size_changes=same_size,
        changed_matches=changed,
        completed=oh is not None,
        original_hits=oh,
        best_hits=bh,
    )


def guard_allocation_rows(coupons: Iterable) -> list[dict]:
    rows = []
    for coupon in coupons:
        a = audit_coupon_guard_allocation(coupon)
        if a is None:
            continue
        rows.append({
            "Kupong": a.coupon_id,
            "Rader": a.rows,
            "Original P(13)": a.original_coverage,
            "Bästa samma-rad-alternativ": a.best_label,
            "Alternativ P(13)": a.best_coverage,
            "P(13)-skillnad pp": a.coverage_delta_pp,
            "Relativ förbättring": a.relative_uplift,
            "Garderingar tillagda": a.guard_additions,
            "Garderingar borttagna": a.guard_removals,
            "Samma storlek, andra tecken": a.same_size_changes,
            "Ändrade matcher": a.changed_matches,
            "Original träffar": a.original_hits,
            "Alternativ träffar": a.best_hits,
        })
    return rows


def guard_allocation_summary(
    coupons: Iterable,
    *,
    min_review_coupons: int = 20,
    material_relative_uplift: float = 0.01,
    min_relocation_share: float = 0.25,
) -> dict:
    coupons = list(coupons)
    audits = [a for c in coupons if (a := audit_coupon_guard_allocation(c)) is not None]
    n = len(audits)
    relocations = [a for a in audits if a.guard_additions > 0 and a.guard_removals > 0]
    material = [a for a in relocations if (a.relative_uplift or 0.0) >= float(material_relative_uplift)]
    positive = [a for a in audits if a.coverage_delta_pp > 1e-12]
    completed = [a for a in audits if a.completed]
    result_better = [a for a in completed if (a.best_hits or 0) > (a.original_hits or 0)]
    mean_rel = sum((a.relative_uplift or 0.0) for a in audits) / n if n else None
    mean_delta = sum(a.coverage_delta_pp for a in audits) / n if n else None
    ready = n >= int(min_review_coupons)

    if not n:
        status = "SAMLA FRYSTA SAMMA-RAD-ALTERNATIV"
        lesson = (
            "Inga kuponger har både originalsystem och ett före-match fryst alternativ med exakt samma radantal. "
            "Streckverket rekonstruerar inte gamla garderingar efter facit."
        )
    elif not ready:
        status = "SAMLA MER PROSPEKTIV GARDERINGSHISTORIK"
        lesson = (
            f"{n} kuponger kan granskas med exakt samma radantal. Minst {min_review_coupons} krävs innan "
            "garderingarnas placering får pekas ut som ett återkommande problem."
        )
    else:
        share = len(material) / n
        if share >= float(min_relocation_share):
            status = "GRANSKA GARDERINGSALLOKERING"
            lesson = (
                "På en återkommande andel prospektiva kuponger fanns ett redan fryst system med exakt samma antal rader "
                "som flyttade garderingar mellan matcher och gav minst den förhandsbestämda P(13)-förbättringen. "
                "Det motiverar ett separat strategiexperiment, inte en automatisk ändring."
            )
        else:
            status = "INGEN TYDLIG ÅTERKOMMANDE GARDERINGSBRIST"
            lesson = (
                "Samma-rad-jämförelserna visar inte tillräckligt återkommande P(13)-nytta av att flytta garderingar "
                "för att garderingarnas placering ska pekas ut som huvudproblem."
            )

    return {
        "stored_coupons": len(coupons),
        "auditable_coupons": n,
        "review_ready": ready,
        "min_review_coupons": int(min_review_coupons),
        "material_relative_uplift": float(material_relative_uplift),
        "min_relocation_share": float(min_relocation_share),
        "coupons_with_relocation": len(relocations),
        "coupons_with_material_relocation": len(material),
        "material_relocation_share": (len(material) / n) if n else None,
        "coupons_with_positive_same_row_headroom": len(positive),
        "mean_p13_delta_pp": mean_delta,
        "mean_relative_p13_uplift": mean_rel,
        "completed_audits": len(completed),
        "secondary_result_better": len(result_better),
        "status": status,
        "lesson": lesson,
        "exact_same_rows_required": True,
        "selection_uses_results": False,
        "results_are_secondary": True,
        "automatic_strategy_change": False,
        "edge_claim_allowed": False,
    }
