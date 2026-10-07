from counterfactual_system_lab import CounterfactualSystemSnapshot
from facit import FacitCoupon, FacitMatch
from guard_allocation_lab import audit_coupon_guard_allocation, guard_allocation_summary
from model_change_registry import get_model_change
from release_info import APP_VERSION


def _matches():
    return tuple(FacitMatch(i+1, f'H{i}', f'A{i}', (.60,.25,.15), (.58,.25,.17), (.55,.25,.20), ('1',), result='1') for i in range(13))


def _coupon(cid='c', original_cov=.10, best_cov=.12):
    original_sels=[('1',) for _ in range(13)]
    original_sels[0]=('1','X')
    best_sels=[('1',) for _ in range(13)]
    best_sels[1]=('1','X')
    original=CounterfactualSystemSnapshot('ORIGINAL','current_system',tuple(original_sels),2,original_cov)
    best=CounterfactualSystemSnapshot('BÄSTA SWAP','budget_reallocation',tuple(best_sels),2,best_cov)
    return FacitCoupon(cid,'2026-09-11T10:00:00Z','Live','MAX 13',2,2,original_cov,_matches(),counterfactual_systems=(original,best))


def test_release_registered_non_predictive():
    assert tuple(map(int, APP_VERSION.split('.'))) >= (3,85,0)
    c=get_model_change('3.85.0')
    assert c and c.predictive_change is False


def test_guard_audit_requires_same_rows_and_detects_relocation():
    a=audit_coupon_guard_allocation(_coupon())
    assert a is not None
    assert a.guard_additions == 1
    assert a.guard_removals == 1
    assert a.changed_matches == 2
    assert abs(a.relative_uplift - .20) < 1e-9


def test_more_expensive_variant_is_not_used_for_allocation_claim():
    c=_coupon()
    bigger=CounterfactualSystemSnapshot('STÖRRE','optimizer:MAX 13',tuple(('1','X') for _ in range(13)),8192,.9)
    c=FacitCoupon(c.coupon_id,c.captured_at,c.source,c.strategy,c.budget,c.rows,c.model_coverage,c.matches,counterfactual_systems=c.counterfactual_systems+(bigger,))
    a=audit_coupon_guard_allocation(c)
    assert a is not None
    assert a.best_label == 'BÄSTA SWAP'


def test_no_same_row_alternative_is_not_reconstructed():
    c=_coupon()
    original=c.counterfactual_systems[0]
    c=FacitCoupon(c.coupon_id,c.captured_at,c.source,c.strategy,c.budget,c.rows,c.model_coverage,c.matches,counterfactual_systems=(original,))
    assert audit_coupon_guard_allocation(c) is None


def test_review_gate_requires_breadth_before_guard_allocation_conclusion():
    small=guard_allocation_summary([_coupon(f'c{i}') for i in range(19)])
    assert small['review_ready'] is False
    assert small['status'] == 'SAMLA MER PROSPEKTIV GARDERINGSHISTORIK'
    mature=guard_allocation_summary([_coupon(f'c{i}') for i in range(20)])
    assert mature['review_ready'] is True
    assert mature['status'] == 'GRANSKA GARDERINGSALLOKERING'
    assert mature['selection_uses_results'] is False
    assert mature['automatic_strategy_change'] is False
