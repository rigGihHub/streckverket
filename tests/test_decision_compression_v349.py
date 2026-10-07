from types import SimpleNamespace

from decision_compression import build_compressed_decision
from texttv_view import texttv_decision_html


def m(n, model, public):
    return SimpleNamespace(number=n, home=f"Hem {n}", away=f"Borta {n}", model=model, public=public)


def readiness(status="SPELKLAR", score=82):
    return SimpleNamespace(status=status, score=score)


def test_quick_view_uses_actual_system_spike_not_summary_only():
    matches = [m(1, (.70,.20,.10), (.60,.25,.15)), m(2, (.55,.25,.20), (.40,.30,.30))]
    summary = {
        "system": {"rows":2,"cost":2,"selections":[("1","X"),("1",)]},
        "spikes": [SimpleNamespace(number=1)], "must_guard": [], "traps": [], "upsets": [],
    }
    q = build_compressed_decision(matches, summary, readiness())
    spike = next(a for a in q.actions if a.kind == "SPIK")
    assert spike.match_number == 2


def test_guard_action_must_already_be_guarded_in_system():
    matches = [m(1, (.50,.30,.20), (.50,.30,.20)), m(2, (.45,.35,.20), (.45,.35,.20))]
    must = [SimpleNamespace(number=1), SimpleNamespace(number=2)]
    summary = {
        "system": {"rows":2,"cost":2,"selections":[("1",),("1","X")]},
        "spikes": [], "must_guard": must, "traps": [], "upsets": [],
    }
    q = build_compressed_decision(matches, summary, readiness())
    guard = next(a for a in q.actions if a.kind == "GARDERA")
    assert guard.match_number == 2 and "1X" in guard.title


def test_upset_is_not_surfaced_if_sign_not_in_system():
    matches = [m(1, (.30,.45,.25), (.17,.66,.17))]
    upset = SimpleNamespace(number=1, recommended="1")
    summary = {
        "system": {"rows":1,"cost":1,"selections":[("X",)]},
        "spikes": [], "must_guard": [], "traps": [], "upsets": [upset],
    }
    q = build_compressed_decision(matches, summary, readiness())
    assert not any(a.kind == "SKRÄLL" for a in q.actions)


def test_texttv_page_100_is_action_first_and_disclaims_new_advice():
    matches = [m(1, (.70,.20,.10), (.55,.25,.20))]
    summary = {"system":{"rows":1,"cost":1,"selections":[("1",)]},"spikes":[],"must_guard":[],"traps":[],"upsets":[]}
    html = texttv_decision_html(build_compressed_decision(matches, summary, readiness("VÄNTA", 35)))
    assert "100 STRECKVERKET" in html
    assert "1 RADER · 1 KR" in html
    assert "VÄNTA · 35/100" in html
    assert "INGA NYA SPELRÅD" in html


def test_ui_defaults_to_compressed_mode():
    source = open("ui_decision_page.py", encoding="utf-8").read()
    assert '"Fördjupad analys", value=False' in source
    assert 'if not _show_decision_depth:' in source
    assert 'key="decision_quick_to_coupon"' in source


def test_349_registry_marks_change_as_non_predictive():
    from model_change_registry import get_model_change
    change = get_model_change("3.49.0")
    assert change is not None
    assert change.predictive_change is False
    assert "decision-compression" in change.components
