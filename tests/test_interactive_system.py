import pytest
from demo_data import get_demo_matches
from interactive_system import (
    rows_for_selections, coverage_for_selections, evaluate_interactive_system,
    rank_next_upgrades, best_next_upgrade
)

def test_rows_are_product_of_sign_counts():
    s=[("1",)]*13
    s[0]=("1","X")
    s[1]=("1","X","2")
    assert rows_for_selections(s)==6

def test_single_sign_coverage_is_product():
    matches=get_demo_matches()
    sels=[("1",)]*13
    expected=1.0
    for m in matches:
        expected*=m.model[0]
    assert coverage_for_selections(matches,sels)==pytest.approx(expected)

def test_full_coverage_is_one():
    matches=get_demo_matches()
    sels=[("1","X","2")]*13
    assert coverage_for_selections(matches,sels)==pytest.approx(1.0)

def test_cost_follows_row_price():
    matches=get_demo_matches()
    sels=[("1",)]*13
    x=evaluate_interactive_system(matches,sels,row_price=2.0)
    assert x.rows==1 and x.cost==2.0

def test_upgrade_always_adds_one_sign_and_rows():
    matches=get_demo_matches()
    sels=[("1",)]*13
    u=best_next_upgrade(matches,sels)
    assert u is not None
    assert len(u.new_selection)==2
    assert u.rows_after==2
    assert u.extra_cost==1

def test_ranked_upgrades_are_descending_by_gain_per_kr():
    matches=get_demo_matches()
    sels=[("1",)]*13
    ups=rank_next_upgrades(matches,sels)
    vals=[x.gain_per_kr for x in ups]
    assert vals==sorted(vals,reverse=True)

def test_empty_match_selection_is_invalid():
    matches=get_demo_matches()
    sels=[("1",)]*13
    sels[3]=()
    with pytest.raises(ValueError):
        evaluate_interactive_system(matches,sels)
