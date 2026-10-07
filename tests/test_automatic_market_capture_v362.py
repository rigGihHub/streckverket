from dataclasses import dataclass
from automatic_market_capture import automatic_market_capture, capture_eligible
from history_store import SQLiteHistoryStore

@dataclass
class M:
    number:int; home:str; away:str; kickoff:str; market:tuple=(.5,.3,.2); market_available:bool=True
    market_source:str='verified'; market_bookmaker_count:int=4; market_last_update:str|None=None

def matches(kickoff='2026-09-08T18:00:00+00:00'):
    return [M(i,f'H{i}',f'A{i}',kickoff) for i in range(1,14)]

def test_demo_never_captured(tmp_path):
    store=SQLiteHistoryStore(str(tmp_path/'x.db'))
    r=automatic_market_capture(store,matches(),data_mode='Demo',captured_at='2026-09-08T10:00:00+00:00')
    assert r.status=='SKIPPED' and store.load_market_points()==[]

def test_real_coupon_is_captured_and_deduped(tmp_path):
    store=SQLiteHistoryStore(str(tmp_path/'x.db'))
    ms=matches()
    a=automatic_market_capture(store,ms,data_mode='Svenska Spel',captured_at='2026-09-08T10:00:00+00:00')
    b=automatic_market_capture(store,ms,data_mode='Svenska Spel',captured_at='2026-09-08T10:03:00+00:00')
    assert a.status=='SAVED' and a.saved_points==13
    assert b.status=='UNCHANGED'
    assert len(store.load_market_points())==13

def test_changed_market_inside_five_minutes_is_kept(tmp_path):
    store=SQLiteHistoryStore(str(tmp_path/'x.db'))
    ms=matches()
    automatic_market_capture(store,ms,data_mode='Svenska Spel',captured_at='2026-09-08T10:00:00+00:00')
    ms[0].market=(.55,.25,.20)
    r=automatic_market_capture(store,ms,data_mode='Svenska Spel',captured_at='2026-09-08T10:03:00+00:00')
    assert r.status=='SAVED' and r.saved_points==1

def test_ineligible_without_market():
    ms=matches()
    for m in ms: m.market_available=False
    ok,_=capture_eligible(ms,data_mode='Svenska Spel')
    assert not ok

def test_capture_eligibility_uses_observation_time_not_wall_clock():
    # Historical/prospective timestamps must be judged against their own capture
    # time. Otherwise a valid stored pre-kickoff observation becomes "post kickoff"
    # merely because the test/app is run later.
    ok, reason = capture_eligible(
        matches('2026-09-08T18:00:00+00:00'),
        data_mode='Svenska Spel',
        captured_at='2026-09-08T10:00:00+00:00',
    )
    assert ok, reason
