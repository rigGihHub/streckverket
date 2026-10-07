from facit import FacitCoupon, FacitMatch
from thirteen_right_performance import coupon_diagnostic, miss_rows, performance_summary


def _match(n, result, selected=("1",), model=(0.6,0.25,0.15), market=(0.55,0.25,0.20), market_available=True):
    return FacitMatch(n, f"H{n}", f"A{n}", model, market, (0.5,0.3,0.2), tuple(selected), result=result, market_available=market_available)


def _coupon(matches, cid="c1", coverage=0.10):
    return FacitCoupon(cid, "2026-09-01T10:00:00+00:00", "test", "MAX 13", 100, 100, coverage, tuple(matches))


def test_classifies_spike_half_and_allocation_miss():
    matches=[_match(i,"1",("1",)) for i in range(1,14)]
    matches[0]=_match(1,"2",("1",),model=(0.2,0.2,0.6))  # model right, system excluded -> allocation miss
    matches[1]=_match(2,"2",("1","X"),model=(0.5,0.3,0.2))
    d=coupon_diagnostic(_coupon(matches))
    assert d.system_hits == 11
    assert d.missed_spikes == 1
    assert d.missed_halves == 1
    assert d.allocation_misses == 1


def test_incomplete_coupon_is_excluded():
    matches=[_match(i,"1",("1",)) for i in range(1,14)]
    matches[-1]=FacitMatch(13,"H13","A13",(0.6,.2,.2),(.6,.2,.2),(.6,.2,.2),("1",),result=None)
    assert coupon_diagnostic(_coupon(matches)) is None
    s=performance_summary([_coupon(matches)])
    assert s["complete_coupons"] == 0
    assert s["priority"] == "SAMLA FACIT"


def test_summary_compares_frozen_expected_13_without_claiming_edge():
    perfect=_coupon([_match(i,"1",("1",)) for i in range(1,14)],"perfect",coverage=.20)
    missed=[_match(i,"1",("1",)) for i in range(1,14)]
    missed[0]=_match(1,"2",("1",),model=(.7,.2,.1))
    other=_coupon(missed,"other",coverage=.10)
    s=performance_summary([perfect,other],min_review_coupons=20)
    assert s["thirteen_correct"] == 1
    assert abs(s["expected_13_count_from_frozen_model"]-.30) < 1e-12
    assert s["review_ready"] is False
    assert s["automatic_model_change"] is False
    assert s["edge_claim_allowed"] is False


def test_miss_rows_preserve_observed_failure_not_hindsight_reconstruction():
    matches=[_match(i,"1",("1",)) for i in range(1,14)]
    matches[4]=_match(5,"X",("1","2"),model=(.40,.35,.25))
    rows=miss_rows([_coupon(matches)])
    assert len(rows) == 1
    assert rows[0]["Match"] == 5
    assert rows[0]["Typ"] == "HALVGARDERINGSMISS"
    assert rows[0]["Utfall"] == "X"
    assert rows[0]["Rätt utfalls modellrank"] == 2
