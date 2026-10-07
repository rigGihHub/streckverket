from fact_market_timing import (
    fact_market_timing_rows,
    first_observed_movement_interval,
    timing_evidence_summary,
)
from market_timeline import MarketPoint
from signal_timeline import SignalPoint


def mp(ts, market, n=1):
    return MarketPoint('c1', n, 'Home', 'Away', ts, '2026-09-05T14:00:00+00:00', market, True, 'Odds', 5, ts)


def fact(verified, *, status='VERIFIERAD MODELLSIGNAL', usable=True):
    return SignalPoint(
        coupon_key='c1', match_number=1, home='Home', away='Away', captured_at=verified,
        signal_type='verified_fact', subject='Spelarfrånvaro', source='API',
        verification_status=status, upstream_origin='api', model_usable=usable,
        payload={'category': 'injury_suspension'}, observed_at=verified, verified_at=verified,
    )


def test_first_movement_preserves_interval_uncertainty():
    series = [
        mp('2026-09-05T10:00:00+00:00', (0.50, 0.25, 0.25)),
        mp('2026-09-05T11:00:00+00:00', (0.505, 0.245, 0.25)),
        mp('2026-09-05T12:00:00+00:00', (0.52, 0.24, 0.24)),
    ]
    x = first_observed_movement_interval(series)
    assert x is not None
    assert x.interval_start.startswith('2026-09-05T11:00')
    assert x.interval_end.startswith('2026-09-05T12:00')
    assert x.strongest_outcome == '1'
    assert round(x.strongest_delta_pp, 1) == 2.0


def test_fact_before_interval_is_definitely_before():
    market = [mp('2026-09-05T10:00:00+00:00', (0.50,0.25,0.25)), mp('2026-09-05T12:00:00+00:00', (0.52,0.24,0.24))]
    rows = fact_market_timing_rows(market, [fact('2026-09-05T09:00:00+00:00')], coupon_key='c1')
    assert rows[0]['Tidsrelation'] == 'SÄKERT FÖRE RÖRELSEINTERVALL'
    assert rows[0]['Minsta försprång h'] == 1.0


def test_fact_inside_interval_is_ambiguous():
    market = [mp('2026-09-05T10:00:00+00:00', (0.50,0.25,0.25)), mp('2026-09-05T12:00:00+00:00', (0.52,0.24,0.24))]
    rows = fact_market_timing_rows(market, [fact('2026-09-05T11:00:00+00:00')], coupon_key='c1')
    assert rows[0]['Tidsrelation'] == 'INOM OSÄKERT RÖRELSEINTERVALL'


def test_direct_provider_observation_not_promoted_to_verified_fact_analysis():
    market = [mp('2026-09-05T10:00:00+00:00', (0.50,0.25,0.25)), mp('2026-09-05T12:00:00+00:00', (0.52,0.24,0.24))]
    rows = fact_market_timing_rows(market, [fact('2026-09-05T09:00:00+00:00', status='DIREKT LEVERANTÖRSUPPGIFT')], coupon_key='c1')
    assert rows == []


def test_summary_requires_30_before_any_review_status():
    row = {'Tidsrelation': 'SÄKERT FÖRE RÖRELSEINTERVALL'}
    small = timing_evidence_summary([row] * 29)
    enough = timing_evidence_summary([row] * 30)
    assert small['status'] == 'FÖR LITE DATA'
    assert enough['status'] == 'TILLRÄCKLIGT FÖR GRANSKNING'
    assert enough['edge_claim_allowed'] is False
