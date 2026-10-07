from datetime import datetime, timezone

from core import MatchInput
from facit import dumps_facit, loads_facit, make_coupon_snapshot, with_results
from swap_backtest import (
    SwapProposalSnapshot,
    evaluate_swap_proposal,
    snapshot_reallocation_proposals,
    swap_backtest_summary,
)


def m(n, model):
    return MatchInput(n, f"H{n}", f"A{n}", (2.0, 3.2, 4.0), (.34, .33, .33), model)


def full_coupon_matches():
    rows = [m(1, (.50,.30,.20)), m(2, (.45,.40,.15))]
    rows += [m(i, (.80,.10,.10)) for i in range(3,14)]
    return rows


def make_snapshot(results=None, *, proposals=True):
    matches = full_coupon_matches()
    sels = [("1","X"),("1",)] + [("1",)]*11
    system = {"rows":2,"selections":sels,"coverage":.05}
    ps = snapshot_reallocation_proposals(matches, system, limit=5) if proposals else ()
    c = make_coupon_snapshot(
        "c1", matches, sels, source="test", strategy="MAX 13", budget=2,
        rows=2, model_coverage=.05, captured_at="2026-09-06T12:00:00+00:00",
        model_version="3.52.0", swap_proposals=ps,
    )
    return with_results(c, results or {})


def test_snapshot_saves_exact_prospective_proposal():
    c = make_snapshot()
    assert c.swap_proposals
    p = c.swap_proposals[0]
    assert p.rank == 1
    assert p.rows == c.rows
    assert p.donor_match_number == 1
    assert p.recipient_match_number == 2
    assert p.donor_from == ("1","X")
    assert p.recipient_from == ("1",)


def test_swap_proposal_roundtrips_through_facit_json():
    c = make_snapshot()
    restored = loads_facit(dumps_facit([c]))[0]
    assert restored.swap_proposals == c.swap_proposals


def test_legacy_facit_without_swap_metadata_loads_as_unknown_not_reconstructed():
    c = make_snapshot(proposals=False)
    text = dumps_facit([c]).replace(',\n    "swap_proposals": []', '')
    restored = loads_facit(text)[0]
    assert restored.swap_proposals == ()


def test_with_results_preserves_swap_provenance():
    c = make_snapshot()
    updated = with_results(c, {i:"1" for i in range(1,14)})
    assert updated.swap_proposals == c.swap_proposals


def test_backtest_can_show_better_actual_coverage():
    # Original: M1 covers 1/X, M2 only 1. The best swap moves X cover to M2.
    c = make_snapshot({1:"1", 2:"X", **{i:"1" for i in range(3,14)}})
    r = evaluate_swap_proposal(c, c.swap_proposals[0])
    assert r.completed
    assert r.original_hits == 12
    assert r.swapped_hits == 13
    assert r.hit_delta == 1
    assert r.original_13 is False and r.swapped_13 is True
    assert r.verdict == "BÄTTRE UTFALLSTÄCKNING"


def test_backtest_can_show_worse_actual_coverage():
    c = make_snapshot({1:"X", 2:"1", **{i:"1" for i in range(3,14)}})
    r = evaluate_swap_proposal(c, c.swap_proposals[0])
    assert r.original_hits == 13
    assert r.swapped_hits == 12
    assert r.hit_delta == -1
    assert r.verdict == "SÄMRE UTFALLSTÄCKNING"


def test_incomplete_coupon_waits_for_facit():
    c = make_snapshot({1:"1"})
    r = evaluate_swap_proposal(c, c.swap_proposals[0])
    assert not r.completed
    assert r.verdict == "VÄNTAR PÅ FACIT"


def test_corrupt_provenance_fails_closed():
    c = make_snapshot({i:"1" for i in range(1,14)})
    p = c.swap_proposals[0]
    bad = SwapProposalSnapshot(
        rank=1, donor_match_number=p.donor_match_number, donor_from=("2",), donor_to=p.donor_to,
        recipient_match_number=p.recipient_match_number, recipient_from=p.recipient_from,
        recipient_to=p.recipient_to, rows=p.rows,
        predicted_delta_coverage_pp=p.predicted_delta_coverage_pp,
        predicted_relative_gain_pct=p.predicted_relative_gain_pct,
    )
    r = evaluate_swap_proposal(c, bad)
    assert r.verdict == "OGILTIG PROVENIENS"
    assert r.hit_delta is None


def test_summary_requires_20_completed_primary_proposals_before_review_status():
    coupons=[]
    for n in range(19):
        c=make_snapshot({1:"1",2:"X",**{i:"1" for i in range(3,14)}})
        object.__setattr__(c, "coupon_id", f"c{n}")
        coupons.append(c)
    s=swap_backtest_summary(coupons)
    assert s["completed_primary"] == 19
    assert s["better"] == 19
    assert s["status"] == "FÖR LITE PROSPEKTIV HISTORIK"


def test_old_coupons_are_counted_but_never_backfilled():
    c=make_snapshot(proposals=False)
    s=swap_backtest_summary([c])
    assert s["legacy_without_proposal"] == 1
    assert s["prospective_coupons"] == 0
    assert s["completed_primary"] == 0


def test_ui_capture_passes_locks_and_saves_swap_proposals():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    ui=(root/'ui_facit.py').read_text()
    app=(root/'app.py').read_text()
    assert 'snapshot_reallocation_proposals(matches, system, locks=locks, limit=5)' in ui
    assert 'swap_proposals=swap_proposals' in ui
    assert 'render_facit_learning(matches, budget, strategy, system, locks)' in app
    assert 'Omfördelningsfacit – prospektivt test' in ui
