import pandas as pd
from data_sources import aggregate_1x2_event, parse_coupon_csv, match_odds_to_coupon
from demo_data import get_demo_matches


def test_aggregate_1x2_event():
    event = {
        "id":"e1","home_team":"Arsenal","away_team":"Wolves","sport_title":"EPL",
        "bookmakers":[
            {"last_update":"2026-09-01T10:00:00Z","markets":[{"key":"h2h","outcomes":[
                {"name":"Arsenal","price":1.5},{"name":"Draw","price":4.2},{"name":"Wolves","price":6.5}
            ]}]},
            {"last_update":"2026-09-01T10:01:00Z","markets":[{"key":"h2h","outcomes":[
                {"name":"Arsenal","price":1.6},{"name":"Draw","price":4.0},{"name":"Wolves","price":6.0}
            ]}]}
        ]
    }
    x = aggregate_1x2_event(event)
    assert x["bookmaker_count"] == 2
    assert x["odds"] == (1.55,4.1,6.25)


def test_exact_coupon_odds_matching():
    coupon = get_demo_matches()
    events = [{"home":"Arsenal","away":"Wolves","odds":(1.5,4.0,7.0)}]
    matched = match_odds_to_coupon(coupon, events)
    assert 1 in matched
    assert len(matched) == 1


def test_parse_coupon_csv_13_rows():
    rows=[]
    for i in range(1,14):
        rows.append({"nr":i,"hemma":f"H{i}","borta":f"B{i}","streck1":50,"streckx":30,"streck2":20,"odds1":2.0,"oddsx":3.5,"odds2":4.0})
    matches=parse_coupon_csv(pd.DataFrame(rows))
    assert len(matches)==13
    assert abs(sum(matches[0].public)-1)<1e-12
