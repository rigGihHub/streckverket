from pathlib import Path
import pytest
from types import SimpleNamespace

from facit import FacitCoupon, FacitMatch, dumps_facit, loads_facit, with_results
from predictive_experiment import (
    MARKET_PULL_EXPERIMENT_ID, ShadowPrediction, build_shadow_predictions,
    eligible_shadow_spec, shadow_experiment_summary,
)
from model_change_registry import get_model_change
from release_info import APP_VERSION, RELEASE_NAME


def _history_coupon(cid, *, model=(0.50,.30,.20), market=(.70,.20,.10), result="1"):
    return SimpleNamespace(coupon_id=cid, matches=tuple(SimpleNamespace(
        match_number=i+1, result=result, model=model, market=market,
        market_available=True, factors=()
    ) for i in range(13)))


def _live_matches():
    return [SimpleNamespace(number=i+1, model=(.50,.30,.20), market=(.70,.20,.10), market_available=True) for i in range(13)]


def test_v378_is_registered_and_non_predictive():
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (3, 78, 0)
    change = get_model_change("3.78.0")
    assert change is not None and change.predictive_change is False
    assert "shadow-mode" in change.components


def test_shadow_candidate_is_blocked_before_v377_gate_opens():
    assert eligible_shadow_spec([_history_coupon("c1")]) is None
    assert build_shadow_predictions(_live_matches(), [_history_coupon("c1")], source_model_version="3.78.0") == {}


def test_market_pull_candidate_freezes_only_after_mature_market_win():
    history=[_history_coupon(f"c{i}") for i in range(20)]
    spec=eligible_shadow_spec(history)
    assert spec is not None and spec["experiment_id"] == MARKET_PULL_EXPERIMENT_ID
    preds=build_shadow_predictions(_live_matches(), history, source_model_version="3.78.0")
    p=preds[1][0]
    assert p.probabilities == pytest.approx((0.55, 0.275, 0.175))
    assert p.source_model_version == "3.78.0"


def test_shadow_predictions_roundtrip_and_survive_results():
    pred=ShadowPrediction(MARKET_PULL_EXPERIMENT_ID,"25 % närmare bookmakerankaret",(.55,.275,.175),"3.78.0","fixed")
    matches=tuple(FacitMatch(i+1,f"H{i}",f"A{i}",(.5,.3,.2),(.7,.2,.1),(.5,.3,.2),("1",),market_available=True,shadow_predictions=(pred,)) for i in range(13))
    coupon=FacitCoupon("c","2026-09-10T00:00:00Z","Live","MAX 13",100,1,.1,matches,model_version="3.78.0")
    restored=loads_facit(dumps_facit([coupon]))[0]
    assert restored.matches[0].shadow_predictions[0].experiment_id == MARKET_PULL_EXPERIMENT_ID
    completed=with_results(restored,{i:"1" for i in range(1,14)})
    assert completed.matches[0].shadow_predictions[0].probabilities == (.55,.275,.175)


def test_shadow_summary_does_not_backfill_legacy_coupons():
    legacy=_history_coupon("legacy")
    result=shadow_experiment_summary([legacy])
    assert result["completed_matches"] == 0
    assert result["status"] == "INGA FÄRDIGA SHADOW-OBSERVATIONER"


def test_ui_and_release_note_keep_candidate_isolated():
    ui=Path("ui_facit.py").read_text(encoding="utf-8")
    note=Path("PREDICTIVE_EXPERIMENT_FRAMEWORK_v3.78.md").read_text(encoding="utf-8")
    assert "Predictive Experiment Framework · Shadow mode" in ui
    assert "Gamla kuponger backfillas aldrig" in ui
    assert "model_engine.py" in note and "strategy_engine.py" in note
