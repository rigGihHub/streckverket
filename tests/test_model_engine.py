from model_engine import Absence, missing_value, parse_api_football_injuries, enriched_probabilities, build_match_signals
from performance import team_strength_signal, availability_signal


def test_absence_impact_uses_importance_and_replacement():
    a=Absence('A',1,'injured','',0.8,0.25,True)
    assert abs(a.impact-0.6)<1e-12


def test_unverified_absence_has_zero_impact():
    a=Absence('A',1,'rumour','',1.0,0.0,False)
    assert a.impact==0


def test_missing_value_subadditive():
    xs=[Absence('A',1,'','',0.8,0.5,True), Absence('B',1,'','',0.5,0.5,True)]
    v=missing_value(xs,1)
    assert 0 < v < 0.65


def test_parse_api_football_injuries():
    payload={'response':[{'player':{'name':'Player One','type':'Missing Fixture','reason':'Hamstring'},'team':{'id':7}}]}
    xs=parse_api_football_injuries(payload)
    assert len(xs)==1 and xs[0].team_id==7 and xs[0].verified


def test_strength_signal_moves_toward_stronger_home():
    sig=team_strength_signal(.75,.42,'test',20)
    p,_=enriched_probabilities((.45,.30,.25),[sig])
    assert p[0]>.45 and p[2]<.25


def test_absence_signal_moves_against_home_when_home_more_hurt():
    sig=availability_signal(.60,.10,'test',True)
    p,_=enriched_probabilities((.50,.28,.22),[sig])
    assert p[0]<.50 and p[2]>.22


def test_total_shift_is_capped():
    sigs=[team_strength_signal(1,0,'x',100), availability_signal(0,1,'x',True)]
    p,_=enriched_probabilities((.34,.33,.33),sigs,max_total_shift=.08)
    moved=.5*sum(abs(a-b) for a,b in zip(p,(.34,.33,.33)))
    assert moved <= .080000001


def test_build_match_signals():
    xs=build_match_signals(home_strength=.7,away_strength=.4,home_missing=.1,away_missing=.3)
    assert {x.category for x in xs}=={'team_strength','injury_suspension'}
