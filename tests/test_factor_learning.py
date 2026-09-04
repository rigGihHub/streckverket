from dataclasses import replace

from core import MatchInput
from evidence import make_signal
from factor_learning import (
    FactorSnapshot, factor_lesson, factor_map_from_cards, factor_observations,
    factor_scorecard, proposed_weight_actions, snapshots_from_card,
)
from facit import FacitCoupon, FacitMatch, dumps_facit, loads_facit, make_coupon_snapshot, with_results
from match_intelligence import build_match_card


def _card():
    sig1 = make_signal("home_away_form", "Hemmaform", (0.30, 0.0, -0.30), 0.9, "formkälla", is_verified=True)
    sig2 = make_signal("injury_suspension", "Frånvaro", (-0.20, 0.02, 0.20), 0.8, "skadekälla", is_verified=True)
    return build_match_card(match_number=1, home="A", away="B", base_market=(0.50,0.28,0.22), signals=[sig1,sig2], max_total_shift=0.14)


def test_snapshots_store_counterfactual_and_real_delta():
    card = _card()
    rows = snapshots_from_card(card)
    assert len(rows) == 2
    assert all(r.verified for r in rows)
    assert all(abs(sum(r.delta)) < 1e-9 for r in rows)
    assert any(sum(abs(x) for x in r.delta) > 0 for r in rows)


def test_factor_map_uses_match_number():
    card = _card()
    fmap = factor_map_from_cards([card])
    assert 1 in fmap and len(fmap[1]) == 2


def test_facit_roundtrip_preserves_factors():
    matches=[]
    sels=[]
    card=_card()
    for n in range(1,14):
        matches.append(MatchInput(n, f"H{n}", f"A{n}", (2.0,3.5,4.0), (0.5,0.3,0.2), (0.5,0.28,0.22)))
        sels.append(("1",))
    fmap={1:snapshots_from_card(card)}
    c=make_coupon_snapshot("c1",matches,sels,source="Multi-source",strategy="MAX 13",budget=128,rows=128,model_coverage=.1,factor_snapshots=fmap)
    loaded=loads_facit(dumps_facit([c]))[0]
    assert len(loaded.matches[0].factors)==2
    assert loaded.matches[0].factors[0].category in {"home_away_form","injury_suspension"}


def test_old_facit_without_factors_is_backward_compatible():
    text='''[{"coupon_id":"x","captured_at":"2026-01-01","source":"Svenska Spel","strategy":"MAX 13","budget":1,"rows":1,"model_coverage":0.1,"matches":[{"match_number":1,"home":"A","away":"B","model":[0.5,0.3,0.2],"market":[0.5,0.3,0.2],"public":[0.5,0.3,0.2],"selected":["1"],"result":"1"}]}]'''
    loaded=loads_facit(text)
    assert loaded[0].matches[0].factors == ()


def test_with_results_preserves_factor_dataclasses():
    f=FactorSnapshot("team_strength","Lagstyrka","src",True,.5,(.4,.3,.3),(.1,0,-.1))
    m=FacitMatch(1,"A","B",(.5,.3,.2),(.4,.3,.3),(.5,.3,.2),("1",),None,(f,))
    c=FacitCoupon("x","t","s","MAX",1,1,.1,(m,))
    updated=with_results(c,{1:"1"})
    assert updated.matches[0].result=="1"
    assert isinstance(updated.matches[0].factors[0], FactorSnapshot)


def _coupon_with_factor(result="1", helpful=True):
    final=(.65,.20,.15) if helpful else (.35,.35,.30)
    without=(.50,.30,.20)
    delta=tuple(a-b for a,b in zip(final,without))
    f=FactorSnapshot("team_strength","Lagstyrka","src",True,.5,without,delta)
    m=FacitMatch(1,"A","B",final,without,(.5,.3,.2),("1",),result,(f,))
    return FacitCoupon("x","t","s","MAX",1,1,.1,(m,))


def test_factor_observation_gain_positive_when_factor_improves_result_probability():
    rows=factor_observations([_coupon_with_factor(helpful=True)])
    assert rows[0]["brier_gain"] > 0
    assert rows[0]["helped"] is True


def test_scorecard_waits_for_min_sample_and_then_flags_pattern():
    few=factor_scorecard([_coupon_with_factor(helpful=True) for _ in range(5)], min_sample=30)
    assert few[0]["verdict"] == "För lite data"
    many=factor_scorecard([_coupon_with_factor(helpful=True) for _ in range(35)], min_sample=30)
    assert many[0]["verdict"] == "Ser lovande ut"


def test_weight_actions_are_review_only_and_require_large_sample():
    score=factor_scorecard([_coupon_with_factor(helpful=True) for _ in range(120)], min_sample=30)
    actions=proposed_weight_actions(score,min_sample=100)
    assert actions
    assert "Överväg" in actions[0]["action"] or "Behåll" in actions[0]["action"]
    assert "autom" not in actions[0]["action"].lower()
    assert "ändra" not in factor_lesson(score).lower() or "automatiskt" in factor_lesson(score).lower()
