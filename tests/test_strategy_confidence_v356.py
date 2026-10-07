from dataclasses import replace

from demo_data import get_demo_matches
from facit import make_coupon_snapshot, with_results
from counterfactual_system_lab import CounterfactualSystemSnapshot
from strategy_confidence import exact_two_sided_sign_p, holm_adjust, strategy_confidence


def _coupon(cid, result='X', public=(.70,.20,.10)):
    base=get_demo_matches(); matches=[]
    for m in base:
        matches.append(replace(m, public=public, model=(.50,.25,.25), odds=(1/.55,1/.25,1/.20), market_available=True))
    a=CounterfactualSystemSnapshot('A','test',tuple((('1',),)*13),1,0.1)
    b=CounterfactualSystemSnapshot('B','test',tuple((('1','X'),)*13),8192,0.2)
    c=make_coupon_snapshot(cid,matches,[('1',)]*13,source='x',strategy='MAX 13',budget=128,rows=1,model_coverage=.1,counterfactual_systems=(a,b))
    return with_results(c,{i:result for i in range(1,14)})


def test_exact_sign_test_balanced_is_one():
    assert exact_two_sided_sign_p(10,10) == 1.0


def test_exact_sign_test_extreme_is_small():
    assert exact_two_sided_sign_p(20,0) < 0.001


def test_no_decisive_coupon_has_no_p_value():
    assert exact_two_sided_sign_p(0,0) is None


def test_holm_never_makes_p_smaller_and_preserves_order():
    raw=[0.01,0.03,0.20]
    adj=holm_adjust(raw)
    assert all(a >= p for a,p in zip(adj,raw))
    assert len(adj)==3


def test_holm_blocks_a_marginal_raw_finding_when_many_tests_exist():
    adj=holm_adjust([0.01,0.02,0.03,0.04,0.20])
    assert adj[0] >= 0.05


def test_29_shared_coupons_do_not_enter_confidence_family():
    r=strategy_confidence([_coupon(f'c{i}') for i in range(29)])
    assert r['family_size'] == 0
    assert r['status'] == 'FÖR LITE HISTORIK FÖR KONFIDENSTEST'


def test_30_decisive_shared_coupons_can_survive_holm():
    r=strategy_confidence([_coupon(f'c{i}', result='X') for i in range(30)])
    assert r['family_size'] >= 1
    assert r['significant_after_holm'] >= 1
    assert any(t.direction == 'B' and t.status == 'SIGNAL EFTER MULTIPEL-KORRIGERING' for t in r['tests'])
    assert r['edge_claim_allowed'] is False
    assert r['roi_claim_allowed'] is False
    assert r['automatic_strategy_change_allowed'] is False
    assert r['formal_proof'] is False


def test_draws_do_not_create_false_direction():
    # Both systems contain 1; all coupons draw in strategy result only if result 1.
    r=strategy_confidence([_coupon(f'c{i}', result='1') for i in range(30)])
    assert r['tests']
    assert all(t.decisive_coupons == 0 for t in r['tests'])
    assert all(t.status == 'INGEN RIKTNINGSINFORMATION' for t in r['tests'])


def test_contrasting_segments_are_separate_tests_in_same_family():
    fav=[_coupon(f'f{i}', result='X', public=(.70,.20,.10)) for i in range(30)]
    open_=[_coupon(f'o{i}', result='X', public=(.40,.35,.25)) for i in range(30)]
    r=strategy_confidence(fav+open_)
    favorite_tests=[t for t in r['tests'] if t.dimension=='FAVORITBILD']
    assert len(favorite_tests)==2
    assert r['family_size'] >= 2
