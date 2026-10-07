from market_timeline import MarketPoint
from pre_kickoff_market_quality import compare_snapshot_to_late_market, latest_verified_pre_kickoff, pre_kickoff_timing, quality_rows


def p(t, market=(.5,.3,.2), available=True, count=5):
    return MarketPoint('c',1,'A','B',t,'2026-09-07T18:00:00+00:00',market,available,'book',count,None)


def test_timing_labels_are_conservative():
    assert pre_kickoff_timing(30) == 'MYCKET NÄRA'
    assert pre_kickoff_timing(120) == 'NÄRA'
    assert pre_kickoff_timing(240) == 'TIDIG'
    assert pre_kickoff_timing(-1) == 'OKÄND'


def test_latest_point_is_verified_and_pre_kickoff_only():
    pts=[p('2026-09-07T15:00:00+00:00'), p('2026-09-07T17:30:00+00:00',(.55,.27,.18)), p('2026-09-07T17:50:00+00:00',available=False), p('2026-09-07T18:01:00+00:00')]
    got=latest_verified_pre_kickoff(pts,coupon_key='c',match_number=1)
    assert got.captured_at == '2026-09-07T17:30:00+00:00'


def test_compare_reports_real_delta_and_model_alignment_without_ev_claim():
    snap=p('2026-09-07T15:00:00+00:00')
    late=p('2026-09-07T17:30:00+00:00',(.55,.27,.18))
    row=compare_snapshot_to_late_market(snap,[snap,late],model=(.60,.25,.15))
    assert row.timing == 'MYCKET NÄRA'
    assert tuple(round(x, 1) for x in row.deltas_pp) == (5.0, -3.0, -2.0)
    assert row.largest_sign == '1'
    assert row.moved_toward_model is True
    assert round(row.model_alignment_change_pp, 1) == 5.0


def test_no_kickoff_or_post_kickoff_snapshot_is_not_fabricated():
    bad=MarketPoint('c',1,'A','B','2026-09-07T18:01:00+00:00','2026-09-07T18:00:00+00:00',(.5,.3,.2),True,'book',5,None)
    assert compare_snapshot_to_late_market(bad,[bad]) is None


def test_quality_rows_uses_earliest_verified_point_as_live_timeline_baseline():
    pts=[p('2026-09-07T14:00:00+00:00'),p('2026-09-07T17:00:00+00:00',(.52,.29,.19))]
    rows=quality_rows(pts,coupon_key='c',models={1:(.55,.28,.17)})
    assert len(rows)==1
    assert rows[0].latest_at.endswith('17:00:00+00:00')
