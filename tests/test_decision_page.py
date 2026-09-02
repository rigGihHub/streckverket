from demo_data import get_demo_matches
from decision_page import build_match_decisions, summarize_decisions

def test_all_matches_get_decision():
    m=get_demo_matches()
    d=build_match_decisions(m)
    assert len(d)==13
    assert [x.number for x in d]==list(range(1,14))

def test_decision_recommended_sign_is_valid():
    for d in build_match_decisions(get_demo_matches()):
        assert d.recommended in {"1","X","2"}

def test_summary_contains_system_and_sections():
    s=summarize_decisions(get_demo_matches(),192)
    assert "system" in s
    assert {"spikes","traps","upsets","must_guard"} <= set(s)

def test_summary_system_respects_budget():
    s=summarize_decisions(get_demo_matches(),192)
    assert s["system"]["cost"] <= 192

def test_spikes_are_sorted_by_confidence_then_edge():
    s=summarize_decisions(get_demo_matches(),192)
    vals=[(x.confidence,x.edge) for x in s["spikes"]]
    assert vals==sorted(vals,reverse=True)
