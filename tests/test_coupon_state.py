from coupon_state import ensure_coupon_state, set_coupon_state
from demo_data import get_demo_matches


def test_initialization_sets_coupon_metadata_without_stale_notice():
    state = {}
    ensure_coupon_state(state, get_demo_matches())
    assert len(state["coupon"]) == 13
    assert state["data_mode"] == "Demo"
    assert "analysis_stale_notice" not in state


def test_changed_coupon_invalidates_analysis_and_manual_state():
    coupon = get_demo_matches()
    state = {
        "coupon": coupon,
        "data_mode": "Demo",
        "source_message": "old",
        "one_click_result": object(),
        "one_click_coupon_fingerprint": "old-fp",
        "one_click_duration_seconds": 3.2,
        "manual_coupon": [("1",)] * 13,
    }
    changed = list(coupon)
    m = changed[0]
    changed[0] = type(m)(m.number, m.home + " X", m.away, m.odds, m.public, m.model)

    result = set_coupon_state(state, changed, data_mode="CSV-import", source_message="new")

    assert result.changed is True
    assert "one_click_result" not in state
    assert "one_click_coupon_fingerprint" not in state
    assert "one_click_duration_seconds" not in state
    assert "manual_coupon" not in state
    assert state["analysis_stale_notice"]
    assert state["data_mode"] == "CSV-import"


def test_identical_coupon_preserves_valid_analysis_on_rerun():
    coupon = get_demo_matches()
    marker = object()
    state = {
        "coupon": coupon,
        "one_click_result": marker,
        "one_click_coupon_fingerprint": "kept",
        "manual_coupon": [("1",)] * 13,
    }
    result = set_coupon_state(state, list(coupon), data_mode="Demo", source_message="same")
    assert result.changed is False
    assert state["one_click_result"] is marker
    assert state["one_click_coupon_fingerprint"] == "kept"
    assert "manual_coupon" in state


def test_rejects_incomplete_coupon():
    state = {}
    try:
        set_coupon_state(state, get_demo_matches()[:12], data_mode="Demo", source_message="bad")
    except ValueError as exc:
        assert "exakt 13" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_commit_analysis_keeps_new_result_when_enriched_coupon_changes():
    from coupon_state import commit_analysis_state
    coupon = get_demo_matches()
    state = {
        "coupon": coupon,
        "one_click_result": "old-analysis",
        "one_click_coupon_fingerprint": "old-fp",
    }
    enriched = list(coupon)
    m = enriched[0]
    enriched[0] = type(m)(m.number, m.home, m.away, (1.9, 3.4, 4.2), m.public, m.model)
    new_result = object()

    transition = commit_analysis_state(
        state,
        enriched_coupon=enriched,
        result=new_result,
        coupon_fingerprint_value="new-fp",
        duration_seconds=1.25,
    )

    assert transition.changed is True
    assert state["one_click_result"] is new_result
    assert state["one_click_coupon_fingerprint"] == "new-fp"
    assert state["one_click_duration_seconds"] == 1.25
    assert state["data_mode"] == "Multi-source"
    assert "analysis_stale_notice" not in state
