from expert_decision_summary import build_expert_decision_summary


def test_demo_is_never_ready_for_expert_decision():
    s = build_expert_decision_summary(
        data_mode="Demo", total_matches=13, market_verified=13,
        analysis_available=True, readiness_priority_text=None,
        evidence={"review_now": 3},
    )
    assert s.data_status == "DEMO – INTE SPELKLAR"
    assert "riktig kupong" in s.next_action
    assert s.edge_claim_allowed is False


def test_missing_market_overrides_evidence_queue():
    s = build_expert_decision_summary(
        data_mode="Svenska Spel", total_matches=13, market_verified=11,
        analysis_available=True, readiness_priority_text="Ingen tydlig datalucka dominerar.",
        evidence={"review_now": 4},
    )
    assert "MARKNADSANKARE" in s.data_status
    assert "2 av 13" in s.next_action
    assert s.evidence_status.startswith("4 segment")


def test_analysis_missing_is_explicit():
    s = build_expert_decision_summary(
        data_mode="Svenska Spel", total_matches=13, market_verified=13,
        analysis_available=False, readiness_priority_text=None, evidence={},
    )
    assert "ANALYS SAKNAS" in s.data_status
    assert "Analysera kupongen" in s.next_action


def test_reviewable_segments_become_next_action_only_when_data_gate_is_clear():
    s = build_expert_decision_summary(
        data_mode="Svenska Spel", total_matches=13, market_verified=13,
        analysis_available=True,
        readiness_priority_text="Ingen tydlig datalucka dominerar den aktuella kupongen. Förbättra inte fler källor utan historiskt stöd.",
        evidence={"review_now": 3, "timing_review": 2, "provenance_gaps": 0, "collect_more": 7},
    )
    assert s.data_status == "MARKNADSBAS VERIFIERAD"
    assert s.evidence_status == "3 segment värda manuell granskning"
    assert "Granska de 3 segment" in s.next_action


def test_readiness_priority_beats_history_when_current_coupon_has_gap():
    priority = "Största prioriterade dataluckan är skador/avstängningar: saknas för 6 av 13 matcher."
    s = build_expert_decision_summary(
        data_mode="Svenska Spel", total_matches=13, market_verified=13,
        analysis_available=True, readiness_priority_text=priority,
        evidence={"review_now": 5},
    )
    assert s.next_action == priority
    assert s.review_now == 5
