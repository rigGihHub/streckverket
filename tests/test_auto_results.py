from dataclasses import dataclass
from auto_results import outcome_from_goals, resolve_api_football_payload, fetch_coupon_results

@dataclass
class M:
    match_number:int
    home:str
    away:str
    kickoff:str|None=None

def payload(status="FT"):
    return {"response":[
        {"fixture":{"id":99,"status":{"short":status}},"teams":{"home":{"name":"Manchester United"},"away":{"name":"Arsenal"}},"goals":{"home":2,"away":1}},
        {"fixture":{"id":100,"status":{"short":"FT"}},"teams":{"home":{"name":"Chelsea"},"away":{"name":"Liverpool"}},"goals":{"home":0,"away":0}},
    ]}

def test_outcome_from_goals():
    assert outcome_from_goals(2,1)=="1"
    assert outcome_from_goals(1,1)=="X"
    assert outcome_from_goals(0,2)=="2"

def test_high_confidence_finished_fixture_is_resolved():
    r=resolve_api_football_payload([M(1,"Man Utd","Arsenal")],payload())
    assert r[1].result=="1" and r[1].status=="klar" and r[1].provider_fixture_id==99

def test_unfinished_fixture_is_not_registered():
    r=resolve_api_football_payload([M(1,"Man Utd","Arsenal")],payload("NS"))
    assert r[1].result is None and r[1].status=="ej_klar"

def test_uncertain_match_is_never_guessed():
    r=resolve_api_football_payload([M(1,"Completely Different","Unknown")],payload())
    assert r[1].result is None

def test_coupon_fetch_groups_by_saved_kickoff_date():
    class C: pass
    c=C(); c.matches=(M(1,"Man Utd","Arsenal","2026-09-05T15:00:00Z"),)
    calls=[]
    def fake(key,date):
        calls.append(date); return payload()
    results,details=fetch_coupon_results(c,"k",fetcher=fake)
    assert results=={1:"1"}; assert calls==["2026-09-05"]; assert details[0].status=="klar"

def test_old_snapshot_without_kickoff_stays_manual():
    class C: pass
    c=C(); c.matches=(M(1,"Man Utd","Arsenal",None),)
    results,details=fetch_coupon_results(c,"k",fetcher=lambda *_: payload())
    assert results=={} and details[0].status=="saknar_datum"
