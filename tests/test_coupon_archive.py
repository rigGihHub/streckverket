from facit import make_coupon_snapshot, with_results
from demo_data import get_demo_matches
from coupon_archive import archive_rows, archive_summary, coupon_status, factor_archive_rows, filter_coupons, match_archive_rows


def _coupon(coupon_id="c1", captured_at="2026-09-01T10:00:00+00:00", strategy="MAX 13"):
    matches = get_demo_matches()
    selections = [("1", "X", "2") for _ in matches]
    return make_coupon_snapshot(
        coupon_id,
        matches,
        selections,
        source="Testkälla",
        strategy=strategy,
        budget=100,
        rows=100,
        model_coverage=0.5,
        captured_at=captured_at,
    )


def test_status_waiting_partial_and_complete():
    coupon = _coupon()
    assert coupon_status(coupon) == "Väntar på facit"
    partial = with_results(coupon, {1: "1"})
    assert coupon_status(partial) == "Pågående facit"
    complete = with_results(coupon, {i: "1" for i in range(1, 14)})
    assert coupon_status(complete) == "Systemet täckte 13"


def test_archive_rows_newest_first():
    older = _coupon("old", "2026-09-01T10:00:00+00:00")
    newer = _coupon("new", "2026-09-02T10:00:00+00:00")
    rows = archive_rows([older, newer])
    assert [r.coupon_id for r in rows] == ["new", "old"]


def test_filter_by_strategy_and_team_query():
    a = _coupon("a", strategy="MAX 13")
    b = _coupon("b", strategy="VÄRDE")
    assert [c.coupon_id for c in filter_coupons([a, b], strategy="VÄRDE")] == ["b"]
    team = a.matches[0].home
    assert filter_coupons([a, b], query=team)


def test_match_rows_are_13_and_plain():
    coupon = with_results(_coupon(), {1: "1"})
    rows = match_archive_rows(coupon)
    assert len(rows) == 13
    assert rows[0]["Resultat"] == "1"
    assert rows[0]["Täckt"] == "Ja"


def test_factor_rows_empty_without_saved_factors():
    assert factor_archive_rows(_coupon()) == []


def test_archive_summary_counts():
    waiting = _coupon("w")
    complete = with_results(_coupon("done"), {i: "1" for i in range(1, 14)})
    summary = archive_summary([waiting, complete])
    assert summary["coupons"] == 2
    assert summary["complete"] == 1
    assert summary["thirteen"] == 1
    assert summary["waiting"] == 1
