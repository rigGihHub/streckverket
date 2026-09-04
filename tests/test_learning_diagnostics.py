from dataclasses import replace

from demo_data import get_demo_matches
from core import optimize_system
from facit import make_coupon_snapshot, with_results
from learning_diagnostics import diagnostic_segments, recommended_action, strongest_lessons


def _coupon(n=1):
    matches = get_demo_matches()
    system = optimize_system(matches, 128, "MAX 13", {})
    c = make_coupon_snapshot(
        f"c{n}", matches, system["selections"], source="test", strategy="MAX 13",
        budget=128, rows=system["rows"], model_coverage=system["coverage"],
    )
    results = {m.number: ("1", "X", "2")[(m.number + n) % 3] for m in matches}
    return with_results(c, results)


def test_empty_history_has_no_segments():
    assert diagnostic_segments([]) == []


def test_segments_include_all_matches():
    rows = diagnostic_segments([_coupon()], min_sample=5)
    overall = next(r for r in rows if r.segment == "Alla matcher")
    assert overall.matches == 13
    assert isinstance(overall.improvement, float)


def test_small_samples_are_not_overinterpreted():
    rows = diagnostic_segments([_coupon()], min_sample=30)
    assert all(r.verdict == "För lite data" for r in rows)
    lessons = strongest_lessons(rows)
    assert lessons["best"] is None
    assert "för lite historik" in lessons["summary"].lower()


def test_recommended_action_never_auto_changes_weights():
    rows = diagnostic_segments([_coupon(i) for i in range(1, 5)], min_sample=5)
    text = recommended_action(rows).lower()
    assert "automatiskt" in text or "ingen modelländring" in text


def test_invalid_min_sample_rejected():
    try:
        diagnostic_segments([_coupon()], min_sample=4)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
