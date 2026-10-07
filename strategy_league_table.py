from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from core import SIGNS

MIN_SHARED_COUPONS = 20


@dataclass(frozen=True)
class StrategyCouponResult:
    coupon_id: str
    strategy: str
    hits: int
    thirteen_correct: bool
    rows: int


@dataclass(frozen=True)
class PairwiseMatchup:
    strategy_a: str
    strategy_b: str
    shared_coupons: int
    wins_a: int
    draws: int
    wins_b: int
    mean_hits_a: float
    mean_hits_b: float
    thirteen_a: int
    thirteen_b: int
    mean_rows_a: float
    mean_rows_b: float
    status: str
    matchup_result: str


def _complete(coupon) -> bool:
    return len(getattr(coupon, 'matches', ())) == 13 and all(
        getattr(m, 'result', None) in SIGNS for m in coupon.matches
    )


def _labels_for_variant(coupon, variant) -> tuple[str, ...]:
    labels = [str(getattr(variant, 'label', '') or '').strip()]
    labels.extend(str(x).strip() for x in (getattr(variant, 'aliases', ()) or ()))
    # v3.53 and older did not preserve aliases. The actual strategy used for
    # ORIGINAL is nevertheless explicitly stored on the coupon and is safe to
    # recover as an alias; we do not infer any other missing historical alias.
    if getattr(variant, 'origin', '') == 'current_system':
        actual = str(getattr(coupon, 'strategy', '') or '').strip().upper()
        if actual in {'MAX 13', 'VÄRDE'}:
            labels.append(actual)
    out = []
    for label in labels:
        if label and label not in out:
            out.append(label)
    return tuple(out)


def strategy_coupon_results(coupons: Iterable) -> list[StrategyCouponResult]:
    """Expand frozen systems to strategy-labelled results without hindsight.

    Only complete coupons and systems frozen before kickoff are eligible. Aliases
    represent strategies that produced the exact same frozen system.
    """
    out: list[StrategyCouponResult] = []
    for coupon in coupons:
        variants = tuple(getattr(coupon, 'counterfactual_systems', ()) or ())
        if not variants or not _complete(coupon):
            continue
        result_signs = tuple(m.result for m in coupon.matches)
        seen: set[str] = set()
        for variant in variants:
            selections = tuple(getattr(variant, 'selections', ()) or ())
            if len(selections) != 13:
                continue
            hits = sum(1 for result, selected in zip(result_signs, selections) if result in selected)
            for label in _labels_for_variant(coupon, variant):
                if label in seen:
                    continue
                seen.add(label)
                out.append(StrategyCouponResult(
                    coupon_id=str(coupon.coupon_id), strategy=label, hits=hits,
                    thirteen_correct=(hits == 13), rows=int(getattr(variant, 'rows', 0) or 0),
                ))
    return out


def paired_matchups(coupons: Iterable, *, min_shared: int = MIN_SHARED_COUPONS) -> list[PairwiseMatchup]:
    rows = strategy_coupon_results(coupons)
    by_coupon: dict[str, dict[str, StrategyCouponResult]] = {}
    strategies: set[str] = set()
    for row in rows:
        by_coupon.setdefault(row.coupon_id, {})[row.strategy] = row
        strategies.add(row.strategy)

    out: list[PairwiseMatchup] = []
    for a, b in combinations(sorted(strategies), 2):
        pairs = [(m[a], m[b]) for m in by_coupon.values() if a in m and b in m]
        n = len(pairs)
        if not n:
            continue
        wa = sum(x.hits > y.hits for x, y in pairs)
        wb = sum(y.hits > x.hits for x, y in pairs)
        draws = n - wa - wb
        reviewable = n >= int(min_shared)
        if not reviewable:
            status = 'FÖR LITE GEMENSAM HISTORIK'
            result = 'INGET LIGARESULTAT'
        else:
            status = 'GRANSKNINGSBAR'
            if wa > wb:
                result = a
            elif wb > wa:
                result = b
            else:
                result = 'OAVGJORT'
        out.append(PairwiseMatchup(
            strategy_a=a, strategy_b=b, shared_coupons=n,
            wins_a=wa, draws=draws, wins_b=wb,
            mean_hits_a=sum(x.hits for x, _ in pairs)/n,
            mean_hits_b=sum(y.hits for _, y in pairs)/n,
            thirteen_a=sum(x.thirteen_correct for x, _ in pairs),
            thirteen_b=sum(y.thirteen_correct for _, y in pairs),
            mean_rows_a=sum(x.rows for x, _ in pairs)/n,
            mean_rows_b=sum(y.rows for _, y in pairs)/n,
            status=status, matchup_result=result,
        ))
    return out


def strategy_league(coupons: Iterable, *, min_shared: int = MIN_SHARED_COUPONS) -> dict:
    coupons = list(coupons)
    matchups = paired_matchups(coupons, min_shared=min_shared)
    qualified = [m for m in matchups if m.status == 'GRANSKNINGSBAR']
    strategies = sorted({x for m in matchups for x in (m.strategy_a, m.strategy_b)})
    table = {s: {'strategy': s, 'matchups': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'points': 0} for s in strategies}
    for m in qualified:
        a, b = table[m.strategy_a], table[m.strategy_b]
        a['matchups'] += 1; b['matchups'] += 1
        if m.matchup_result == m.strategy_a:
            a['wins'] += 1; b['losses'] += 1; a['points'] += 3
        elif m.matchup_result == m.strategy_b:
            b['wins'] += 1; a['losses'] += 1; b['points'] += 3
        else:
            a['draws'] += 1; b['draws'] += 1; a['points'] += 1; b['points'] += 1
    league = list(table.values())
    for row in league:
        row['status'] = 'GRANSKNINGSBAR' if row['matchups'] else 'FÖR LITE GEMENSAM HISTORIK'
    league.sort(key=lambda r: (-r['points'], -r['wins'], r['strategy']))
    return {
        'league': league,
        'matchups': matchups,
        'qualified_matchups': len(qualified),
        'total_matchups': len(matchups),
        'min_shared_coupons': int(min_shared),
        'edge_claim_allowed': False,
        'roi_claim_allowed': False,
    }
