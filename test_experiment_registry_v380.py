from types import SimpleNamespace

from experiment_registry import (
    MARKET_PULL_EXPERIMENT_ID,
    STATUS_ACTIVE, STATUS_PAUSED, STATUS_REJECTED, STATUS_WAITING_GATE,
    experiment_lifecycle, get_experiment, registered_experiments,
)
from predictive_experiment import ShadowPrediction, build_shadow_predictions
from facit import FacitCoupon, FacitMatch
from model_change_registry import get_model_change
from release_info import APP_VERSION


def _history_coupon(cid, *, model=(0.50,.30,.20), market=(.70,.20,.10), result='1'):
    return SimpleNamespace(coupon_id=cid, matches=tuple(SimpleNamespace(
        match_number=i+1, result=result, model=model, market=market,
        market_available=True, factors=(), shadow_predictions=()
    ) for i in range(13)))


def _shadow_coupon(cid, *, candidate=(.80,.12,.08), baseline=(.65,.22,.13), result='1'):
    pred=ShadowPrediction(MARKET_PULL_EXPERIMENT_ID,'candidate',candidate,'3.78.0','fixed')
    matches=tuple(FacitMatch(i+1,f'H{i}',f'A{i}',baseline,(.75,.15,.10),(.75,.15,.10),('1',),
                             result=result,market_available=True,shadow_predictions=(pred,)) for i in range(13))
    return FacitCoupon(cid,'2026-09-10T00:00:00Z','Live','MAX 13',100,1,.1,matches,model_version='3.78.0')


def test_v380_registered_and_non_predictive():
    assert tuple(int(x) for x in APP_VERSION.split('.')) >= (3, 80, 0)
    c=get_model_change('3.80.0')
    assert c is not None and c.predictive_change is False


def test_registry_is_explicit_and_pre_registered():
    exp=get_experiment(MARKET_PULL_EXPERIMENT_ID)
    assert exp is not None
    assert exp.created_version == '3.78.0'
    assert dict(exp.pre_registered_parameters)['market_weight'] == .25
    assert registered_experiments() == (exp,)


def test_waiting_gate_does_not_snapshot():
    history=[_history_coupon('c1')]
    life=experiment_lifecycle(history)
    assert life['status'] == STATUS_WAITING_GATE
    assert life['accepts_new_snapshots'] is False


def test_open_gate_starts_registered_experiment():
    history=[_history_coupon(f'c{i}') for i in range(20)]
    life=experiment_lifecycle(history)
    assert life['status'] == STATUS_ACTIVE
    assert life['accepts_new_snapshots'] is True


def test_rejected_experiment_stops_future_snapshots():
    history=[_shadow_coupon(f'c{i}', candidate=(.50,.30,.20), baseline=(.75,.15,.10)) for i in range(20)]
    life=experiment_lifecycle(history)
    assert life['status'] == STATUS_REJECTED
    assert life['terminal'] is True
    assert life['accepts_new_snapshots'] is False
    live=[SimpleNamespace(number=i+1,model=(.5,.3,.2),market=(.7,.2,.1),market_available=True) for i in range(13)]
    assert build_shadow_predictions(live, history, source_model_version='3.80.0') == {}


def test_promoted_shadow_phase_pauses_before_any_production_change():
    history=[_shadow_coupon(f'c{i}') for i in range(20)]
    life=experiment_lifecycle(history)
    assert life['status'] == STATUS_PAUSED
    assert life['accepts_new_snapshots'] is False
    assert life['affects_production'] is False
    assert life['automatic_promotion'] is False
