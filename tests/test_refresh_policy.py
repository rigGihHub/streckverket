from datetime import datetime, timezone, timedelta
from refresh_policy import build_refresh_plan, is_due

def test_refresh_gets_faster_near_deadline():
    now=datetime(2026,9,1,12,tzinfo=timezone.utc)
    far=build_refresh_plan(now+timedelta(hours=30),now)
    near=build_refresh_plan(now+timedelta(minutes=15),now)
    assert near.intervals_minutes['odds'] < far.intervals_minutes['odds']
    assert near.intervals_minutes['lineups'] < far.intervals_minutes['lineups']

def test_is_due_without_previous_update():
    assert is_due(None,10)

def test_is_due_respects_interval():
    now=datetime(2026,9,1,12,tzinfo=timezone.utc)
    assert is_due(now-timedelta(minutes=11),10,now)
    assert not is_due(now-timedelta(minutes=5),10,now)
