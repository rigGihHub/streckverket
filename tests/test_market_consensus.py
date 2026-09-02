from market_consensus import BookmakerQuote, robust_market_consensus, quotes_from_odds_api_event


def test_consensus_rejects_extreme_outlier_when_enough_quotes():
    qs=[
        BookmakerQuote("a",(2.0,3.5,4.0)), BookmakerQuote("b",(2.05,3.45,3.95)),
        BookmakerQuote("c",(1.98,3.55,4.1)), BookmakerQuote("bad",(8.0,2.0,1.5)),
    ]
    c=robust_market_consensus(qs)
    assert abs(sum(c.probabilities)-1)<1e-9
    assert c.bookmaker_count >= 3
    assert "bad" in c.outliers


def test_parse_odds_api_quotes():
    event={"home_team":"A","away_team":"B","bookmakers":[{"title":"BM","markets":[{"key":"h2h","outcomes":[{"name":"A","price":2.0},{"name":"Draw","price":3.2},{"name":"B","price":4.0}]}]}]}
    qs=quotes_from_odds_api_event(event)
    assert len(qs)==1 and qs[0].odds[1]==3.2
