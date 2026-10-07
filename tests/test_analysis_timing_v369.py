from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from analysis_timing import analysis_timing_advice

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

def m(hours=None, kickoff=None):
    if kickoff is None and hours is not None:
        kickoff = (NOW + timedelta(hours=hours)).isoformat()
    return SimpleNamespace(kickoff=kickoff)

def test_unknown_time_never_invents_deadline():
    a = analysis_timing_advice([m(kickoff=None)], now=NOW)
    assert a.headline == "TIDPUNKT OKÄND"
    assert "inte verifierat officiellt spelstopp" in a.basis

def test_early_check_more_than_day():
    assert analysis_timing_advice([m(30)], now=NOW).headline == "TIDIG KOLL"

def test_first_analysis_window():
    assert analysis_timing_advice([m(12)], now=NOW).headline == "BRA LÄGE FÖR FÖRSTA ANALYS"

def test_final_check_approaches():
    assert analysis_timing_advice([m(3)], now=NOW).headline == "SLUTLIG KONTROLL NÄRMAR SIG"

def test_final_check_now():
    assert analysis_timing_advice([m(.5)], now=NOW).headline == "GÖR SLUTLIG KONTROLL NU"

def test_passed_kickoff_is_not_prematch():
    assert analysis_timing_advice([m(-1), m(2)], now=NOW).headline == "MATCH HAR STARTAT"

def test_uses_earliest_known_kickoff():
    a = analysis_timing_advice([m(8), m(2)], now=NOW)
    assert a.headline == "SLUTLIG KONTROLL NÄRMAR SIG"
    assert round(a.hours_to_first_kickoff, 1) == 2.0
