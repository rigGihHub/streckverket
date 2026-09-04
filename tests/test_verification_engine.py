from dataclasses import replace
from core import MatchInput
from facit import make_coupon_snapshot, with_results
from verification_engine import benchmark_against_market


def _coupon(cid, model=(0.70,0.20,0.10), market=(0.45,0.30,0.25), available=True):
    matches=[]
    for i in range(13):
        odds=tuple(1.0/p for p in market)
        matches.append(MatchInput(i+1, f'H{i}', f'A{i}', odds=odds, public=(0.5,0.3,0.2), model=model, market_available=available))
    c=make_coupon_snapshot(cid, matches, [('1',)]*13, source='test', strategy='MAX13', budget=13, rows=1, model_coverage=.1, captured_at=f'2026-01-{int(cid):02d}T12:00:00+00:00')
    return with_results(c, {i:'1' for i in range(1,14)})


def test_too_little_data_never_claims_edge():
    r=benchmark_against_market([_coupon('01')], min_sample=100)
    assert r.matches == 13
    assert r.verdict == 'FÖR LITE DATA'


def test_clear_model_improvement_can_be_lovande_after_enough_data():
    coupons=[_coupon(f'{i:02d}') for i in range(1,9)]
    r=benchmark_against_market(coupons, min_sample=100)
    assert r.matches == 104
    assert r.brier_gain > 0
    assert r.logloss_gain > 0
    assert r.verdict == 'LOVANDE EDGE'


def test_bad_model_marks_market_better():
    coupons=[_coupon(f'{i:02d}', model=(0.20,0.40,0.40), market=(0.70,0.20,0.10)) for i in range(1,9)]
    r=benchmark_against_market(coupons, min_sample=100)
    assert r.brier_gain < 0
    assert r.verdict == 'MARKNADEN BÄTTRE'


def test_missing_market_is_excluded():
    r=benchmark_against_market([_coupon('01', available=False)])
    assert r.matches == 0
    assert r.verdict == 'INGET UNDERLAG'


def test_market_availability_roundtrips_snapshot():
    c=_coupon('01', available=False)
    assert all(m.market_available is False for m in c.matches)
