from dataclasses import replace

from core import MatchInput
from facit import make_coupon_snapshot, dumps_facit, loads_facit, with_results
from late_market_benchmark import late_market_benchmark, prospective_observations
from market_timeline import MarketPoint


def _matches():
    out=[]
    for n in range(1,14):
        out.append(MatchInput(n,f'H{n}',f'A{n}',(2,3.333333333,5),(.50,.28,.22),(.58,.24,.18),
                              market_available=True,market_source='Odds',market_bookmaker_count=5,
                              kickoff='2026-09-08T15:00:00+00:00'))
    return out


def _coupon(key='k1', cid='c1'):
    return make_coupon_snapshot(cid,_matches(),[('1',)]*13,source='x',strategy='MAX13',budget=1,rows=1,
        model_coverage=.1,captured_at='2026-09-08T10:00:00+00:00',model_version='3.61.0',market_timeline_key=key)


def _point(n, market, at='2026-09-08T14:30:00+00:00', key='k1'):
    return MarketPoint(key,n,f'H{n}',f'A{n}',at,'2026-09-08T15:00:00+00:00',market,True,'Odds',5,at)


def test_snapshot_stores_explicit_market_timeline_key_and_roundtrips():
    c=_coupon()
    restored=loads_facit(dumps_facit([c]))[0]
    assert restored.market_timeline_key=='k1'


def test_with_results_preserves_market_timeline_key():
    c=with_results(_coupon(),{1:'1'})
    assert c.market_timeline_key=='k1'


def test_legacy_coupon_without_key_is_never_backfilled():
    c=replace(_coupon(),market_timeline_key='')
    rows, meta=prospective_observations([c],[_point(1,(.54,.26,.20))])
    assert rows==[] and meta['excluded_legacy_coupons']==1


def test_same_time_snapshot_point_is_not_counted_as_later_market():
    c=_coupon()
    p=_point(1,(.50,.28,.22),at='2026-09-08T10:00:00+00:00')
    rows, meta=prospective_observations([c],[p])
    assert rows==[] and meta['excluded_no_later_point']==13


def test_post_kickoff_point_is_excluded():
    c=_coupon()
    p=_point(1,(.56,.25,.19),at='2026-09-08T15:01:00+00:00')
    rows,_=prospective_observations([c],[p])
    assert rows==[]


def test_market_move_toward_model_is_detected_without_outcome_data():
    c=_coupon()
    points=[_point(n,(.55,.25,.20)) for n in range(1,14)]
    r=late_market_benchmark([c],points,min_matches=1,min_coupons=1)
    assert r['prospective_matches']==13 and r['prospective_coupons']==1
    assert r['toward']==13 and r['away']==0 and r['toward_rate']==1.0
    assert all(s.status=='GRANSKNINGSBAR' for s in r['segments'] if s.matches)
    assert r['automatic_model_weight'] is False and r['edge_claim_allowed'] is False


def test_move_away_from_model_is_detected():
    c=_coupon()
    points=[_point(n,(.44,.31,.25)) for n in range(1,14)]
    r=late_market_benchmark([c],points,min_matches=1,min_coupons=1)
    assert r['away']==13 and r['toward']==0


def test_review_gate_requires_matches_and_coupon_diversity():
    coupons=[_coupon(key=f'k{i}',cid=f'c{i}') for i in range(2)]
    points=[]
    for i in range(2):
        points.extend(_point(n,(.55,.25,.20),key=f'k{i}') for n in range(1,14))
    r=late_market_benchmark(coupons,points,min_matches=20,min_coupons=3)
    seg=next(s for s in r['segments'] if s.matches)
    assert seg.matches==26 and seg.coupons==2 and seg.status=='SAMLA MER DATA'
