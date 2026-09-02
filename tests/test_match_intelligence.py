from datetime import datetime, timezone

from evidence import make_signal
from match_intelligence import build_match_card, resolve_claim
from source_consensus import Observation, DEFAULT_SOURCES


def test_market_only_card_is_low_readiness():
    c=build_match_card(match_number=1,home="A",away="B",base_market=(.5,.3,.2))
    assert c.readiness_score < 50
    assert c.final_model == c.base_market


def test_verified_signals_move_model_but_are_capped():
    sig=make_signal("team_strength","styrka",(2.0,0,-2.0),1.0,"x",is_verified=True,weight=1.0)
    c=build_match_card(match_number=1,home="A",away="B",base_market=(.5,.3,.2),signals=[sig],max_total_shift=.10)
    moved=.5*sum(abs(a-b) for a,b in zip(c.base_market,c.final_model))
    assert moved <= .1000001
    assert c.final_model[0] > c.base_market[0]


def test_unverified_signal_does_not_move_model():
    sig=make_signal("fan_sentiment","rykte",(3,0,-3),1,"forum",is_verified=False,weight=1)
    c=build_match_card(match_number=1,home="A",away="B",base_market=(.5,.3,.2),signals=[sig])
    assert c.final_model == c.base_market
    assert len(c.used_signals) == 0


def test_independent_sources_can_make_claim_usable():
    obs=[
        Observation("p1_status","OUT",DEFAULT_SOURCES["api_football"],confidence=.95),
        Observation("p1_status","OUT",DEFAULT_SOURCES["club_official"],confidence=1.0),
    ]
    claim=resolve_claim("p1_status","injury_suspension",obs)
    assert claim.consensus is not None
    assert claim.consensus.independent_groups == 2
    assert claim.usable


def test_conflicting_claim_reduces_readiness_and_is_flagged():
    obs=[
        Observation("p1_status","OUT",DEFAULT_SOURCES["api_football"],confidence=.9),
        Observation("p1_status","FIT",DEFAULT_SOURCES["club_official"],confidence=.9),
    ]
    claim=resolve_claim("p1_status","injury_suspension",obs)
    c=build_match_card(match_number=1,home="A",away="B",base_market=(.5,.3,.2),claims=[claim])
    assert "p1_status" in c.conflicts
