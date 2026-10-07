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
    assert r.verdict == 'FÖR LITE OBEROENDE HISTORIK'


def test_clear_model_improvement_still_needs_enough_separate_coupons():
    coupons=[_coupon(f'{i:02d}') for i in range(1,9)]
    r=benchmark_against_market(coupons, min_sample=100)
    assert r.matches == 104
    assert r.brier_gain > 0
    assert r.logloss_gain > 0
    assert r.verdict == 'FÖR LITE OBEROENDE HISTORIK'


def test_bad_model_marks_market_better():
    coupons=[_coupon(f'{i:02d}', model=(0.20,0.40,0.40), market=(0.70,0.20,0.10)) for i in range(1,9)]
    r=benchmark_against_market(coupons, min_sample=100)
    assert r.brier_gain < 0
    assert r.verdict == 'FÖR LITE OBEROENDE HISTORIK'


def test_missing_market_is_excluded():
    r=benchmark_against_market([_coupon('01', available=False)])
    assert r.matches == 0
    assert r.verdict == 'INGET UNDERLAG'


def test_market_availability_roundtrips_snapshot():
    c=_coupon('01', available=False)
    assert all(m.market_available is False for m in c.matches)


def test_near_kickoff_filter_excludes_early_and_unknown_snapshots():
    from datetime import datetime, timedelta, timezone
    from dataclasses import replace
    base = _coupon('21')
    captured = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
    near_matches = tuple(replace(m, kickoff=(captured + timedelta(hours=2)).isoformat()) for m in base.matches)
    early = _coupon('22')
    early_matches = tuple(replace(m, kickoff=(captured + timedelta(hours=20)).isoformat()) for m in early.matches)
    unknown = _coupon('23')
    unknown_matches = tuple(replace(m, kickoff=None) for m in unknown.matches)
    near = replace(base, captured_at=captured.isoformat(), matches=near_matches)
    early = replace(early, captured_at=captured.isoformat(), matches=early_matches)
    unknown = replace(unknown, captured_at=captured.isoformat(), matches=unknown_matches)
    report = benchmark_against_market([near, early, unknown], min_sample=100, max_hours_before_kickoff=3)
    assert report.matches == 13
    assert report.coupons == 1
