import pytest
from demo_data import get_demo_matches
from budget_workshop import optimize_for_budget,budget_curve,nearby_budgets,best_value_step,compare_budget_points

def test_budget_optimizer_never_exceeds_budget():
    m=get_demo_matches()
    for b in [16,31,64,100,192,257]:
        r=optimize_for_budget(m,b)
        assert r["cost"] <= b

def test_more_budget_never_reduces_coverage_on_curve():
    pts=budget_curve(get_demo_matches(),[16,32,64,128,256])
    cov=[p.coverage for p in pts]
    assert cov == sorted(cov)

def test_nearby_budgets_contains_target_and_are_sorted_unique():
    x=nearby_budgets(192)
    assert 192 in x
    assert x==sorted(set(x))

def test_curve_delta_matches_difference():
    pts=budget_curve(get_demo_matches(),[64,128])
    assert pts[1].delta_cost == pytest.approx(pts[1].cost-pts[0].cost)
    assert pts[1].delta_coverage_pp == pytest.approx((pts[1].coverage-pts[0].coverage)*100)

def test_best_value_step_is_one_of_curve_points():
    pts=budget_curve(get_demo_matches(),[16,32,64,128,256])
    best=best_value_step(pts)
    assert best in pts

def test_compare_budget_points():
    pts=budget_curve(get_demo_matches(),[64,128])
    c=compare_budget_points(pts[0],pts[1])
    assert c["added_cost"] >= 0
    assert c["added_coverage_pp"] >= -1e-12

def test_locks_are_respected():
    m=get_demo_matches()
    r=optimize_for_budget(m,128,locks={1:("X",)})
    assert tuple(r["selections"][0]) == ("X",)
