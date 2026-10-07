from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
from core import SIGNS
from budget_workshop import optimize_for_budget
from budget_reallocation import best_reallocation

@dataclass(frozen=True)
class CounterfactualSystemSnapshot:
    label: str
    origin: str
    selections: tuple[tuple[str, ...], ...]
    rows: int
    model_coverage: float
    aliases: tuple[str, ...] = ()

@dataclass(frozen=True)
class CounterfactualResult:
    coupon_id: str
    label: str
    origin: str
    completed: bool
    system_hits: int | None
    thirteen_correct: bool | None
    rows: int
    model_coverage: float


def _sel_tuple(selections):
    return tuple(tuple(str(s) for s in sel) for sel in selections)


def _apply_best_swap(matches, system: dict, locks=None):
    move = best_reallocation(matches, system, locks=locks)
    if move is None:
        return None
    sels = [tuple(x) for x in system['selections']]
    idx = {int(m.number): i for i, m in enumerate(matches)}
    di, ri = idx.get(move.donor_match_number), idx.get(move.recipient_match_number)
    if di is None or ri is None:
        return None
    sels[di] = tuple(move.donor_to); sels[ri] = tuple(move.recipient_to)
    return {
        'selections': sels,
        'rows': int(move.rows),
        'coverage': float(move.new_coverage),
    }


def snapshot_counterfactual_systems(matches, system: dict, *, budget: int, locks: Mapping[int, Sequence[str]] | None = None) -> tuple[CounterfactualSystemSnapshot, ...]:
    """Freeze systems that genuinely existed before kickoff for later comparison.

    Same coupon, budget and user locks. Duplicates are removed by exact selections.
    This is a system-construction experiment, not a payout/ROI experiment.
    """
    candidates = [('ORIGINAL', 'current_system', system)]
    swapped = _apply_best_swap(matches, system, locks=locks)
    if swapped is not None:
        candidates.append(('BÄSTA SWAP', 'budget_reallocation', swapped))
    for label, strategy in [('MAX 13', 'MAX 13'), ('VÄRDE', 'VÄRDE')]:
        try:
            alt = optimize_for_budget(matches, int(budget), strategy, locks)
            candidates.append((label, f'optimizer:{strategy}', alt))
        except (ValueError, TypeError):
            continue

    # Store one physical system per unique selection set, but preserve the names of
    # strategies that independently produced exactly the same system. This matters
    # for future paired strategy comparisons: identical output is a real tie, not
    # evidence that the duplicate strategy was absent.
    by_selections = {}
    order = []
    for label, origin, obj in candidates:
        sels=_sel_tuple(obj.get('selections', ()))
        if len(sels) != 13 or any(not x or any(s not in SIGNS for s in x) for x in sels):
            continue
        if sels not in by_selections:
            by_selections[sels] = {
                'label': label, 'origin': origin, 'obj': obj, 'aliases': []
            }
            order.append(sels)
        elif label != by_selections[sels]['label'] and label not in by_selections[sels]['aliases']:
            by_selections[sels]['aliases'].append(label)

    out=[]
    for sels in order:
        item = by_selections[sels]
        obj = item['obj']
        out.append(CounterfactualSystemSnapshot(
            label=item['label'], origin=item['origin'], selections=sels,
            rows=int(obj.get('rows', 0)), model_coverage=float(obj.get('coverage', 0.0)),
            aliases=tuple(item['aliases']),
        ))
    return tuple(out)


def evaluate_counterfactual(coupon, variant: CounterfactualSystemSnapshot) -> CounterfactualResult:
    complete = len(coupon.matches) == 13 and all(getattr(m,'result',None) in SIGNS for m in coupon.matches)
    if not complete:
        return CounterfactualResult(str(coupon.coupon_id), variant.label, variant.origin, False, None, None, variant.rows, variant.model_coverage)
    if len(variant.selections) != 13:
        return CounterfactualResult(str(coupon.coupon_id), variant.label, variant.origin, True, None, None, variant.rows, variant.model_coverage)
    hits=sum(1 for m,sel in zip(coupon.matches, variant.selections) if m.result in sel)
    return CounterfactualResult(str(coupon.coupon_id), variant.label, variant.origin, True, hits, hits==13, variant.rows, variant.model_coverage)


def counterfactual_results(coupons: Iterable) -> list[CounterfactualResult]:
    out=[]
    for c in coupons:
        for v in tuple(getattr(c,'counterfactual_systems',()) or ()):
            out.append(evaluate_counterfactual(c,v))
    return out


def counterfactual_summary(coupons: Iterable) -> dict:
    coupons=list(coupons)
    prospective=[c for c in coupons if tuple(getattr(c,'counterfactual_systems',()) or ())]
    rows=[r for r in counterfactual_results(prospective) if r.completed and r.system_hits is not None]
    grouped={}
    for r in rows:
        g=grouped.setdefault(r.label, {'label':r.label,'coupons':0,'mean_hits':0.0,'thirteen_correct':0,'rows_total':0})
        g['coupons']+=1; g['mean_hits']+=r.system_hits; g['thirteen_correct']+=int(bool(r.thirteen_correct)); g['rows_total']+=r.rows
    table=[]
    for g in grouped.values():
        n=g['coupons']; g['mean_hits']=g['mean_hits']/n; g['mean_rows']=g.pop('rows_total')/n
        g['status']='GRANSKNINGSBAR' if n>=20 else 'FÖR LITE PROSPEKTIV HISTORIK'
        table.append(g)
    table.sort(key=lambda x:(-x['coupons'], -x['mean_hits'], x['label']))
    return {'prospective_coupons':len(prospective),'legacy_without_variants':len(coupons)-len(prospective),'variants':table,'edge_claim_allowed':False}
