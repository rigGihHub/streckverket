from types import SimpleNamespace

import pandas as pd

import coupon_loader
from core import MatchInput
from demo_data import get_demo_matches
from data_sources import SourceStatus


def test_demo_loader_returns_complete_coupon():
    coupon = coupon_loader.load_demo_coupon()
    assert len(coupon) == 13
    assert [m.number for m in coupon] == list(range(1, 14))


def test_csv_loader_uses_source_validation():
    rows = []
    for i in range(1, 14):
        rows.append({
            "nr": i, "hemma": f"H{i}", "borta": f"B{i}",
            "streck1": 50, "streckx": 30, "streck2": 20,
        })
    coupon = coupon_loader.load_csv_coupon(pd.DataFrame(rows))
    assert len(coupon) == 13
    assert all(m.market_available is False for m in coupon)


def test_external_odds_merge_preserves_metadata_and_marks_market_available(monkeypatch):
    coupon = list(get_demo_matches())
    original = coupon[0]
    coupon[0] = MatchInput(
        original.number, original.home, original.away, original.odds,
        original.public, original.model,
        kickoff="2026-09-05T14:00:00Z", competition="Premier League",
        market_available=False,
    )
    status = SourceStatus("The Odds API", True, "2026-09-03T17:00:00Z", "Hög", "1 matcher med aggregerade 1X2-odds.")
    monkeypatch.setattr(coupon_loader, "fetch_the_odds_api", lambda *args, **kwargs: ([{
        "home": coupon[0].home, "away": coupon[0].away, "odds": (1.8, 3.7, 4.5)
    }], status))
    monkeypatch.setattr(coupon_loader, "match_odds_to_coupon", lambda matches, events: {1: events[0]})

    result = coupon_loader.merge_external_odds(coupon, "key", ["soccer_epl"], "eu")

    merged = result.coupon[0]
    assert result.matched_count == 1
    assert merged.odds == (1.8, 3.7, 4.5)
    assert merged.market_available is True
    assert merged.kickoff == "2026-09-05T14:00:00Z"
    assert merged.competition == "Premier League"


def test_failed_odds_fetch_leaves_coupon_unchanged(monkeypatch):
    coupon = list(get_demo_matches())
    status = SourceStatus("The Odds API", False, None, "Saknas", "Inga odds kunde hämtas.")
    monkeypatch.setattr(coupon_loader, "fetch_the_odds_api", lambda *args, **kwargs: ([], status))

    result = coupon_loader.merge_external_odds(coupon, "bad", ["soccer_epl"])

    assert result.matched_count == 0
    assert result.coupon == coupon
    assert result.status.ok is False
