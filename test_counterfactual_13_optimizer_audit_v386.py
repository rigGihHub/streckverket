from counterfactual_system_lab import CounterfactualSystemSnapshot
from facit import FacitCoupon, FacitMatch
from counterfactual_13_optimizer_audit import audit_coupon_optimizer, optimizer_audit_summary
from model_change_registry import get_model_change
from release_info import APP_VERSION

def _matches():
    return tuple(FacitMatch(i+1,f'H{i}',f'A{i}',(.6,.25,.15),(.58,.25,.17),(.55,.25,.20),('1',),result='1') for i in range(13))

def _coupon(cid='c', oc=.10, bc=.12):
    a=[('1',) for _ in range(13)]; a[0]=('1','X')
    b=[('1',) for _ in range(13)]; b[0]=('1',); b[1]=('1','X')
    original=CounterfactualSystemSnapshot('ORIGINAL','current_system',tuple(a),2,oc)
    best=CounterfactualSystemSnapshot('MAX13 ALT','optimizer:MAX 13',tuple(b),2,bc)
    return FacitCoupon(cid,'2026-09-11T10:00:00Z','Live','MAX 13',2,2,oc,_matches(),counterfactual_systems=(original,best))

def test_release_registered_non_predictive():
    assert tuple(map(int,APP_VERSION.split('.'))) >= (3,86,0)
    c=get_model_change('3.86.0'); assert c and c.predictive_change is False

def test_audit_classifies_structure_without_results_selection():
    a=audit_coupon_optimizer(_coupon()); assert a is not None
    assert a.guard_to_spike == 1 and a.spike_to_guard == 1
    assert a.changed_matches == 2
    assert abs(a.relative_uplift-.20)<1e-9

def test_more_expensive_candidate_is_excluded():
    c=_coupon(); big=CounterfactualSystemSnapshot('BIG','optimizer:MAX 13',tuple(('1','X') for _ in range(13)),8192,.95)
    c=FacitCoupon(c.coupon_id,c.captured_at,c.source,c.strategy,c.budget,c.rows,c.model_coverage,c.matches,counterfactual_systems=c.counterfactual_systems+(big,))
    assert audit_coupon_optimizer(c).best_label == 'MAX13 ALT'

def test_review_gate_requires_breadth():
    s=optimizer_audit_summary([_coupon(str(i)) for i in range(19)]); assert not s['review_ready']
    m=optimizer_audit_summary([_coupon(str(i)) for i in range(20)])
    assert m['review_ready'] and m['status']=='GRANSKA COUNTERFACTUAL MAX-13-STRUKTUR'
    assert m['selection_uses_results'] is False and m['automatic_strategy_change'] is False
