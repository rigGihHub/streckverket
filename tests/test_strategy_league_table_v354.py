from dataclasses import replace

from counterfactual_system_lab import CounterfactualSystemSnapshot, snapshot_counterfactual_systems
from strategy_league_table import paired_matchups, strategy_coupon_results, strategy_league
from facit import make_coupon_snapshot, with_results, dumps_facit, loads_facit
from demo_data import get_demo_matches
from budget_workshop import optimize_for_budget


def _complete_coupon(cid='c1', variants=None, strategy='MAX 13', results=None):
    matches = get_demo_matches()
    system = optimize_for_budget(matches, 128, 'MAX 13', {})
    if variants is None:
        variants = snapshot_counterfactual_systems(matches, system, budget=128, locks={})
    c = make_coupon_snapshot(
        cid, matches, system['selections'], source='test', strategy=strategy,
        budget=128, rows=system['rows'], model_coverage=system['coverage'],
        counterfactual_systems=variants,
    )
    results = results or {m.match_number: '1' for m in c.matches}
    return with_results(c, results)


def test_snapshot_preserves_alias_when_strategy_outputs_are_identical():
    matches = get_demo_matches()
    system = optimize_for_budget(matches, 128, 'MAX 13', {})
    variants = snapshot_counterfactual_systems(matches, system, budget=128, locks={})
    original = variants[0]
    # The current system was produced with MAX 13, so if optimizer repeats it the
    # physical selection set remains one snapshot but the strategy name survives.
    if original.selections == tuple(tuple(x) for x in optimize_for_budget(matches,128,'MAX 13',{})['selections']):
        assert 'MAX 13' in original.aliases


def test_alias_json_roundtrip():
    base = CounterfactualSystemSnapshot('ORIGINAL','current_system',tuple((('1',),)*13),1,0.1,('MAX 13',))
    c = _complete_coupon(variants=(base,))
    loaded = loads_facit(dumps_facit([c]))[0]
    assert loaded.counterfactual_systems[0].aliases == ('MAX 13',)


def test_identical_aliases_create_real_tie():
    base = CounterfactualSystemSnapshot('ORIGINAL','current_system',tuple((('1',),)*13),1,0.1,('MAX 13','VÄRDE'))
    coupons = [_complete_coupon(f'c{i}', variants=(base,), strategy='MAX 13') for i in range(20)]
    match = next(m for m in paired_matchups(coupons) if {m.strategy_a,m.strategy_b} == {'MAX 13','VÄRDE'})
    assert match.shared_coupons == 20
    assert match.draws == 20 and match.matchup_result == 'OAVGJORT'


def test_no_result_before_20_shared_coupons():
    a = CounterfactualSystemSnapshot('A','test',tuple((('1',),)*13),1,0.1)
    b = CounterfactualSystemSnapshot('B','test',tuple((('1','X'),)*13),8192,0.2)
    coupons=[_complete_coupon(f'c{i}',variants=(a,b)) for i in range(19)]
    m=paired_matchups(coupons)[0]
    assert m.status == 'FÖR LITE GEMENSAM HISTORIK'
    assert m.matchup_result == 'INGET LIGARESULTAT'
    league=strategy_league(coupons)
    assert league['qualified_matchups'] == 0
    assert all(x['points'] == 0 for x in league['league'])


def test_pair_uses_only_shared_coupons():
    a = CounterfactualSystemSnapshot('A','test',tuple((('1',),)*13),1,0.1)
    b = CounterfactualSystemSnapshot('B','test',tuple((('1','X'),)*13),8192,0.2)
    both=[_complete_coupon(f'b{i}',variants=(a,b)) for i in range(20)]
    only_a=[_complete_coupon(f'a{i}',variants=(a,)) for i in range(25)]
    m=paired_matchups(both+only_a)[0]
    assert m.shared_coupons == 20


def test_qualified_pair_awards_league_points_from_paired_wins():
    a = CounterfactualSystemSnapshot('A','test',tuple((('1',),)*13),1,0.1)
    b = CounterfactualSystemSnapshot('B','test',tuple((('1','X'),)*13),8192,0.2)
    coupons=[]
    for i in range(20):
        results={n:('X' if n==1 else '1') for n in range(1,14)}
        coupons.append(_complete_coupon(f'c{i}',variants=(a,b),results=results))
    league=strategy_league(coupons)
    m=league['matchups'][0]
    assert m.matchup_result == 'B'
    rows={x['strategy']:x for x in league['league']}
    assert rows['B']['points'] == 3 and rows['A']['points'] == 0


def test_incomplete_coupon_is_excluded():
    matches=get_demo_matches(); system=optimize_for_budget(matches,128,'MAX 13',{})
    variants=snapshot_counterfactual_systems(matches,system,budget=128,locks={})
    c=make_coupon_snapshot('pending',matches,system['selections'],source='x',strategy='MAX 13',budget=128,rows=system['rows'],model_coverage=system['coverage'],counterfactual_systems=variants)
    assert strategy_coupon_results([c]) == []


def test_league_never_claims_roi_or_edge():
    s=strategy_league([])
    assert s['edge_claim_allowed'] is False and s['roi_claim_allowed'] is False
