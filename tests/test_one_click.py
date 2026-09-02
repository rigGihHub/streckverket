from core import MatchInput
from one_click import name_similarity, match_api_football_fixture, parse_coupon_date, OneClickConfig, run_one_click
from demo_data import get_demo_matches


def test_name_similarity_aliases():
    assert name_similarity("Man Utd","Manchester United FC") > .9
    assert name_similarity("Wolves","Wolverhampton Wanderers") > .9


def test_fixture_matching_requires_both_teams():
    m=MatchInput(1,"Manchester United","Arsenal",(2.2,3.4,3.1),(.4,.3,.3),(.4,.3,.3),kickoff="2026-09-05T14:00:00Z")
    payload={"response":[
        {"fixture":{"id":10,"date":"2026-09-05T14:00:00Z"},"teams":{"home":{"id":1,"name":"Manchester United"},"away":{"id":2,"name":"Arsenal"}}},
        {"fixture":{"id":11,"date":"2026-09-05T15:00:00Z"},"teams":{"home":{"id":3,"name":"Manchester City"},"away":{"id":4,"name":"Arsenal"}}},
    ]}
    fm=match_api_football_fixture(m,payload)
    assert fm.fixture_id == 10
    assert fm.confidence == "Hög"


def test_fixture_no_false_high_on_one_team():
    m=MatchInput(1,"Leeds","Coventry",(2.2,3.4,3.1),(.4,.3,.3),(.4,.3,.3))
    payload={"response":[{"fixture":{"id":10},"teams":{"home":{"id":1,"name":"Leeds United"},"away":{"id":2,"name":"Liverpool"}}}]}
    fm=match_api_football_fixture(m,payload)
    assert fm.confidence != "Hög"


def test_parse_coupon_date():
    assert parse_coupon_date("2026-09-05T14:00:00Z") == "2026-09-05"
    assert parse_coupon_date(None) is None


def test_one_click_can_run_without_optional_keys(monkeypatch):
    demo=get_demo_matches()
    out=run_one_click(OneClickConfig(),coupon=demo,fetch_coupon=False)
    assert len(out.coupon)==13
    assert len(out.cards)==13
    assert [s.name for s in out.stages][:4] == ["Kupong","The Odds API","football-data.org","API-Football"]
