from core import MatchInput
from budget_reallocation import best_reallocation, reallocation_candidates


def m(n, model, public=(.34,.33,.33)):
    return MatchInput(n, f"H{n}", f"A{n}", (2.0,3.2,4.0), public, model)


def test_reallocation_keeps_exact_same_rows_and_cost():
    matches=[m(1,(.80,.10,.10)),m(2,(.45,.40,.15))]
    system={"rows":2,"selections":[("1","X"),("1",)],"row_price":2.0}
    rows=reallocation_candidates(matches,system)
    assert rows
    assert all(x.rows==2 and x.cost==4.0 for x in rows)


def test_reallocation_can_move_half_guard_between_matches():
    matches=[m(1,(.50,.30,.20)),m(2,(.45,.40,.15))]
    system={"rows":2,"selections":[("1","X"),("1",)]}
    rows=reallocation_candidates(matches,system)
    assert any(x.donor_match_number==1 and x.recipient_match_number==2 for x in rows)


def test_only_positive_coverage_moves_are_returned():
    matches=[m(1,(.50,.30,.20)),m(2,(.45,.40,.15))]
    system={"rows":2,"selections":[("1","X"),("1",)]}
    rows=reallocation_candidates(matches,system)
    assert rows
    assert all(x.new_coverage>x.base_coverage and x.delta_coverage_pp>0 for x in rows)


def test_best_reallocation_is_sorted_by_absolute_coverage_gain():
    matches=[m(1,(.50,.30,.20)),m(2,(.45,.40,.15)),m(3,(.80,.15,.05))]
    system={"rows":4,"selections":[("1","X"),("1",),("1","X")]}
    rows=reallocation_candidates(matches,system)
    assert rows
    top=best_reallocation(matches,system)
    assert top == rows[0]
    assert top.delta_coverage_pp == max(x.delta_coverage_pp for x in rows)


def test_locked_donor_is_never_modified():
    matches=[m(1,(.50,.30,.20)),m(2,(.45,.40,.15))]
    system={"rows":2,"selections":[("1","X"),("1",)]}
    assert reallocation_candidates(matches,system,locks={1:("1","X")}) == []


def test_locked_recipient_is_never_modified():
    matches=[m(1,(.50,.30,.20)),m(2,(.45,.40,.15))]
    system={"rows":2,"selections":[("1","X"),("1",)]}
    assert reallocation_candidates(matches,system,locks={2:("1",)}) == []


def test_full_to_half_and_half_to_full_can_trade_exact_rows():
    matches=[m(1,(.60,.30,.10)),m(2,(.35,.25,.40))]
    system={"rows":6,"selections":[("1","X","2"),("1","X")]}
    rows=reallocation_candidates(matches,system)
    assert any(len(x.donor_from)==3 and len(x.donor_to)==2 and len(x.recipient_from)==2 and len(x.recipient_to)==3 for x in rows)


def test_invalid_alignment_fails_closed():
    matches=[m(1,(.60,.25,.15))]
    assert reallocation_candidates(matches,{"rows":1,"selections":[]})==[]


def test_no_change_when_system_has_only_spikes():
    matches=[m(1,(.60,.25,.15)),m(2,(.55,.25,.20))]
    assert reallocation_candidates(matches,{"rows":1,"selections":[("1",),("1",)]})==[]


def test_public_distribution_does_not_change_reallocation_math():
    a=[m(1,(.50,.30,.20),(.8,.1,.1)),m(2,(.45,.40,.15),(.1,.8,.1))]
    b=[m(1,(.50,.30,.20),(.1,.1,.8)),m(2,(.45,.40,.15),(.8,.1,.1))]
    system={"rows":2,"selections":[("1","X"),("1",)]}
    ra=[(x.donor_match_number,x.recipient_match_number,x.removed_signs,x.added_signs,round(x.delta_coverage_pp,12)) for x in reallocation_candidates(a,system)]
    rb=[(x.donor_match_number,x.recipient_match_number,x.removed_signs,x.added_signs,round(x.delta_coverage_pp,12)) for x in reallocation_candidates(b,system)]
    assert ra==rb


def test_texttv_page_558_is_wired_without_altering_model_logic():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    text=(root/'texttv_view.py').read_text()
    ui=(root/'ui_decision_page.py').read_text()
    assert "texttv_budget_reallocation_html" in text
    assert "558, 'OMFÖRDELA'" in text
    assert '"558 OMFÖRDELA"' in ui
    assert "locks=locks" in ui
