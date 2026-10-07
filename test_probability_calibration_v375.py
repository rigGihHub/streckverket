from facit import FacitCoupon, FacitMatch
from probability_calibration import calibration_rows, calibration_summary, outcome_calibration_rows


def m(n, result="1", model=(.62,.23,.15), market=(.58,.25,.17), selected=("1",), available=True):
    return FacitMatch(n,f"H{n}",f"A{n}",model,market,(.5,.3,.2),tuple(selected),result=result,market_available=available)

def c(cid="c", matches=None):
    return FacitCoupon(cid,"2026-09-01T10:00:00+00:00","test","MAX 13",100,100,.1,tuple(matches or [m(i) for i in range(1,14)]))


def test_model_top_pick_calibration_uses_frozen_probability_and_result():
    rows=calibration_rows([c()])
    row=next(r for r in rows if r["Intervall"]=="60–65 %")
    assert row["Matcher"]==13
    assert abs(row["Snittprognos"]-.62)<1e-12
    assert row["Faktisk träff"]==1.0


def test_market_missing_is_excluded_not_backfilled():
    matches=[m(i, available=(i != 1)) for i in range(1,14)]
    s=calibration_summary([c(matches=matches)])
    assert s["model"]["matches"]==13
    assert s["market"]["matches"]==12


def test_spike_bins_only_use_saved_single_sign_selections():
    matches=[m(i, selected=(("1","X") if i==1 else ("1",))) for i in range(1,14)]
    rows=calibration_rows([c(matches=matches)], spikes_only=True)
    assert sum(r["Matcher"] for r in rows)==12


def test_outcome_rows_separate_home_draw_away():
    matches=[m(i, result="X", model=(.2,.60,.2)) for i in range(1,14)]
    rows=outcome_calibration_rows([c(matches=matches)])
    x=next(r for r in rows if r["Tecken"]=="X" and r["Intervall"]=="60–65 %")
    assert x["Matcher"]==13 and x["Faktisk frekvens"]==1.0


def test_small_sample_never_creates_automatic_spike_rule():
    s=calibration_summary([c()], min_review_coupons=20)
    assert s["review_ready"] is False
    assert s["status"]=="SAMLA MER PROSPEKTIV HISTORIK"
    assert s["automatic_threshold_change"] is False
    assert s["automatic_model_change"] is False
