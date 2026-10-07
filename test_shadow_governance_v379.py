from facit import FacitCoupon, FacitMatch
from predictive_experiment import ShadowPrediction, MARKET_PULL_EXPERIMENT_ID
from shadow_governance import shadow_governance
from release_info import APP_VERSION
from model_change_registry import get_model_change


def _coupon(cid, candidate=(0.72,.18,.10), baseline=(0.65,.22,.13), market=(0.75,.15,.10), result='1'):
    pred=ShadowPrediction(MARKET_PULL_EXPERIMENT_ID,'candidate',candidate,'3.78.0','fixed')
    matches=tuple(FacitMatch(i+1,f'H{i}',f'A{i}',baseline,market,market,('1',),result=result,market_available=True,shadow_predictions=(pred,)) for i in range(13))
    return FacitCoupon(cid,'2026-09-10T00:00:00Z','Live','MAX 13',100,1,.1,matches,model_version='3.78.0')


def test_release_registered_and_non_predictive():
    assert tuple(int(x) for x in APP_VERSION.split('.')) >= (3, 79, 0)
    c=get_model_change('3.79.0')
    assert c is not None and c.predictive_change is False


def test_no_data_means_no_assessment():
    g=shadow_governance([])
    assert g['decision']=='INGEN BEDÖMNING'
    assert g['automatic_promotion'] is False
    assert g['engine_change_allowed'] is False


def test_small_sample_keeps_collecting():
    g=shadow_governance([_coupon('c1')])
    assert g['decision']=='FORTSÄTT SAMLA DATA'


def test_mature_bad_candidate_is_rejected():
    coupons=[_coupon(f'c{i}', candidate=(.50,.30,.20), baseline=(.75,.15,.10)) for i in range(20)]
    g=shadow_governance(coupons)
    assert g['promotion_ready'] is True
    assert g['decision']=='FÖRKASTA KANDIDATEN'


def test_broad_material_candidate_can_reach_manual_review_gate():
    coupons=[_coupon(f'c{i}', candidate=(.80,.12,.08), baseline=(.65,.22,.13)) for i in range(20)]
    g=shadow_governance(coupons)
    assert g['promotion_ready'] is True
    assert g['material_gain'] is True
    assert g['broad_gain'] is True
    assert g['concentration_ok'] is True
    assert g['decision']=='GODKÄND FÖR SEPARAT PRODUKTIONSKANDIDAT-GRANSKNING'
    assert g['automatic_promotion'] is False
