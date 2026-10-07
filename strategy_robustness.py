from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable

from core import SIGNS
from strategy_league_table import paired_matchups

MIN_SHARED_PER_SEGMENT = 20


@dataclass(frozen=True)
class CouponSegmentProfile:
    coupon_id: str
    favorite_picture: str
    crowding: str
    model_market_gap: str
    favorite_count_60: int
    mean_crowd_concentration: float
    mean_model_market_gap: float


@dataclass(frozen=True)
class SegmentMatchup:
    dimension: str
    segment: str
    strategy_a: str
    strategy_b: str
    shared_coupons: int
    wins_a: int
    draws: int
    wins_b: int
    mean_hits_a: float
    mean_hits_b: float
    status: str
    matchup_result: str


def _normalized_entropy(values) -> float:
    vals = [max(0.0, float(x)) for x in values]
    total = sum(vals)
    if total <= 0:
        return 0.0
    probs = [x / total for x in vals if x > 0]
    if len(probs) <= 1:
        return 0.0
    return -sum(p * log(p) for p in probs) / log(3)


def coupon_segment_profile(coupon) -> CouponSegmentProfile | None:
    """Classify a frozen coupon without using results.

    Thresholds are deliberately fixed in code and are not learned from outcomes:
    - favourite picture: count of matches with public favourite >=60%
    - crowding: mean 1-normalized entropy of public 1/X/2 shares
    - model-market gap: mean total-variation distance between model and market
    """
    matches = tuple(getattr(coupon, 'matches', ()) or ())
    if len(matches) != 13:
        return None
    if any(len(getattr(m, 'public', ())) != 3 or len(getattr(m, 'model', ())) != 3 or len(getattr(m, 'market', ())) != 3 for m in matches):
        return None

    fav_count = sum(max(float(x) for x in m.public) >= 0.60 for m in matches)
    concentrations = [1.0 - _normalized_entropy(m.public) for m in matches]
    gaps = [0.5 * sum(abs(float(a) - float(b)) for a, b in zip(m.model, m.market)) for m in matches]
    mean_crowd = sum(concentrations) / 13.0
    mean_gap = sum(gaps) / 13.0

    if fav_count >= 7:
        favorite_picture = 'FAVORITDOMINERAD'
    elif fav_count <= 3:
        favorite_picture = 'ÖPPEN'
    else:
        favorite_picture = 'BALANSERAD'

    if mean_crowd >= 0.28:
        crowding = 'HÖG TRÄNGSEL'
    elif mean_crowd <= 0.16:
        crowding = 'LÅG TRÄNGSEL'
    else:
        crowding = 'NORMAL TRÄNGSEL'

    if mean_gap >= 0.08:
        model_market_gap = 'HÖG MODELL–MARKNAD GAP'
    elif mean_gap <= 0.04:
        model_market_gap = 'LÅG MODELL–MARKNAD GAP'
    else:
        model_market_gap = 'NORMAL MODELL–MARKNAD GAP'

    return CouponSegmentProfile(
        coupon_id=str(getattr(coupon, 'coupon_id', '')),
        favorite_picture=favorite_picture,
        crowding=crowding,
        model_market_gap=model_market_gap,
        favorite_count_60=fav_count,
        mean_crowd_concentration=mean_crowd,
        mean_model_market_gap=mean_gap,
    )


def segment_matchups(coupons: Iterable, *, min_shared: int = MIN_SHARED_PER_SEGMENT) -> list[SegmentMatchup]:
    coupons = list(coupons)
    profiles = {str(c.coupon_id): coupon_segment_profile(c) for c in coupons}
    dimensions = {
        'FAVORITBILD': lambda p: p.favorite_picture,
        'PUBLIKTRÄNGSEL': lambda p: p.crowding,
        'MODELL–MARKNAD': lambda p: p.model_market_gap,
    }
    out: list[SegmentMatchup] = []
    for dimension, get_segment in dimensions.items():
        segment_names = sorted({get_segment(p) for p in profiles.values() if p is not None})
        for segment in segment_names:
            subset = [c for c in coupons if profiles.get(str(c.coupon_id)) is not None and get_segment(profiles[str(c.coupon_id)]) == segment]
            for m in paired_matchups(subset, min_shared=min_shared):
                out.append(SegmentMatchup(
                    dimension=dimension,
                    segment=segment,
                    strategy_a=m.strategy_a,
                    strategy_b=m.strategy_b,
                    shared_coupons=m.shared_coupons,
                    wins_a=m.wins_a,
                    draws=m.draws,
                    wins_b=m.wins_b,
                    mean_hits_a=m.mean_hits_a,
                    mean_hits_b=m.mean_hits_b,
                    status=m.status,
                    matchup_result=m.matchup_result,
                ))
    return out


def strategy_robustness(coupons: Iterable, *, min_shared: int = MIN_SHARED_PER_SEGMENT) -> dict:
    coupons = list(coupons)
    profiles = [p for c in coupons if (p := coupon_segment_profile(c)) is not None]
    matchups = segment_matchups(coupons, min_shared=min_shared)
    qualified = [m for m in matchups if m.status == 'GRANSKNINGSBAR']
    strategies = sorted({x for m in matchups for x in (m.strategy_a, m.strategy_b)})
    rows = []
    for strategy in strategies:
        ms = [m for m in qualified if strategy in (m.strategy_a, m.strategy_b)]
        wins = draws = losses = 0
        dimensions = set()
        segments = set()
        for m in ms:
            dimensions.add(m.dimension)
            segments.add((m.dimension, m.segment))
            if m.matchup_result == 'OAVGJORT':
                draws += 1
            elif m.matchup_result == strategy:
                wins += 1
            else:
                losses += 1
        levels_by_dimension: dict[str, set[str]] = {}
        for m in ms:
            levels_by_dimension.setdefault(m.dimension, set()).add(m.segment)
        contrasting_dimensions = sum(len(levels) >= 2 for levels in levels_by_dimension.values())
        if contrasting_dimensions < 1:
            status = 'FÖR LITE KONTRASTERANDE HISTORIK'
        elif wins and losses:
            status = 'BLANDAD MELLAN MILJÖER'
        elif wins >= 2 and losses == 0:
            status = 'KONSEKVENT POSITIV I GRANSKADE MILJÖER'
        elif losses >= 2 and wins == 0:
            status = 'KONSEKVENT NEGATIV I GRANSKADE MILJÖER'
        else:
            status = 'JÄMN I GRANSKADE MILJÖER'
        rows.append({
            'strategy': strategy,
            'qualified_segments': len(ms),
            'dimensions': len(dimensions),
            'contrasting_dimensions': contrasting_dimensions,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'status': status,
        })
    rows.sort(key=lambda r: (-r['qualified_segments'], -r['wins'], r['losses'], r['strategy']))
    return {
        'coupon_profiles': profiles,
        'matchups': matchups,
        'qualified_matchups': len(qualified),
        'strategies': rows,
        'min_shared_per_segment': int(min_shared),
        'thresholds': {
            'favorite_dominated': 'minst 7 av 13 matcher med publikfavorit >=60%',
            'open': 'högst 3 av 13 matcher med publikfavorit >=60%',
            'high_crowding': 'snittkoncentration >=0,28',
            'low_crowding': 'snittkoncentration <=0,16',
            'high_model_market_gap': 'snitt total-variation >=0,08',
            'low_model_market_gap': 'snitt total-variation <=0,04',
        },
        'edge_claim_allowed': False,
        'roi_claim_allowed': False,
        'strategy_change_allowed': False,
    }
