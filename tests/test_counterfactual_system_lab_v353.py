from dataclasses import replace
from demo_data import get_demo_matches
from budget_workshop import optimize_for_budget
from counterfactual_system_lab import snapshot_counterfactual_systems, counterfactual_summary, evaluate_counterfactual
from facit import make_coupon_snapshot, with_results, dumps_facit, loads_facit


def _snapshot():
    ms=get_demo_matches(); sys=optimize_for_budget(ms,128,'MAX 13',{})
    variants=snapshot_counterfactual_systems(ms,sys,budget=128,locks={})
    c=make_coupon_snapshot('c1',ms,sys['selections'],source='test',strategy='MAX 13',budget=128,rows=sys['rows'],model_coverage=sys['coverage'],counterfactual_systems=variants)
    return c, variants

def test_freezes_original_and_deduplicates():
    c,v=_snapshot(); assert v and v[0].label=='ORIGINAL'; assert len({x.selections for x in v})==len(v)

def test_json_roundtrip_variants():
    c,v=_snapshot(); loaded=loads_facit(dumps_facit([c]))[0]; assert loaded.counterfactual_systems==v

def test_legacy_stays_unknown_empty():
    c,v=_snapshot(); legacy=replace(c,counterfactual_systems=()); loaded=loads_facit(dumps_facit([legacy]))[0]; assert loaded.counterfactual_systems==()

def test_waits_for_complete_results():
    c,v=_snapshot(); r=evaluate_counterfactual(c,v[0]); assert not r.completed and r.system_hits is None

def test_evaluates_actual_hit_coverage():
    c,v=_snapshot(); results={m.match_number:'1' for m in c.matches}; c=with_results(c,results); r=evaluate_counterfactual(c,v[0]); assert r.completed and 0 <= r.system_hits <= 13

def test_summary_requires_20_per_variant():
    c,v=_snapshot(); results={m.match_number:'1' for m in c.matches}; done=with_results(c,results)
    rows=[replace(done,coupon_id=f'c{i}') for i in range(19)]
    s=counterfactual_summary(rows); assert all(x['status']=='FÖR LITE PROSPEKTIV HISTORIK' for x in s['variants'])

def test_summary_reviewable_at_20():
    c,v=_snapshot(); results={m.match_number:'1' for m in c.matches}; done=with_results(c,results)
    rows=[replace(done,coupon_id=f'c{i}') for i in range(20)]
    s=counterfactual_summary(rows); assert all(x['status']=='GRANSKNINGSBAR' for x in s['variants'])

def test_no_edge_claim():
    c,v=_snapshot(); assert counterfactual_summary([c])['edge_claim_allowed'] is False
