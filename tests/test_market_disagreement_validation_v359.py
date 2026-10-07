from dataclasses import replace

from core import MatchInput
from facit import make_coupon_snapshot, with_results
from market_disagreement_validation import market_disagreement_validation, gap_bucket


def _match(n, dispersion=.02, count=5, model=(.55,.25,.20), market=(.48,.28,.24)):
    return MatchInput(n,f'H{n}',f'A{n}',(2,3.5,4),model,(.50,.28,.22),market_available=True,
                      market_source='The Odds API', market_bookmaker_count=count,
                      market_dispersion=dispersion, market_consensus_method='robust median')


def _coupon(i, *, version='3.58.0', dispersion=.02, count=5, result='1', model=(.55,.25,.20), market=(.48,.28,.24)):
    ms=[_match(n,dispersion,count,model,market) for n in range(1,14)]
    c=make_coupon_snapshot(f'c{i}',ms,[('1',)]*13,source='x',strategy='MAX 13',budget=1,rows=1,
                           model_coverage=.1,captured_at=f'2026-09-{(i%28)+1:02d}T10:00:00+00:00',model_version=version)
    return with_results(c,{n:result for n in range(1,14)})


def test_old_snapshots_are_not_backfilled_into_disagreement_validation():
    r=market_disagreement_validation([_coupon(1,version='3.57.0')],min_matches=1,min_coupons=1)
    assert r['prospective_matches']==0
    assert r['excluded_legacy_coupons']==1


def test_missing_dispersion_is_excluded_not_guessed():
    c=_coupon(1)
    ms=tuple(replace(m,market_dispersion=None) for m in c.matches)
    c=replace(c,matches=ms)
    r=market_disagreement_validation([c],min_matches=1,min_coupons=1)
    assert r['prospective_matches']==0
    assert r['excluded_without_diagnostics']==13


def test_segments_use_frozen_v358_confidence_rules():
    coupons=[_coupon(1,dispersion=.02,count=5),_coupon(2,dispersion=.04,count=3),_coupon(3,dispersion=.08,count=3)]
    r=market_disagreement_validation(coupons,min_matches=1,min_coupons=1)
    by={s.segment:s for s in r['segments']}
    assert by['HÖG'].matches==13
    assert by['NORMAL'].matches==13
    assert by['OENIG'].matches==13


def test_review_gate_requires_both_matches_and_coupon_diversity():
    many_matches=[_coupon(i,dispersion=.08,count=3) for i in range(1,8)] # 91 matches, 7 coupons
    r=market_disagreement_validation(many_matches,min_matches=90,min_coupons=8)
    o=next(s for s in r['segments'] if s.segment=='OENIG')
    assert o.matches==91 and o.coupons==7 and o.status=='SAMLA MER DATA'
    r2=market_disagreement_validation(many_matches,min_matches=90,min_coupons=7)
    assert next(s for s in r2['segments'] if s.segment=='OENIG').status=='GRANSKNINGSBAR'


def test_brier_gain_is_market_minus_model_so_positive_means_model_better():
    r=market_disagreement_validation([_coupon(1,result='1',model=(.70,.15,.15),market=(.40,.30,.30))],min_matches=1,min_coupons=1)
    high=next(s for s in r['segments'] if s.segment=='HÖG')
    assert high.brier_gain is not None and high.brier_gain>0


def test_high_vs_disagree_contrast_only_when_both_reviewable():
    r=market_disagreement_validation([_coupon(1,dispersion=.02,count=5)],min_matches=1,min_coupons=1)
    assert r['contrast_status']=='SAMLA MER DATA' and r['high_vs_disagree_brier_gain_delta'] is None
    r2=market_disagreement_validation([_coupon(1,dispersion=.02,count=5),_coupon(2,dispersion=.08,count=3)],min_matches=1,min_coupons=1)
    assert r2['contrast_status']=='KONTRAST GRANSKNINGSBAR'
    assert r2['high_vs_disagree_brier_gain_delta'] is not None


def test_gap_buckets_are_fixed_and_not_result_dependent():
    assert gap_bucket((.50,.30,.20),(.50,.30,.20))=='LÅGT GAP'
    assert gap_bucket((.58,.22,.20),(.50,.30,.20))=='HÖGT GAP'


def test_gap_context_is_exploratory_and_never_changes_model():
    r=market_disagreement_validation([_coupon(1)],min_matches=100,min_coupons=20)
    assert len(r['gap_context'])==9
    assert all(g.status.startswith('EXPLORATIV') for g in r['gap_context'])
    assert r['automatic_model_weight'] is False and r['edge_claim_allowed'] is False
