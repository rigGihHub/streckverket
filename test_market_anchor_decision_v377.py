from pathlib import Path
from types import SimpleNamespace

from factor_learning import FactorSnapshot
from market_anchor_decision import market_anchor_decision
from model_change_registry import get_model_change
from release_info import APP_VERSION, RELEASE_NAME


def _coupon(cid, *, model=(0.70,0.20,0.10), market=(0.60,0.25,0.15), result="1", factor=None):
    return SimpleNamespace(
        coupon_id=cid,
        matches=tuple(SimpleNamespace(
            match_number=i+1,
            result=result,
            model=model,
            market=market,
            market_available=True,
            factors=(() if factor is None else (factor,)),
        ) for i in range(13)),
    )


def test_v377_registry_entry_remains_non_predictive():
    change = get_model_change("3.77.0")
    assert change is not None and change.predictive_change is False
    assert change.parent_version == "3.76.0"


def test_gate_blocks_small_sample():
    result = market_anchor_decision([_coupon("c1")])
    assert result["status"] == "INGET PREDIKTIVT EXPERIMENT ÄNNU"
    assert result["candidate_experiment"] is None
    assert result["automatic_model_change"] is False
    assert result["engine_change_allowed"] is False


def test_gate_prefers_market_when_market_beats_mature_model():
    coupons=[_coupon(f"c{i}", model=(0.50,0.30,0.20), market=(0.70,0.20,0.10)) for i in range(20)]
    result=market_anchor_decision(coupons)
    assert result["model_market"]["review_ready"] is True
    assert result["status"] == "MARKNADSANKARET SKA PRIORITERAS"
    assert result["candidate_experiment"] == "TESTA MINDRE MODELLJUSTERINGAR MOT MARKNADSANKARET"
    assert result["engine_change_allowed"] is False


def test_specific_signal_candidate_requires_mature_positive_ablation():
    factor=FactorSnapshot(
        category="team_strength", name="Lagstyrka", source="test", verified=True,
        effective_strength=1.0, counterfactual=(0.55,0.30,0.15), delta=(0.15,-0.10,-0.05)
    )
    coupons=[_coupon(f"c{i}", factor=factor) for i in range(20)]
    result=market_anchor_decision(coupons)
    assert result["status"] == "PREDIKTIVT EXPERIMENT KAN MOTIVERAS"
    assert "GRUNDSTYRKA" in result["candidate_experiment"]
    assert result["positive_mature_signals"] >= 1
    assert result["automatic_model_change"] is False


def test_release_note_and_ui_preserve_engine_guard():
    note=Path("MARKET_ANCHOR_DECISION_v3.77.md").read_text(encoding="utf-8")
    ui=Path("ui_facit.py").read_text(encoding="utf-8")
    assert "model_engine.py" in note and "strategy_engine.py" in note
    assert "Market Anchor Decision Lab" in ui
    assert "Blandad evidens = ändra inget" in ui
