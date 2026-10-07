from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from capture_quality import assess_capture_quality


def _match(*, market=True, kickoff_hours=3, source="the_odds_api", books=5, update_minutes=5, conf=1.0):
    now = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        market_available=market,
        kickoff=(now + timedelta(hours=kickoff_hours)).isoformat(),
        market_source=source,
        market_bookmaker_count=books,
        market_last_update=(now - timedelta(minutes=update_minutes)).isoformat() if update_minutes is not None else None,
        market_match_confidence=conf,
        public_last_update=(now - timedelta(minutes=5)).isoformat(),
    )


def test_good_capture_is_saveable():
    now = "2026-09-04T18:00:00+00:00"
    gate = assess_capture_quality([_match() for _ in range(13)], captured_at=now)
    assert gate.can_save is True
    assert gate.status == "BRA"
    assert gate.verified_market_matches == 13
    assert gate.average_score >= 80


def test_missing_one_market_blocks_facit_capture():
    now = "2026-09-04T18:00:00+00:00"
    matches = [_match() for _ in range(12)] + [_match(market=False)]
    gate = assess_capture_quality(matches, captured_at=now)
    assert gate.can_save is False
    assert gate.status == "VÄNTA"
    assert gate.verified_market_matches == 12
    assert "12/13" in gate.message


def test_started_match_blocks_pre_match_capture():
    now = "2026-09-04T18:00:00+00:00"
    matches = [_match() for _ in range(12)] + [_match(kickoff_hours=-1)]
    gate = assess_capture_quality(matches, captured_at=now)
    assert gate.can_save is False
    assert gate.status == "SPARA INTE"
    assert gate.started_matches == 1


def test_weak_metadata_does_not_become_prediction_claim():
    now = "2026-09-04T18:00:00+00:00"
    matches = [_match(source="", books=None, update_minutes=None, conf=None) for _ in range(13)]
    gate = assess_capture_quality(matches, captured_at=now)
    assert gate.can_save is True
    assert gate.status in {"SVAG", "GODKÄND"}
    assert gate.evidence_coverage < 100
    assert any("odds" in action.lower() for action in gate.actions)


def test_wrong_coupon_size_blocks_capture():
    gate = assess_capture_quality([_match() for _ in range(12)], captured_at="2026-09-04T18:00:00+00:00")
    assert gate.can_save is False
    assert gate.status == "SPARA INTE"
