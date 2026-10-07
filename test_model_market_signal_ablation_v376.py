from pathlib import Path
from types import SimpleNamespace

from model_market_validation import model_market_summary, paired_observations
from signal_ablation import signal_ablation_scorecard
from factor_learning import FactorSnapshot
from release_info import APP_VERSION, RELEASE_NAME
from model_change_registry import get_model_change


def _coupon(cid="c1", *, n=13, model=(0.7,0.2,0.1), market=(0.6,0.25,0.15), result="1", factor=None):
    matches=[]
    for i in range(n):
        matches.append(SimpleNamespace(
            match_number=i+1, result=result, model=model, market=market,
            market_available=True, factors=(() if factor is None else (factor,))
        ))
    return SimpleNamespace(coupon_id=cid, matches=tuple(matches))


def test_v376_registry_entry_remains_non_predictive():
    c=get_model_change("3.76.0")
    assert c is not None and c.predictive_change is False
    assert "paired-model-market-validation" in c.components


def test_paired_model_market_uses_same_eligible_matches():
    rows=paired_observations([_coupon()])
    assert len(rows)==13
    assert all(r["brier_gain"] > 0 for r in rows)


def test_summary_requires_prospective_sample_even_if_model_is_better():
    s=model_market_summary([_coupon("c1")])
    assert s["review_ready"] is False
    assert s["automatic_model_change"] is False


def test_market_missing_is_excluded():
    c=_coupon()
    c.matches[0].market_available=False
    assert len(paired_observations([c])) == 12


def test_signal_ablation_positive_when_removing_signal_worsens_prediction():
    factor=FactorSnapshot(category="team_strength", name="Lagstyrka", source="test", verified=True,
        effective_strength=1.0, counterfactual=(0.55,0.30,0.15), delta=(0.15,-0.10,-0.05))
    coupons=[_coupon(f"c{i}", factor=factor) for i in range(10)]
    rows=signal_ablation_scorecard(coupons, min_observations=50, min_coupons=10)
    assert rows and rows[0]["review_ready"] is True
    assert rows[0]["brier_contribution"] > 0
    assert rows[0]["verdict"] == "Bidrar positivt i detta sample"


def test_ui_wires_v376_lab_and_release_note_protects_engines():
    ui=Path("ui_facit.py").read_text(encoding="utf-8")
    note=Path("MODEL_VS_MARKET_SIGNAL_ABLATION_v3.76.md").read_text(encoding="utf-8")
    assert "Model vs Market & Signal Ablation Lab" in ui
    assert "signal_ablation_summary" in ui
    assert "model_engine.py" in note and "strategy_engine.py" in note
