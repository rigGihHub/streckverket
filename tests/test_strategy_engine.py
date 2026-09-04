from demo_data import get_demo_matches
from strategy_engine import coupon_type, predictability_ranking, value_ranking, best_cross, coupon_cleaners, three_systems, countercheck

def test_coupon_type_known():
    label,_=coupon_type(get_demo_matches())
    assert label in {"FAVORITBETONAD","NORMAL","SKRÄLLVÄNLIG","MYCKET SVÅR"}

def test_rankings_cover_all_matches():
    ms=get_demo_matches()
    assert len(predictability_ranking(ms))==13
    assert len(value_ranking(ms))==13

def test_cleaners_are_low_public_and_positive_edge():
    for c in coupon_cleaners(get_demo_matches()):
        assert c.public_share < .35
        assert c.model_probability > c.public_share

def test_best_cross_is_x_or_none():
    c=best_cross(get_demo_matches())
    assert c is None or c.sign=="X"

def test_three_systems_within_budget():
    systems=three_systems(get_demo_matches(),192)
    assert set(systems)=={"FÖRSIKTIGT","STRECKVERKETS VAL","HÖGRE POTENTIAL"}
    assert all(s["cost"] <= 192 for s in systems.values())

def test_countercheck_returns_text():
    s=three_systems(get_demo_matches(),192)["STRECKVERKETS VAL"]
    assert countercheck(get_demo_matches(),s)
