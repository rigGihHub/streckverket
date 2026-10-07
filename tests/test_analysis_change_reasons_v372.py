from types import SimpleNamespace
from analysis_change_report import make_analysis_snapshot, compare_analysis_snapshots


def m(n, odds=(2,3,4), public=(.5,.3,.2), model=(.52,.28,.2)):
    return SimpleNamespace(number=n, odds=odds, public=public, model=model)


def card(n, missing=()):
    return SimpleNamespace(match_number=n, missing=list(missing))


def test_changed_system_explains_observed_market_and_model_changes_without_claiming_cause():
    before = make_analysis_snapshot([m(1)], [("1","X")], "VÄNTA", [card(1)])
    after = make_analysis_snapshot([m(1, odds=(1.8,3.2,4.2), model=(.58,.24,.18))], [("1",)], "VÄNTA", [card(1)])
    r = compare_analysis_snapshots(before, after)
    assert r.system_changed
    assert len(r.reasons) == 1
    assert "marknadsoddsen ändrades" in r.reasons[0]
    assert "modellens sannolikheter ändrades" in r.reasons[0]
    assert "inte bevisad enskild orsak" in r.reasons[0]


def test_changed_system_mentions_public_streak_change():
    before = make_analysis_snapshot([m(1)], [("1","X")], "VÄNTA", [])
    after = make_analysis_snapshot([m(1, public=(.62,.22,.16))], [("1",)], "VÄNTA", [])
    r = compare_analysis_snapshots(before, after)
    assert "streckfördelningen ändrades" in r.reasons[0]
    assert "streckfördelningen ändrades i 1 matcher" in r.summary.lower()


def test_changed_system_can_explain_new_verified_lineup_support():
    before = make_analysis_snapshot([m(1)], [("1","X")], "VÄNTA", [card(1,("confirmed_lineup",))])
    after = make_analysis_snapshot([m(1, model=(.57,.25,.18))], [("1",)], "SYSTEMET KAN ANVÄNDAS", [card(1)])
    r = compare_analysis_snapshots(before, after)
    assert "nytt verifierat startelvsunderlag tillkom" in r.reasons[0]


def test_global_budget_reallocation_is_named_when_other_match_changed():
    before = make_analysis_snapshot([m(1),m(2)], [("1","X"),("1",)], "VÄNTA", [])
    after = make_analysis_snapshot([m(1),m(2, public=(.7,.2,.1))], [("1",),("1","X")], "VÄNTA", [])
    r = compare_analysis_snapshots(before, after)
    reason1 = next(x for x in r.reasons if x.startswith("Match 1:"))
    assert "systemet optimeras över hela kupongen" in reason1
    assert "budgeten kan ha flyttats" in reason1


def test_no_visible_input_change_is_admitted_not_invented():
    before = make_analysis_snapshot([m(1)], [("1","X")], "VÄNTA", [])
    after = make_analysis_snapshot([m(1)], [("1",)], "VÄNTA", [])
    r = compare_analysis_snapshots(before, after)
    assert "kan därför inte förklaras säkert" in r.reasons[0]
