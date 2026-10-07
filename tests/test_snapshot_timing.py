from dataclasses import replace
from datetime import datetime, timedelta, timezone

from snapshot_timing import classify_snapshot_timing, summarize_snapshot_timing
from tests.test_verification_engine import _coupon


def test_timing_buckets_are_explicit_and_pre_match():
    captured = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
    assert classify_snapshot_timing(captured.isoformat(), (captured + timedelta(minutes=45)).isoformat()).bucket == "LE_1H"
    assert classify_snapshot_timing(captured.isoformat(), (captured + timedelta(hours=2)).isoformat()).bucket == "1_3H"
    assert classify_snapshot_timing(captured.isoformat(), (captured + timedelta(hours=8)).isoformat()).bucket == "3_12H"
    assert classify_snapshot_timing(captured.isoformat(), (captured - timedelta(minutes=1)).isoformat()).eligible_pre_match is False


def test_unknown_timing_is_not_treated_as_near_kickoff():
    row = classify_snapshot_timing("2026-09-04T18:00:00+00:00", None)
    assert row.bucket == "UNKNOWN"
    assert row.hours_before_kickoff is None
    assert row.eligible_pre_match is False


def test_summary_counts_near_kickoff_without_calling_it_closing_line():
    base = _coupon('01')
    captured = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
    matches = tuple(replace(m, kickoff=(captured + timedelta(hours=2)).isoformat()) for m in base.matches)
    coupon = replace(base, captured_at=captured.isoformat(), matches=matches)
    summary = summarize_snapshot_timing([coupon])
    assert summary["within_3h"] == 13
    assert summary["known"] == 13
    assert summary["post_kickoff"] == 0
