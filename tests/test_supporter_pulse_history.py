from pathlib import Path

import pytest

from advanced_context import ForumPost, analyze_supporter_pulse
from core import MatchInput
from supporter_pulse_history import (
    append_pulse_snapshots,
    attach_results,
    competition_pulse_rows,
    load_pulse_history,
    make_pulse_snapshot,
    signal_history_rows,
)


def _match():
    return MatchInput(1, "Home FC", "Away FC", (2.0, 3.4, 4.0), (0.50, 0.28, 0.22), (0.50, 0.28, 0.22), kickoff="2026-09-05T15:00:00Z", competition="Test League")


def _pulse(text="confident win strong good feeling"):
    posts=[ForumPost(text, text, 0, 5, 2, "Reddit r/test", author=f"u{i}") for i in range(12)]
    return analyze_supporter_pulse(posts)


def test_demo_pulse_cannot_enter_real_history():
    with pytest.raises(ValueError):
        make_pulse_snapshot(coupon_fingerprint="abc", match=_match(), team="Home FC", pulse=_pulse(), data_mode="Demo")


def test_snapshot_keeps_market_anchor_and_pulse_dimensions(tmp_path: Path):
    snap=make_pulse_snapshot(coupon_fingerprint="abc", match=_match(), team="Home FC", pulse=_pulse(), data_mode="Multi-source", captured_at="2026-09-05T10:00:00Z")
    assert snap.side == "home"
    assert snap.market_team_win_prob == pytest.approx(_match().market[0])
    assert snap.confidence > 0
    p=tmp_path/"pulse.json"
    append_pulse_snapshots(p,[snap,snap])
    rows=load_pulse_history(p)
    assert len(rows) == 1



def test_snapshot_requires_real_market_anchor():
    m=_match()
    m.market_available=False
    with pytest.raises(ValueError):
        make_pulse_snapshot(coupon_fingerprint="abc", match=m, team="Home FC", pulse=_pulse(), data_mode="Multi-source")

def test_results_attach_only_when_real_facit_exists(tmp_path: Path):
    snap=make_pulse_snapshot(coupon_fingerprint="abc", match=_match(), team="Away FC", pulse=_pulse(), data_mode="Multi-source", captured_at="2026-09-05T10:00:00Z")
    p=tmp_path/"pulse.json"; append_pulse_snapshots(p,[snap])
    assert attach_results(p,{("abc",1):"2"}) == 1
    assert load_pulse_history(p)[0]["result"] == "2"
    assert attach_results(p,{("abc",1):"?"}) == 0


def test_history_compares_signal_to_market_not_raw_win_rate():
    rows=[]
    for i in range(30):
        rows.append({
            "confidence":0.8,"optimism":0.5,"resignation":0.0,"worry":0.0,
            "side":"home","result":"1" if i < 24 else "2",
            "market_team_win_prob":0.80,"competition":"Test League","sample_quality":0.8,
        })
    table=signal_history_rows(rows,min_observations=30)
    confident=next(x for x in table if x["Signal"]=="Hög självsäkerhet")
    assert confident["Marknadsjusterad avvikelse"] == "+0.0 p.e."
    assert confident["Bedömning"] == "Ingen tydlig marginalnytta mot marknaden"


def test_competition_rows_require_outcomes():
    rows=[{"side":"home","result":"1","market_team_win_prob":0.6,"competition":"A","sample_quality":0.5,"confidence":0.5,"optimism":0.4,"resignation":0,"worry":0}]
    out=competition_pulse_rows(rows,min_observations=2)
    assert out[0]["Observationer"] == 1
    assert "För lite data" in out[0]["Underlag"]
