from core import MatchInput
from pool_value import system_pool_value, sign_pool_edges, top_coupon_cleaners

def m(n=1, public=(.6,.25,.15), model=(.5,.3,.2)):
    return MatchInput(n,"A","B",(2.0,3.5,4.0),public,model)

def test_pool_value_exact_single_match():
    r=system_pool_value([m()],[('X',)])
    assert abs(r.model_coverage-.3)<1e-9
    assert abs(r.public_survival_mass-.25)<1e-9
    assert abs(r.leverage-1.2)<1e-9

def test_guard_increases_public_survival_mass():
    a=system_pool_value([m()],[('X',)])
    b=system_pool_value([m()],[('1','X')])
    assert b.public_survival_mass>a.public_survival_mass
    assert b.model_coverage>a.model_coverage

def test_edges_reward_understrecking():
    e={x['sign']:x for x in sign_pool_edges(m())}
    assert e['2']['value_ratio']>e['1']['value_ratio']

def test_cleaners_exclude_public_favorite():
    r=top_coupon_cleaners([m()])
    assert all(x['sign']!='1' for x in r)

def test_tiny_longshot_is_not_cleaner():
    mm=m(public=(.85,.13,.02),model=(.82,.15,.03))
    assert all(x['sign']!='2' for x in top_coupon_cleaners([mm]))
