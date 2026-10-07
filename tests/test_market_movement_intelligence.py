from market_movement_intelligence import (
    assess_match_movement,
    classify_magnitude,
    movement_rows,
    supporter_timing_rows,
)
from market_timeline import MarketPoint


def point(t, market, *, n=1, home="A", away="B", available=True):
    return MarketPoint(
        coupon_key="coupon",
        match_number=n,
        home=home,
        away=away,
        captured_at=t,
        kickoff="2026-09-05T15:00:00+00:00",
        market=market,
        market_available=available,
        market_source="test",
    )


def test_magnitude_buckets_are_descriptive():
    assert classify_magnitude(0.9) == "STABIL"
    assert classify_magnitude(1.0) == "MÅTTLIG RÖRELSE"
    assert classify_magnitude(2.9) == "MÅTTLIG RÖRELSE"
    assert classify_magnitude(3.0) == "KRAFTIG RÖRELSE"


def test_assessment_uses_first_and_last_verified_points():
    rows = [
        point("2026-09-05T10:00:00+00:00", (0.50, 0.30, 0.20)),
        point("2026-09-05T11:00:00+00:00", (0.52, 0.29, 0.19), available=False),
        point("2026-09-05T12:00:00+00:00", (0.54, 0.28, 0.18)),
    ]
    a = assess_match_movement(rows)
    assert a is not None
    assert a.points == 2
    assert a.classification == "KRAFTIG RÖRELSE"
    assert a.strongest_outcome == "1"
    assert round(a.strongest_delta_pp, 1) == 4.0


def test_assessment_requires_two_verified_points():
    assert assess_match_movement([point("2026-09-05T10:00:00+00:00", (0.5, 0.3, 0.2))]) is None


def test_movement_rows_do_not_call_anything_edge():
    rows = movement_rows([
        point("2026-09-05T10:00:00+00:00", (0.50, 0.30, 0.20)),
        point("2026-09-05T12:00:00+00:00", (0.48, 0.31, 0.21)),
    ], coupon_key="coupon")
    assert len(rows) == 1
    assert "edge" not in " ".join(str(v).lower() for v in rows[0].values())


def test_supporter_timing_can_show_pulse_before_observed_move():
    points = [
        point("2026-09-05T10:00:00+00:00", (0.50, 0.30, 0.20)),
        point("2026-09-05T12:00:00+00:00", (0.515, 0.29, 0.195)),
    ]
    history = [{
        "match_number": 1, "home": "A", "away": "B", "team": "A",
        "captured_at": "2026-09-05T11:00:00+00:00",
    }]
    rows = supporter_timing_rows(points, history, coupon_key="coupon")
    assert len(rows) == 1
    assert rows[0]["Tidsrelation"] == "FÖRE OBSERVERAD RÖRELSE"
    assert rows[0]["Skillnad timmar"] == 1.0


def test_supporter_timing_does_not_invent_exact_move_time_without_threshold_crossing():
    points = [
        point("2026-09-05T10:00:00+00:00", (0.50, 0.30, 0.20)),
        point("2026-09-05T12:00:00+00:00", (0.505, 0.297, 0.198)),
    ]
    history = [{
        "match_number": 1, "home": "A", "away": "B", "team": "A",
        "captured_at": "2026-09-05T11:00:00+00:00",
    }]
    assert supporter_timing_rows(points, history, coupon_key="coupon") == []
