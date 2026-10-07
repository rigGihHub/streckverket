from facit import FacitCoupon, FacitMatch
from predictive_experiment import ShadowPrediction, MARKET_PULL_EXPERIMENT_ID
from experiment_cohorts import cohort_robustness
from release_info import APP_VERSION
from model_change_registry import get_model_change

def _coupon(cid,candidate=(.80,.12,.08),baseline=(.65,.22,.13),market=(.75,.15,.10),result='1'):
    pred=ShadowPrediction(MARKET_PULL_EXPERIMENT_ID,'candidate',candidate,'3.78.0','fixed')
    ms=tuple(FacitMatch(i+1,f'H{i}',f'A{i}',baseline,market,market,('1',),result=result,market_available=True,shadow_predictions=(pred,)) for i in range(13))
    return FacitCoupon(cid,'2026-09-10T00:00:00Z','Live','MAX 13',100,1,.1,ms,model_version='3.80.0')

def test_release_registered_non_predictive():
    assert tuple(map(int,APP_VERSION.split('.'))) >= (3,81,0)
    c=get_model_change('3.81.0'); assert c and c.predictive_change is False

def test_small_sample_not_judged():
    r=cohort_robustness([_coupon('a')]); assert r['status']=='MER DATA KRÄVS'; assert r['production_effect'] is False

def test_mature_positive_segments_are_visible():
    r=cohort_robustness([_coupon(f'c{i}') for i in range(5)])
    assert r['mature_cohorts'] >= 3
    assert not r['worse_cohorts']
    assert any(x['Bedömning']=='KANDIDAT BÄTTRE' for x in r['rows'] if x['Mogen'])

def test_mature_bad_candidate_warns():
    r=cohort_robustness([_coupon(f'c{i}',candidate=(.45,.35,.20),baseline=(.75,.15,.10)) for i in range(5)])
    assert r['status']=='ROBUSTHETSVARNING'; assert r['worse_cohorts']>0
