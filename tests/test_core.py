import math
from core import market_probabilities, normalize, optimize_system
from demo_data import get_demo_matches

def test_market_probs_sum_to_one():
    p = market_probabilities((2.0, 3.5, 4.0))
    assert abs(sum(p)-1) < 1e-12

def test_model_probs_sum_to_one():
    for m in get_demo_matches():
        assert abs(sum(m.model)-1) < 1e-12
        assert abs(sum(m.public)-1) < 1e-12

def test_system_budget_respected():
    matches = get_demo_matches()
    for budget in [16,32,64,128,256]:
        s = optimize_system(matches,budget,"MAX 13")
        assert s["rows"] <= budget
        assert s["rows"] >= 1
        assert 0 < s["coverage"] <= 1

def test_lock_respected():
    matches = get_demo_matches()
    s = optimize_system(matches,64,"MAX 13",{1:("X","2")})
    assert s["selections"][0] == ("X","2")

def test_max13_not_worse_than_random():
    matches = get_demo_matches()
    s = optimize_system(matches,128,"MAX 13")
    assert s["coverage"] > s["random_coverage"]


def test_value_strategy_runs():
    matches = get_demo_matches()
    s = optimize_system(matches,128,"VÄRDE")
    assert s["rows"] <= 128
    assert len(s["selections"]) == 13
