from core import MatchInput
from facit import (
    aggregate_performance, calibration_rows, dumps_facit, evaluate_coupon,
    loads_facit, make_coupon_snapshot, with_results,
)


def matches():
    out=[]
    for i in range(1,14):
        if i % 3 == 1:
            model=(0.60,0.25,0.15); public=(0.50,0.28,0.22); odds=(1.8,3.6,4.5)
        elif i % 3 == 2:
            model=(0.30,0.40,0.30); public=(0.34,0.34,0.32); odds=(2.8,3.1,2.9)
        else:
            model=(0.20,0.25,0.55); public=(0.28,0.27,0.45); odds=(3.8,3.4,2.0)
        out.append(MatchInput(i,f"H{i}",f"A{i}",odds,public,model))
    return out


def snapshot():
    ms=matches()
    sels=[("1",) if i%3==1 else ("X",) if i%3==2 else ("2",) for i in range(1,14)]
    return make_coupon_snapshot("c1",ms,sels,source="test",strategy="MAX 13",budget=128,rows=128,model_coverage=.12,captured_at="2026-09-02T12:00:00+00:00")


def test_snapshot_requires_13_matches():
    ms=matches()[:12]
    try:
        make_coupon_snapshot("x",ms,[("1",)]*12,source="x",strategy="MAX 13",budget=1,rows=1,model_coverage=.1)
        assert False
    except ValueError:
        assert True


def test_results_and_coupon_evaluation_all_covered():
    c=snapshot()
    results={i:("1" if i%3==1 else "X" if i%3==2 else "2") for i in range(1,14)}
    c=with_results(c,results)
    e=evaluate_coupon(c)
    assert e["completed"]==13
    assert e["system_hits"]==13
    assert e["thirteen_correct"] is True
    assert e["model_pick_hits"]==13


def test_partial_results_are_not_thirteen_correct():
    c=with_results(snapshot(),{1:"1",2:"X"})
    e=evaluate_coupon(c)
    assert e["completed"]==2
    assert e["thirteen_correct"] is False
    assert "inte komplett" in e["plain_summary"]


def test_invalid_result_rejected():
    try:
        with_results(snapshot(),{1:"3"})
        assert False
    except ValueError:
        assert True


def test_roundtrip_json():
    c=with_results(snapshot(),{1:"1",2:"X"})
    restored=loads_facit(dumps_facit([c]))
    assert len(restored)==1
    assert restored[0].matches[0].result=="1"
    assert restored[0].matches[1].selected==("X",)


def test_aggregate_performance_and_small_sample_warning():
    c=with_results(snapshot(),{i:("1" if i%3==1 else "X" if i%3==2 else "2") for i in range(1,14)})
    a=aggregate_performance([c])
    assert a["matches"]==13
    assert a["model_pick_accuracy"]==1.0
    assert a["system_13_count"]==1
    assert "litet" in a["lesson"]


def test_calibration_rows_has_observations():
    c=with_results(snapshot(),{i:("1" if i%3==1 else "X" if i%3==2 else "2") for i in range(1,14)})
    rows=calibration_rows([c])
    assert rows
    assert sum(r["antal"] for r in rows)==39
