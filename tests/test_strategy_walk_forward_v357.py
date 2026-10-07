from dataclasses import replace
from datetime import datetime, timedelta, timezone

from core import MatchInput
from facit import make_coupon_snapshot, with_results
from counterfactual_system_lab import CounterfactualSystemSnapshot
from strategy_walk_forward import walk_forward_validation


def _coupon(i, a_hits, b_hits, *, captured=True):
    matches=[]
    results={}
    for n in range(1,14):
        matches.append(MatchInput(number=n, home=f'H{n}', away=f'A{n}', odds=(2.0,4.0,4.0), public=(.55,.25,.20), model=(.5,.25,.25)))
        results[n]='1'
    sel_a=tuple((('1',) if n <= a_hits else ('2',)) for n in range(1,14))
    sel_b=tuple((('1',) if n <= b_hits else ('2',)) for n in range(1,14))
    vars=(
        CounterfactualSystemSnapshot('A','test',sel_a,rows=1,model_coverage=.1),
        CounterfactualSystemSnapshot('B','test',sel_b,rows=1,model_coverage=.1),
    )
    ts=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=i)).isoformat() if captured else ''
    c=make_coupon_snapshot(f'c{i}', matches, sel_a, source='test', strategy='A', budget=1, rows=1, model_coverage=.1, captured_at=ts or None, counterfactual_systems=vars)
    c=with_results(c, results)
    return c if captured else replace(c, captured_at='')


def test_future_results_do_not_affect_first_train_choice():
    coupons=[_coupon(i, 10, 9) for i in range(30)] + [_coupon(i, 8, 12) for i in range(30,40)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=10)
    f=r['folds'][0]
    assert f.selected_strategy == 'A'
    assert f.test_losses_selected == 10


def test_exactly_30_plus_10_creates_one_fold():
    coupons=[_coupon(i, 10, 9) for i in range(40)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=20)
    p=r['pairs'][0]
    assert p.folds == 1
    assert p.oos_coupons == 10
    assert p.status == 'FÖR LITE WALK-FORWARD-HISTORIK'


def test_two_test_blocks_are_reviewable():
    coupons=[_coupon(i, 10, 9) for i in range(50)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=20)
    p=r['pairs'][0]
    assert p.folds == 2
    assert p.oos_coupons == 20
    assert p.status != 'FÖR LITE WALK-FORWARD-HISTORIK'


def test_training_tie_does_not_force_alphabetical_strategy():
    coupons=[_coupon(i, 10, 10) for i in range(30)] + [_coupon(i, 13, 1) for i in range(30,40)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=10)
    f=r['folds'][0]
    assert f.selected_strategy.startswith('INGET VAL')
    assert r['pairs'][0].oos_coupons == 0


def test_missing_capture_time_is_excluded_not_sorted_by_id():
    coupons=[_coupon(i,10,9) for i in range(40)] + [_coupon(99,13,1,captured=False)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=10)
    assert r['chronological_coupons'] == 40
    assert r['excluded_without_valid_chronology'] >= 1


def test_strong_later_performance_can_signal_but_never_edge():
    coupons=[_coupon(i, 10, 9) for i in range(70)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=20)
    p=r['pairs'][0]
    assert p.oos_wins_selected == 40
    assert p.holm_p is not None and p.holm_p <= .05
    assert 'SIGNAL' in p.status
    assert r['edge_claim_allowed'] is False
    assert r['roi_claim_allowed'] is False
    assert r['automatic_strategy_change_allowed'] is False


def test_walk_forward_uses_only_full_test_blocks():
    coupons=[_coupon(i,10,9) for i in range(45)]
    r=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=10)
    assert r['pairs'][0].folds == 1
    assert r['pairs'][0].oos_coupons == 10


def test_chronology_not_input_order():
    coupons=[_coupon(i,10,9) for i in range(40)]
    r1=walk_forward_validation(coupons, min_train=30, test_block=10, min_oos=10)
    r2=walk_forward_validation(list(reversed(coupons)), min_train=30, test_block=10, min_oos=10)
    assert r1['pairs'][0].oos_wins_selected == r2['pairs'][0].oos_wins_selected
    assert r1['folds'][0].test_start_coupon_id == r2['folds'][0].test_start_coupon_id
