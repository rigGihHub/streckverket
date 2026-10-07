from counterfactual_system_lab import CounterfactualSystemSnapshot
from facit import FacitCoupon, FacitMatch
from model_change_registry import get_model_change
from release_info import APP_VERSION
from system_p13_audit import audit_coupon, system_p13_summary


def _matches(result='1'):
    return tuple(FacitMatch(i+1,f'H{i}',f'A{i}',(.60,.25,.15),(.58,.25,.17),(.55,.25,.20),('1',),result=result) for i in range(13))


def _coupon(cid='c', original_cov=.10, best_cov=.12, complete=True):
    original=CounterfactualSystemSnapshot('ORIGINAL','current_system',tuple((('1',) if i else ('1','X')) for i in range(13)),64,original_cov)
    best=CounterfactualSystemSnapshot('MAX 13','optimizer:MAX 13',tuple((('1',) if i != 1 else ('1','X')) for i in range(13)),64,best_cov)
    ms=_matches('1') if complete else tuple(list(_matches('1'))[:-1]+[FacitMatch(13,'H12','A12',(.6,.25,.15),(.58,.25,.17),(.55,.25,.20),('1',),result=None)])
    return FacitCoupon(cid,'2026-09-11T10:00:00Z','Live','VÄRDE',128,64,original_cov,ms,counterfactual_systems=(original,best))


def test_release_registered_non_predictive():
    assert tuple(map(int, APP_VERSION.split('.'))) >= (3,83,0)
    c=get_model_change('3.83.0')
    assert c and c.predictive_change is False


def test_audit_uses_only_frozen_variants_and_finds_p13_headroom():
    a=audit_coupon(_coupon())
    assert a is not None
    assert a.best_label == 'MAX 13'
    assert abs(a.coverage_delta_pp - 2.0) < 1e-9
    assert abs(a.relative_uplift - .20) < 1e-9
    assert a.selections_changed == 2


def test_coupon_without_prospective_variants_is_not_reconstructed():
    c=FacitCoupon('legacy','2026-09-01T00:00:00Z','Live','MAX 13',128,64,.1,_matches())
    assert audit_coupon(c) is None
    s=system_p13_summary([c])
    assert s['auditable_coupons'] == 0
    assert s['legacy_without_frozen_variants'] == 1


def test_review_gate_requires_breadth_before_allocation_conclusion():
    small=system_p13_summary([_coupon(f'c{i}') for i in range(19)])
    assert small['review_ready'] is False
    assert small['status'] == 'SAMLA MER PROSPEKTIV HISTORIK'
    mature=system_p13_summary([_coupon(f'c{i}') for i in range(20)])
    assert mature['review_ready'] is True
    assert mature['status'] == 'GRANSKA SYSTEM-/BUDGETALLOKERING'
    assert mature['optimization_uses_results'] is False
    assert mature['automatic_strategy_change'] is False


def test_malformed_over_budget_variant_cannot_win():
    c=_coupon()
    huge=CounterfactualSystemSnapshot('FÖR STORT','bad',tuple(('1','X','2') for _ in range(13)),256,.99)
    c=FacitCoupon(c.coupon_id,c.captured_at,c.source,c.strategy,c.budget,c.rows,c.model_coverage,c.matches,counterfactual_systems=c.counterfactual_systems+(huge,))
    a=audit_coupon(c)
    assert a and a.best_label == 'MAX 13'
