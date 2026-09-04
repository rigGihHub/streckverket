from types import SimpleNamespace

import pytest

from core import MatchInput
from evidence import make_signal
from data_quality_history import (
    append_quality_snapshot, build_quality_snapshot, competition_history_rows,
    load_quality_history, source_history_rows, competition_source_history_rows,
)


def match(n, comp="Premier League", market=True):
    return MatchInput(n, f"H{n}", f"A{n}", (2.0,3.5,4.0), (.5,.3,.2), (.5,.3,.2), competition=comp, market_available=market)


def card(n, missing=(), source="football-data.org"):
    sig = make_signal("home_away_form", "Form", (.1,0,-.1), .8, source, is_verified=True)
    return SimpleNamespace(readiness_score=60, missing=list(missing), used_signals=[sig])


def stage(name="football-data.org", ok=True, matched=20, attempted=26):
    return SimpleNamespace(name=name, ok=ok, matched=matched, attempted=attempted, message="ok")


def test_demo_snapshot_is_rejected():
    with pytest.raises(ValueError):
        build_quality_snapshot(coupon_fingerprint="x", matches=[match(1)], cards=[card(1)], stages=[], data_mode="Demo")


def test_snapshot_preserves_competition_and_source_signal_usage():
    snap = build_quality_snapshot(coupon_fingerprint="x", matches=[match(1), match(2)], cards=[card(1), card(2, missing=("confirmed_lineup",))], stages=[stage()], data_mode="Multi-source")
    comp = snap["competitions"][0]
    assert comp["competition"] == "Premier League"
    assert comp["verified_signal_sources"]["football-data.org"] == 2
    assert snap["sources"][0]["coverage_pct"] == 77


def test_append_and_load_quality_history(tmp_path):
    p = tmp_path / "quality.json"
    snap = build_quality_snapshot(coupon_fingerprint="x", matches=[match(1)], cards=[card(1)], stages=[stage()], data_mode="Multi-source")
    append_quality_snapshot(p, snap)
    assert load_quality_history(p)[0]["coupon_fingerprint"] == "x"


def test_source_history_refuses_strong_claim_before_three_snapshots():
    snap = build_quality_snapshot(coupon_fingerprint="x", matches=[match(1)], cards=[card(1)], stages=[stage(matched=26, attempted=26)], data_mode="Multi-source")
    row = source_history_rows([snap])[0]
    assert "För lite data" in row["Bedömning"]


def test_source_history_can_label_after_three_snapshots():
    snaps = [build_quality_snapshot(coupon_fingerprint=str(i), matches=[match(1)], cards=[card(1)], stages=[stage(matched=26, attempted=26)], data_mode="Multi-source") for i in range(3)]
    row = source_history_rows(snaps)[0]
    assert row["Bedömning"] == "Stark historisk täckning"


def test_competition_trend_requires_minimum_match_count():
    snaps = [build_quality_snapshot(coupon_fingerprint=str(i), matches=[match(1)], cards=[card(1)], stages=[stage()], data_mode="Multi-source") for i in range(3)]
    row = competition_history_rows(snaps)[0]
    assert "För lite data" in row["Underlag"]


def test_completely_missing_layer_is_kept_as_zero_in_competition_snapshot():
    snap = build_quality_snapshot(
        coupon_fingerprint="z", matches=[match(1)],
        cards=[card(1, missing=("confirmed_lineup",))], stages=[stage()], data_mode="Multi-source"
    )
    assert snap["competitions"][0]["layer_coverage"]["confirmed_lineup"] == 0.0


def test_match_level_source_history_is_aggregated_per_competition():
    prov = [
        SimpleNamespace(match_number=1, competition="Championship", source="API-Football fixture", matched_units=1, attempted_units=1, status="ok"),
        SimpleNamespace(match_number=2, competition="Championship", source="API-Football fixture", matched_units=0, attempted_units=1, status="miss"),
    ]
    snap = build_quality_snapshot(
        coupon_fingerprint="p1", matches=[match(1, "Championship"), match(2, "Championship")],
        cards=[card(1), card(2)], stages=[stage()], data_mode="Multi-source", match_provenance=prov,
    )
    row = competition_source_history_rows([snap], min_attempted_units=2)[0]
    assert row["Liga/tävling"] == "Championship"
    assert row["Källa"] == "API-Football fixture"
    assert row["Matchat"] == "1/2"
    assert row["Täckning"] == "50%"


def test_old_snapshots_without_match_provenance_are_not_backfilled():
    snap = build_quality_snapshot(
        coupon_fingerprint="old", matches=[match(1)], cards=[card(1)], stages=[stage(matched=26, attempted=26)], data_mode="Multi-source"
    )
    assert competition_source_history_rows([snap]) == []


def test_failure_reason_history_uses_explicit_reason_codes_only():
    from data_quality_history import failure_reason_history_rows
    prov = [
        SimpleNamespace(match_number=1, competition="League Two", source="API-Football fixture", matched_units=0, attempted_units=1, status="Matchdatum saknas", reason_code="missing_match_date"),
        SimpleNamespace(match_number=2, competition="League Two", source="API-Football fixture", matched_units=1, attempted_units=1, status="Fixture säkert matchad", reason_code="matched"),
    ]
    snap = build_quality_snapshot(
        coupon_fingerprint="r1", matches=[match(1, "League Two"), match(2, "League Two")],
        cards=[card(1), card(2)], stages=[stage()], data_mode="Multi-source", match_provenance=prov,
    )
    rows = failure_reason_history_rows([snap])
    assert len(rows) == 1
    assert rows[0]["Felorsak"] == "Matchdatum saknas"
    assert "För lite data" in rows[0]["Underlag"]


def test_failure_reason_history_does_not_guess_old_free_text():
    from data_quality_history import failure_reason_history_rows
    old = {"coupon_fingerprint": "old", "data_mode": "Multi-source", "match_provenance": [
        {"match_number": 1, "competition": "League One", "source": "API-Football fixture", "matched_units": 0, "attempted_units": 1, "status": "Ingen säker fixture-matchning"}
    ]}
    assert failure_reason_history_rows([old]) == []
