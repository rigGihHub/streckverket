from dataclasses import replace

from demo_data import get_demo_matches
from facit import make_coupon_snapshot, with_results
from counterfactual_system_lab import CounterfactualSystemSnapshot
from strategy_robustness import coupon_segment_profile, segment_matchups, strategy_robustness


def _coupon(cid, public=(.70,.20,.10), model=(.50,.25,.25), market=(.55,.25,.20), result='1', a_sel=('1',), b_sel=('1','X')):
    base=get_demo_matches()
    matches=[]
    for m in base:
        matches.append(replace(m, public=public, model=model, odds=tuple(1/x for x in market), market_available=True))
    a=CounterfactualSystemSnapshot('A','test',tuple((tuple(a_sel),)*13),1,0.1)
    b=CounterfactualSystemSnapshot('B','test',tuple((tuple(b_sel),)*13),8192,0.2)
    c=make_coupon_snapshot(cid,matches,[('1',)]*13,source='x',strategy='MAX 13',budget=128,rows=1,model_coverage=.1,counterfactual_systems=(a,b))
    return with_results(c,{i:result for i in range(1,14)})


def test_profile_uses_only_frozen_inputs_and_detects_favorite_dominated():
    c=_coupon('c')
    p=coupon_segment_profile(c)
    assert p.favorite_picture == 'FAVORITDOMINERAD'
    assert p.favorite_count_60 == 13


def test_open_coupon_segment():
    c=_coupon('c', public=(.40,.35,.25))
    assert coupon_segment_profile(c).favorite_picture == 'ÖPPEN'


def test_high_model_market_gap_segment():
    c=_coupon('c', model=(.80,.10,.10), market=(.40,.30,.30))
    assert coupon_segment_profile(c).model_market_gap == 'HÖG MODELL–MARKNAD GAP'


def test_19_shared_in_segment_is_not_reviewable():
    coupons=[_coupon(f'c{i}') for i in range(19)]
    matches=[m for m in segment_matchups(coupons) if m.dimension=='FAVORITBILD']
    assert matches and all(m.status == 'FÖR LITE GEMENSAM HISTORIK' for m in matches)


def test_20_shared_in_same_segment_is_reviewable():
    coupons=[_coupon(f'c{i}', result='X') for i in range(20)]
    matches=[m for m in segment_matchups(coupons) if m.dimension=='FAVORITBILD']
    assert matches and matches[0].status == 'GRANSKNINGSBAR'
    assert matches[0].matchup_result == 'B'


def test_different_segments_do_not_get_pooled_to_reach_threshold():
    coupons=[_coupon(f'f{i}') for i in range(10)] + [_coupon(f'o{i}', public=(.40,.35,.25)) for i in range(10)]
    fav=[m for m in segment_matchups(coupons) if m.dimension=='FAVORITBILD']
    assert len(fav) == 2
    assert all(m.shared_coupons == 10 and m.status != 'GRANSKNINGSBAR' for m in fav)


def test_same_cohort_across_dimensions_is_not_enough_for_robustness():
    coupons=[_coupon(f'c{i}', result='X') for i in range(20)]
    r=strategy_robustness(coupons)
    row=next(x for x in r['strategies'] if x['strategy']=='B')
    assert row['dimensions'] >= 2
    assert row['contrasting_dimensions'] == 0
    assert row['status'] == 'FÖR LITE KONTRASTERANDE HISTORIK'
    assert r['edge_claim_allowed'] is False
    assert r['roi_claim_allowed'] is False
    assert r['strategy_change_allowed'] is False


def test_two_environment_levels_in_same_dimension_make_robustness_reviewable():
    fav=[_coupon(f'f{i}', public=(.70,.20,.10), result='X') for i in range(20)]
    open_=[_coupon(f'o{i}', public=(.40,.35,.25), result='X') for i in range(20)]
    r=strategy_robustness(fav+open_)
    row=next(x for x in r['strategies'] if x['strategy']=='B')
    assert row['contrasting_dimensions'] >= 1
    assert row['status'] != 'FÖR LITE KONTRASTERANDE HISTORIK'


def test_results_never_change_coupon_segment_profile():
    c1=_coupon('a', result='1')
    c2=_coupon('b', result='X')
    p1=coupon_segment_profile(c1); p2=coupon_segment_profile(c2)
    assert (p1.favorite_picture,p1.crowding,p1.model_market_gap)==(p2.favorite_picture,p2.crowding,p2.model_market_gap)
