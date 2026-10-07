from core import MatchInput
from guard_efficiency import best_guard_upgrade, guard_upgrade_candidates


def m(n, model, public=(.34,.33,.33)):
    return MatchInput(n, f"H{n}", f"A{n}", (2.0,3.2,4.0), public, model)


def test_upgrade_never_changes_existing_signs_and_adds_exactly_one():
    matches=[m(1,(.70,.20,.10)),m(2,(.45,.35,.20))]
    system={"rows":2,"coverage":.70*.80,"selections":[("1",),("1","X")],"row_price":1.0}
    rows=guard_upgrade_candidates(matches,system)
    assert rows
    for row in rows:
        assert set(row.from_selection).issubset(set(row.to_selection))
        assert len(row.to_selection)==len(row.from_selection)+1
        assert row.added_sign in row.to_selection and row.added_sign not in row.from_selection


def test_extra_rows_follow_system_multiplier():
    matches=[m(1,(.70,.20,.10)),m(2,(.45,.35,.20))]
    system={"rows":2,"coverage":.70*.80,"selections":[("1",),("1","X")],"row_price":1.0}
    rows=guard_upgrade_candidates(matches,system)
    from_spike=[r for r in rows if r.match_number==1]
    from_half=[r for r in rows if r.match_number==2]
    assert all(r.extra_rows==2 for r in from_spike)  # 1 -> 2 doubles total rows
    assert all(r.extra_rows==1 for r in from_half)   # 2 -> 3 adds 50%


def test_new_coverage_is_mathematically_consistent():
    matches=[m(1,(.70,.20,.10)),m(2,(.45,.35,.20))]
    system={"rows":2,"coverage":.70*.80,"selections":[("1",),("1","X")],"row_price":1.0}
    rows=guard_upgrade_candidates(matches,system)
    x=next(r for r in rows if r.match_number==1 and r.added_sign=="X")
    assert abs(x.new_coverage-(.90*.80)) < 1e-12
    assert abs(x.delta_coverage_pp-16.0) < 1e-12


def test_full_guard_has_no_upgrade_candidate():
    matches=[m(1,(.50,.30,.20))]
    system={"rows":3,"coverage":1.0,"selections":[("1","X","2")],"row_price":1.0}
    assert guard_upgrade_candidates(matches,system)==[]
    assert best_guard_upgrade(matches,system) is None


def test_rank_is_efficiency_not_biggest_absolute_gain():
    matches=[m(1,(.60,.25,.15)),m(2,(.40,.35,.25))]
    system={"rows":2,"coverage":.60*.75,"selections":[("1",),("1","X")],"row_price":1.0}
    rows=guard_upgrade_candidates(matches,system)
    # Match 2 costs only one extra row; adding 2 is highly efficient per extra row.
    assert rows[0].match_number==2
    assert rows[0].added_sign=="2"


def test_cost_uses_row_price_when_present():
    matches=[m(1,(.60,.25,.15)),m(2,(.40,.35,.25))]
    system={"rows":2,"coverage":.60*.75,"selections":[("1",),("1","X")],"row_price":2.5}
    top=best_guard_upgrade(matches,system)
    assert top is not None
    assert top.extra_cost == top.extra_rows*2.5


def test_public_share_is_descriptive_only_and_does_not_change_efficiency_rank():
    matches_a=[m(1,(.60,.25,.15),(.60,.20,.20)),m(2,(.40,.35,.25),(.34,.33,.33))]
    matches_b=[m(1,(.60,.25,.15),(.10,.80,.10)),m(2,(.40,.35,.25),(.90,.05,.05))]
    system={"rows":2,"coverage":.60*.75,"selections":[("1",),("1","X")],"row_price":1.0}
    rank_a=[(x.match_number,x.added_sign) for x in guard_upgrade_candidates(matches_a,system)]
    rank_b=[(x.match_number,x.added_sign) for x in guard_upgrade_candidates(matches_b,system)]
    assert rank_a==rank_b


def test_invalid_alignment_fails_closed():
    matches=[m(1,(.60,.25,.15))]
    assert guard_upgrade_candidates(matches,{"rows":1,"coverage":.6,"selections":[]})==[]
