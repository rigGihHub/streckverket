from types import SimpleNamespace

from beginner_ux import (
    sign_meaning, selection_name, selection_explanation,
    coupon_readiness, edge_explanation, glossary,
)


def card(score, missing=(), conflicts=()):
    return SimpleNamespace(readiness_score=score, missing=missing, conflicts=conflicts)


def test_sign_meanings_are_plain_swedish():
    assert sign_meaning("1", "Arsenal", "Chelsea") == "Arsenal vinner"
    assert sign_meaning("X", "Arsenal", "Chelsea") == "matchen slutar oavgjort"
    assert sign_meaning("2", "Arsenal", "Chelsea") == "Chelsea vinner"


def test_selection_names_and_explanations():
    assert selection_name(("1",)) == "Spik"
    assert selection_name(("1", "X")) == "Halvgardering"
    assert selection_name(("1", "X", "2")) == "Helgardering"
    assert "spik" in selection_explanation(("1",), "A", "B").lower()
    assert "halvgardering" in selection_explanation(("1", "X"), "A", "B").lower()
    assert "helgardering" in selection_explanation(("1", "X", "2"), "A", "B").lower()


def test_demo_is_never_play_ready():
    r = coupon_readiness([card(90) for _ in range(13)], [("1",)] * 13, demo=True)
    assert r.score == 0
    assert "DEMO" in r.status


def test_low_readiness_says_wait():
    cards = [card(30, ("confirmed_lineup",)) for _ in range(13)]
    r = coupon_readiness(cards, [("1",)] * 13)
    assert r.status == "VÄNTA"
    assert any("startelvor" in b for b in r.blockers)


def test_high_readiness_is_ready():
    cards = [card(84) for _ in range(13)]
    r = coupon_readiness(cards, [("1",)] * 13)
    assert r.status == "SPELKlar".upper()
    assert r.ready_matches == 13


def test_spikes_weight_readiness_more_than_full_guards():
    cards = [card(20), card(90)]
    spike_first = coupon_readiness(cards, [("1",), ("1", "X", "2")])
    full_first = coupon_readiness(cards, [("1", "X", "2"), ("1",)])
    assert spike_first.score < full_first.score


def test_edge_explanation_contains_percentages():
    text = edge_explanation(0.60, 0.45, "1")
    assert "60" in text and "45" in text


def test_glossary_has_core_terms():
    g = glossary()
    assert "Spik" in g and "Streck" in g and "13-rättstäckning" in g
