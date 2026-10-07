from types import SimpleNamespace as NS

import system_decision_attribution as sda


def _summary(status, ready=True, delta=.2):
    return {"status": status, "review_ready": ready, "mean_p13_delta_pp": delta}


def test_attribution_does_not_add_overlapping_p13_effects(monkeypatch):
    monkeypatch.setattr(sda, "system_p13_summary", lambda c: _summary("GRANSKA SYSTEM-/BUDGETALLOKERING", True, .5))
    monkeypatch.setattr(sda, "guard_allocation_summary", lambda c: _summary("GRANSKA GARDERINGSALLOKERING", True, .3))
    monkeypatch.setattr(sda, "optimizer_audit_summary", lambda c: _summary("GRANSKA COUNTERFACTUAL MAX-13-STRUKTUR", True, .4))
    monkeypatch.setattr(sda, "spike_failure_summary", lambda c: {"status":"INGET TYDLIGT ÅTERKOMMANDE SPIKPROBLEM","review_ready":True})
    out=sda.decision_attribution_summary([NS()])
    assert out["priority"] == "TESTA GARDERINGSALLOKERING FÖRST"
    assert out["p13_effects_are_additive"] is False
    assert abs(out["guard_share_of_structure_headroom"]-.75) < 1e-12


def test_structure_wins_when_guard_does_not_explain_headroom(monkeypatch):
    monkeypatch.setattr(sda, "system_p13_summary", lambda c: _summary("GRANSKA SYSTEM-/BUDGETALLOKERING", True, .5))
    monkeypatch.setattr(sda, "guard_allocation_summary", lambda c: _summary("INGEN TYDLIG ÅTERKOMMANDE GARDERINGSBRIST", True, .05))
    monkeypatch.setattr(sda, "optimizer_audit_summary", lambda c: _summary("GRANSKA COUNTERFACTUAL MAX-13-STRUKTUR", True, .4))
    monkeypatch.setattr(sda, "spike_failure_summary", lambda c: {"status":"INGET TYDLIGT ÅTERKOMMANDE SPIKPROBLEM","review_ready":True})
    out=sda.decision_attribution_summary([NS()])
    assert out["priority"] == "TESTA SYSTEMSTRUKTUR FÖRST"
    assert out["residual_structure_headroom_pp"] > 0


def test_predictive_spike_signal_is_kept_separate(monkeypatch):
    monkeypatch.setattr(sda, "system_p13_summary", lambda c: _summary("INGEN TYDLIG P(13)-ALLOKERINGSBRIST", True, 0))
    monkeypatch.setattr(sda, "guard_allocation_summary", lambda c: _summary("INGEN TYDLIG ÅTERKOMMANDE GARDERINGSBRIST", True, 0))
    monkeypatch.setattr(sda, "optimizer_audit_summary", lambda c: _summary("INGEN TYDLIG STRUKTURELL P(13)-BRIST", True, 0))
    monkeypatch.setattr(sda, "spike_failure_summary", lambda c: {"status":"GRANSKA SPIKÖVERKONFIDENS","review_ready":True})
    out=sda.decision_attribution_summary([NS()])
    assert out["priority"] == "TESTA SANNOLIKHET/KALIBRERING FÖRE STRATEGI"
    assert out["spike_metrics_commensurable_with_p13"] is False
    assert out["automatic_model_change"] is False


def test_immature_data_cannot_rank_problem(monkeypatch):
    monkeypatch.setattr(sda, "system_p13_summary", lambda c: _summary("SAMLA MER PROSPEKTIV HISTORIK", False, 1))
    monkeypatch.setattr(sda, "guard_allocation_summary", lambda c: _summary("SAMLA MER PROSPEKTIV GARDERINGSHISTORIK", False, 1))
    monkeypatch.setattr(sda, "optimizer_audit_summary", lambda c: _summary("SAMLA MER PROSPEKTIV OPTIMERARHISTORIK", False, 1))
    monkeypatch.setattr(sda, "spike_failure_summary", lambda c: {"status":"SAMLA MER PROSPEKTIV SPIKHISTORIK","review_ready":False})
    out=sda.decision_attribution_summary([NS()])
    assert out["priority"] == "SAMLA MER PROSPEKTIV HISTORIK"
    assert out["uses_results_for_selection"] is False
