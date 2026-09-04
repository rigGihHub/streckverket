from core import MatchInput
from data_sources import parse_svenskaspel_api_payload
import pandas as pd
from data_sources import parse_coupon_csv


def test_svenska_spel_payload_without_odds_is_marked_missing():
    events=[]
    for i in range(13):
        events.append({
            "eventDescription": f"Home{i} - Away{i}",
            "distribution": [40,30,30],
        })
    rows=parse_svenskaspel_api_payload({"drawEvents":events})
    assert len(rows)==13
    assert all(not x.market_available for x in rows)


def test_csv_without_odds_is_marked_missing():
    df=pd.DataFrame([{
        "nr":i,"hemma":f"H{i}","borta":f"A{i}","streck1":40,"streckx":30,"streck2":30
    } for i in range(1,14)])
    rows=parse_coupon_csv(df)
    assert all(not x.market_available for x in rows)


def test_market_available_defaults_true_for_real_inputs():
    m=MatchInput(1,"H","A",(2.0,3.2,4.0),(0.5,0.3,0.2),(0.5,0.3,0.2))
    assert m.market_available is True
