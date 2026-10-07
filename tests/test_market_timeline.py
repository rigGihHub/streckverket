from datetime import datetime, timedelta, timezone

from core import MatchInput
from history_store import SQLiteHistoryStore
from market_timeline import (
    coupon_market_key, deduplicate_points, make_market_points,
    market_movement_rows, timeline_summary,
)


def _matches(home_odds=2.0):
    out=[]
    for i in range(13):
        m=MatchInput(i+1, f"H{i}", f"A{i}", (home_odds,3.4,4.2), (0.50,0.30,0.20), (0.55,0.25,0.20))
        m.market_available=True
        m.market_source="The Odds API"
        m.market_bookmaker_count=7
        m.market_last_update="2026-09-05T05:00:00+00:00"
        m.kickoff="2026-09-05T15:00:00+00:00"
        out.append(m)
    return out


def test_coupon_key_ignores_market_movement():
    a=_matches(2.0)
    b=_matches(1.8)
    assert coupon_market_key(a)==coupon_market_key(b)


def test_near_identical_points_are_deduplicated():
    a=make_market_points(_matches(), captured_at="2026-09-05T05:00:00+00:00")
    b=make_market_points(_matches(), captured_at="2026-09-05T05:03:00+00:00")
    assert deduplicate_points(a,b)==[]


def test_changed_market_is_kept_even_within_five_minutes():
    a=make_market_points(_matches(2.0), captured_at="2026-09-05T05:00:00+00:00")
    b=make_market_points(_matches(1.8), captured_at="2026-09-05T05:03:00+00:00")
    assert len(deduplicate_points(a,b))==13


def test_timeline_summary_counts_captures_and_points():
    a=make_market_points(_matches(2.0), captured_at="2026-09-05T05:00:00+00:00")
    b=make_market_points(_matches(1.8), captured_at="2026-09-05T06:00:00+00:00")
    summary=timeline_summary(a+b, coupon_key=a[0].coupon_key)
    assert summary["captures"]==2
    assert summary["verified_points"]==26
    assert summary["verified_matches_latest"]==13


def test_movement_rows_report_probability_point_change():
    a=make_market_points(_matches(2.0), captured_at="2026-09-05T05:00:00+00:00")
    b=make_market_points(_matches(1.8), captured_at="2026-09-05T06:00:00+00:00")
    rows=market_movement_rows(a+b, coupon_key=a[0].coupon_key)
    assert len(rows)==13
    assert rows[0]["Punkter"]==2
    assert rows[0]["Δ1 p.e."] > 0.0


def test_sqlite_market_timeline_roundtrip_and_dedup(tmp_path):
    store=SQLiteHistoryStore(str(tmp_path/"history.db"))
    a=make_market_points(_matches(), captured_at="2026-09-05T05:00:00+00:00")
    b=make_market_points(_matches(), captured_at="2026-09-05T05:03:00+00:00")
    assert store.save_market_points(a)==13
    assert store.save_market_points(b)==0
    loaded=store.load_market_points(a[0].coupon_key)
    assert len(loaded)==13
    assert loaded[0].market_source=="The Odds API"
