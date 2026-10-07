from types import SimpleNamespace
from analysis_change_report import make_analysis_snapshot, compare_analysis_snapshots


def m(n, odds):
    return SimpleNamespace(number=n, odds=odds)


def card(n, missing=()):
    return SimpleNamespace(match_number=n, missing=list(missing))


def test_reports_unchanged_system_and_changed_odds():
    before = make_analysis_snapshot([m(1,(2,3,4))], [("1",)], "VÄNTA", [card(1,("confirmed_lineup",))])
    after = make_analysis_snapshot([m(1,(1.8,3,4))], [("1",)], "VÄNTA", [card(1,("confirmed_lineup",))])
    r = compare_analysis_snapshots(before, after)
    assert r.headline == "SYSTEMET ÄR OFÖRÄNDRAT"
    assert "odds ändrades i 1 matcher" in r.summary.lower()
    assert not r.system_changed


def test_reports_system_transition_plainly():
    before = make_analysis_snapshot([m(1,(2,3,4))], [("1","X")], "VÄNTA", [])
    after = make_analysis_snapshot([m(1,(2,3,4))], [("1",)], "SYSTEMET KAN ANVÄNDAS", [])
    r = compare_analysis_snapshots(before, after)
    assert r.system_changed
    assert r.changed_matches == (1,)
    assert "Match 1: 1/X → spik 1" in r.details
    assert "status ändrades" in r.summary.lower()


def test_reports_new_lineup_evidence_without_claiming_lineup_itself():
    before = make_analysis_snapshot([m(1,(2,3,4))], [("1",)], "VÄNTA", [card(1,("confirmed_lineup",))])
    after = make_analysis_snapshot([m(1,(2,3,4))], [("1",)], "VÄNTA", [card(1,())])
    r = compare_analysis_snapshots(before, after)
    assert "startelvsunderlaget förbättrades" in r.summary.lower()
    assert any("Nytt startelvsunderlag" in d for d in r.details)
