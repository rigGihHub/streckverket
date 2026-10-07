from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Iterable

from strategy_confidence import exact_two_sided_sign_p, holm_adjust
from strategy_league_table import strategy_coupon_results

MIN_TRAIN_COUPONS = 30
TEST_BLOCK_SIZE = 10
MIN_OOS_COUPONS = 20
ALPHA = 0.05


@dataclass(frozen=True)
class WalkForwardFold:
    strategy_a: str
    strategy_b: str
    train_coupons: int
    test_coupons: int
    train_end_coupon_id: str
    test_start_coupon_id: str
    test_end_coupon_id: str
    selected_strategy: str
    train_mean_hits_selected: float | None
    train_mean_hits_other: float | None
    test_wins_selected: int
    test_draws: int
    test_losses_selected: int
    test_mean_hit_delta_selected_minus_other: float | None


@dataclass(frozen=True)
class WalkForwardPair:
    strategy_a: str
    strategy_b: str
    shared_chronological_coupons: int
    folds: int
    decided_folds: int
    oos_coupons: int
    oos_wins_selected: int
    oos_draws: int
    oos_losses_selected: int
    mean_oos_hit_delta_selected_minus_other: float | None
    raw_p: float | None
    holm_p: float | None
    selection_a_folds: int
    selection_b_folds: int
    status: str


def _parse_time(value: object) -> datetime | None:
    text = str(value or '').strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None


def _chronological_results(coupons: Iterable) -> dict[str, tuple[datetime, dict]]:
    """Return one completed frozen-strategy result map per coupon with known capture time.

    We never infer order from coupon IDs. Coupons with missing/unreadable captured_at are
    excluded because walk-forward validity depends on real chronology.
    """
    coupons = list(coupons)
    results = strategy_coupon_results(coupons)
    by_coupon_rows: dict[str, dict] = {}
    for row in results:
        by_coupon_rows.setdefault(str(row.coupon_id), {})[row.strategy] = row

    out: dict[str, tuple[datetime, dict]] = {}
    for coupon in coupons:
        cid = str(getattr(coupon, 'coupon_id', ''))
        ts = _parse_time(getattr(coupon, 'captured_at', None))
        rows = by_coupon_rows.get(cid)
        if not cid or ts is None or not rows:
            continue
        # If duplicate snapshots with the same coupon id exist, keep the earliest
        # chronologically valid pre-result snapshot rather than inventing an order.
        current = out.get(cid)
        if current is None or ts < current[0]:
            out[cid] = (ts, rows)
    return out


def _pair_folds(
    coupons: Iterable,
    strategy_a: str,
    strategy_b: str,
    *,
    min_train: int = MIN_TRAIN_COUPONS,
    test_block: int = TEST_BLOCK_SIZE,
) -> tuple[list[WalkForwardFold], int]:
    data = _chronological_results(coupons)
    shared = [
        (cid, ts, rows[strategy_a], rows[strategy_b])
        for cid, (ts, rows) in data.items()
        if strategy_a in rows and strategy_b in rows
    ]
    shared.sort(key=lambda x: (x[1], x[0]))
    folds: list[WalkForwardFold] = []
    start = int(min_train)
    block = max(1, int(test_block))
    while start + block <= len(shared):
        train = shared[:start]
        test = shared[start:start + block]
        mean_a = sum(x[2].hits for x in train) / len(train)
        mean_b = sum(x[3].hits for x in train) / len(train)
        if mean_a > mean_b:
            selected, sel_idx, oth_idx = strategy_a, 2, 3
            sel_mean, oth_mean = mean_a, mean_b
        elif mean_b > mean_a:
            selected, sel_idx, oth_idx = strategy_b, 3, 2
            sel_mean, oth_mean = mean_b, mean_a
        else:
            selected, sel_idx, oth_idx = 'INGET VAL – TRÄNING OAVGJORD', None, None
            sel_mean = oth_mean = None

        if sel_idx is None:
            wins = draws = losses = 0
            delta = None
        else:
            diffs = [float(x[sel_idx].hits - x[oth_idx].hits) for x in test]
            wins = sum(d > 0 for d in diffs)
            losses = sum(d < 0 for d in diffs)
            draws = len(diffs) - wins - losses
            delta = sum(diffs) / len(diffs)
        folds.append(WalkForwardFold(
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            train_coupons=len(train),
            test_coupons=len(test),
            train_end_coupon_id=train[-1][0],
            test_start_coupon_id=test[0][0],
            test_end_coupon_id=test[-1][0],
            selected_strategy=selected,
            train_mean_hits_selected=sel_mean,
            train_mean_hits_other=oth_mean,
            test_wins_selected=wins,
            test_draws=draws,
            test_losses_selected=losses,
            test_mean_hit_delta_selected_minus_other=delta,
        ))
        start += block
    return folds, len(shared)


def walk_forward_validation(
    coupons: Iterable,
    *,
    min_train: int = MIN_TRAIN_COUPONS,
    test_block: int = TEST_BLOCK_SIZE,
    min_oos: int = MIN_OOS_COUPONS,
    alpha: float = ALPHA,
) -> dict:
    coupons = list(coupons)
    chronological = _chronological_results(coupons)
    strategies = sorted({s for _, rows in chronological.values() for s in rows})
    provisional = []
    all_folds: list[WalkForwardFold] = []
    for a, b in combinations(strategies, 2):
        folds, shared = _pair_folds(coupons, a, b, min_train=min_train, test_block=test_block)
        all_folds.extend(folds)
        decided = [f for f in folds if not f.selected_strategy.startswith('INGET VAL')]
        oos = sum(f.test_coupons for f in decided)
        wins = sum(f.test_wins_selected for f in decided)
        draws = sum(f.test_draws for f in decided)
        losses = sum(f.test_losses_selected for f in decided)
        weighted_delta = None
        if oos:
            weighted_delta = sum(
                float(f.test_mean_hit_delta_selected_minus_other or 0.0) * f.test_coupons
                for f in decided
            ) / oos
        raw = exact_two_sided_sign_p(wins, losses) if oos >= int(min_oos) else None
        provisional.append({
            'a': a, 'b': b, 'shared': shared, 'folds': folds, 'decided': decided,
            'oos': oos, 'wins': wins, 'draws': draws, 'losses': losses,
            'delta': weighted_delta, 'raw': raw,
            'sel_a': sum(f.selected_strategy == a for f in decided),
            'sel_b': sum(f.selected_strategy == b for f in decided),
        })

    p_items = [(i, x['raw']) for i, x in enumerate(provisional) if x['raw'] is not None]
    adjusted = holm_adjust([float(p) for _, p in p_items])
    holm_by_index = {i: p for (i, _), p in zip(p_items, adjusted)}

    pairs: list[WalkForwardPair] = []
    for i, x in enumerate(provisional):
        holm = holm_by_index.get(i)
        if x['oos'] < int(min_oos):
            status = 'FÖR LITE WALK-FORWARD-HISTORIK'
        elif x['wins'] + x['losses'] == 0:
            status = 'INGEN RIKTNINGSINFORMATION I SENARE KUPONGER'
        elif holm is not None and holm <= float(alpha):
            status = 'SIGNAL I SENARE KUPONGER – MANUELL GRANSKNING'
        else:
            status = 'INGEN KORRIGERAD SIGNAL I SENARE KUPONGER'
        pairs.append(WalkForwardPair(
            strategy_a=x['a'], strategy_b=x['b'], shared_chronological_coupons=x['shared'],
            folds=len(x['folds']), decided_folds=len(x['decided']), oos_coupons=x['oos'],
            oos_wins_selected=x['wins'], oos_draws=x['draws'], oos_losses_selected=x['losses'],
            mean_oos_hit_delta_selected_minus_other=x['delta'], raw_p=x['raw'], holm_p=holm,
            selection_a_folds=x['sel_a'], selection_b_folds=x['sel_b'], status=status,
        ))

    reviewable = [p for p in pairs if p.oos_coupons >= int(min_oos)]
    signals = [p for p in pairs if p.status == 'SIGNAL I SENARE KUPONGER – MANUELL GRANSKNING']
    return {
        'pairs': pairs,
        'folds': all_folds,
        'chronological_coupons': len(chronological),
        'excluded_without_valid_chronology': max(0, len({str(getattr(c, 'coupon_id', '')) for c in coupons}) - len(chronological)),
        'reviewable_pairs': len(reviewable),
        'signals_after_holm': len(signals),
        'min_train': int(min_train),
        'test_block': int(test_block),
        'min_oos': int(min_oos),
        'alpha': float(alpha),
        'method': 'Expanderande walk-forward: äldre kuponger väljer strategi, nästa 10 kuponger testar valet; Holm-korrigering över strategipar.',
        'status': 'FÖR LITE KRONOLOGISK PROSPEKTIV HISTORIK' if not reviewable else (
            'WALK-FORWARD-SIGNALER FINNS – MANUELL GRANSKNING' if signals else 'INGEN KORRIGERAD WALK-FORWARD-SIGNAL'
        ),
        'edge_claim_allowed': False,
        'roi_claim_allowed': False,
        'automatic_strategy_change_allowed': False,
        'formal_out_of_sample_proof': False,
    }
