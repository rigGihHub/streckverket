from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Iterable

from strategy_robustness import segment_matchups

MIN_SHARED_FOR_CONFIDENCE = 30
ALPHA = 0.05


@dataclass(frozen=True)
class ConfidenceTest:
    dimension: str
    segment: str
    strategy_a: str
    strategy_b: str
    shared_coupons: int
    decisive_coupons: int
    wins_a: int
    wins_b: int
    mean_hit_delta_a_minus_b: float
    raw_p: float | None
    holm_p: float | None
    status: str
    direction: str


def exact_two_sided_sign_p(wins_a: int, wins_b: int) -> float | None:
    """Exact two-sided sign test under p=0.5, excluding draws.

    This is a diagnostic paired-coupon test, not proof of profitability or independence.
    """
    a = int(wins_a)
    b = int(wins_b)
    n = a + b
    if n <= 0:
        return None
    k = min(a, b)
    lower = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * lower)


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm family-wise error adjustment, preserving input order."""
    if not p_values:
        return []
    indexed = sorted(enumerate(float(p) for p in p_values), key=lambda x: x[1])
    m = len(indexed)
    adjusted = [1.0] * m
    running = 0.0
    for rank, (idx, p) in enumerate(indexed):
        value = min(1.0, (m - rank) * p)
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def strategy_confidence(
    coupons: Iterable,
    *,
    min_shared: int = MIN_SHARED_FOR_CONFIDENCE,
    alpha: float = ALPHA,
) -> dict:
    """Apply a conservative multiple-testing guard to segmented paired comparisons.

    Segment definitions come from frozen pre-result inputs in strategy_robustness.
    Only matchups with >= min_shared shared completed coupons enter the Holm family.
    Draws remain in sample-size reporting but are excluded from the sign-test direction.
    """
    matchups = segment_matchups(list(coupons), min_shared=min_shared)
    eligible = [m for m in matchups if m.status == 'GRANSKNINGSBAR']

    raw_ps: list[float] = []
    raw_by_index: dict[int, float] = {}
    for i, m in enumerate(eligible):
        p = exact_two_sided_sign_p(m.wins_a, m.wins_b)
        if p is not None:
            raw_by_index[i] = p
            raw_ps.append(p)
    adjusted = holm_adjust(raw_ps)
    adj_iter = iter(adjusted)

    tests: list[ConfidenceTest] = []
    for i, m in enumerate(eligible):
        raw = raw_by_index.get(i)
        holm = next(adj_iter) if raw is not None else None
        decisive = int(m.wins_a + m.wins_b)
        delta = float(m.mean_hits_a - m.mean_hits_b)
        if raw is None:
            status = 'INGEN RIKTNINGSINFORMATION'
            direction = 'OAVGJORT'
        elif holm is not None and holm <= float(alpha):
            status = 'SIGNAL EFTER MULTIPEL-KORRIGERING'
            direction = m.strategy_a if m.wins_a > m.wins_b else m.strategy_b
        else:
            status = 'INGEN SIGNAL EFTER MULTIPEL-KORRIGERING'
            direction = 'INGEN'
        tests.append(ConfidenceTest(
            dimension=m.dimension,
            segment=m.segment,
            strategy_a=m.strategy_a,
            strategy_b=m.strategy_b,
            shared_coupons=m.shared_coupons,
            decisive_coupons=decisive,
            wins_a=m.wins_a,
            wins_b=m.wins_b,
            mean_hit_delta_a_minus_b=delta,
            raw_p=raw,
            holm_p=holm,
            status=status,
            direction=direction,
        ))

    significant = [t for t in tests if t.status == 'SIGNAL EFTER MULTIPEL-KORRIGERING']
    return {
        'tests': tests,
        'family_size': len(tests),
        'significant_after_holm': len(significant),
        'min_shared': int(min_shared),
        'alpha': float(alpha),
        'method': 'Exakt tvåsidigt parat teckentest på kupongnivå + Holm-korrigering',
        'status': 'INGA KORRIGERADE SIGNALER' if tests and not significant else (
            'KORRIGERADE SIGNALER FINNS – KRÄVER MANUELL GRANSKNING' if significant else 'FÖR LITE HISTORIK FÖR KONFIDENSTEST'
        ),
        'edge_claim_allowed': False,
        'roi_claim_allowed': False,
        'automatic_strategy_change_allowed': False,
        'formal_proof': False,
    }
