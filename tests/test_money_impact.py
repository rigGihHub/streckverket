import pytest

from demo_data import get_demo_matches
from money_impact import spending_options, best_spending_option, plain_change, SelectionChange


def test_spending_options_are_sorted_and_do_not_exceed_requested_budget():
    matches = get_demo_matches()
    opts = spending_options(matches, 100, [50, 10, 20])
    assert [o.requested_extra for o in opts] == [10, 20, 50]
    for o in opts:
        assert o.cost_after <= 100 + o.requested_extra
        assert o.cost_after >= o.cost_before


def test_coverage_never_gets_worse_with_more_budget():
    opts = spending_options(get_demo_matches(), 64, [10, 20, 50, 100])
    assert all(o.coverage_after + 1e-12 >= o.coverage_before for o in opts)


def test_actual_extra_and_gain_are_consistent():
    o = spending_options(get_demo_matches(), 64, [64])[0]
    assert o.actual_extra_cost == pytest.approx(o.cost_after - o.cost_before)
    assert o.coverage_gain_pp == pytest.approx((o.coverage_after - o.coverage_before) * 100)
    if o.actual_extra_cost > 0:
        assert o.gain_per_kr == pytest.approx(o.coverage_gain_pp / o.actual_extra_cost)


def test_changes_match_before_and_after_systems():
    opts = spending_options(get_demo_matches(), 32, [128])
    o = opts[0]
    assert all(c.before != c.after for c in o.changes)


def test_best_option_is_highest_gain_per_kr_among_useful():
    opts = spending_options(get_demo_matches(), 32, [16, 32, 64, 128])
    best = best_spending_option(opts)
    useful = [o for o in opts if o.useful]
    if useful:
        assert best is not None
        assert best.gain_per_kr == max(o.gain_per_kr for o in useful)


def test_locks_remain_respected():
    opts = spending_options(get_demo_matches(), 64, [64], locks={1: ("X",)})
    for c in opts[0].changes:
        if c.match_number == 1:
            assert c.after == ("X",)


def test_plain_change_for_added_sign():
    c = SelectionChange(8, "Hem", "Bort", ("1",), ("1", "X"))
    assert "lägg till X" in plain_change(c)
    assert "1 → 1X" in plain_change(c)
