from types import SimpleNamespace

from evidence import make_signal
from match_intelligence import IntelligenceClaim, MatchIntelligenceCard
from source_consensus import DEFAULT_SOURCES, Observation
from signal_timeline import verified_facts_from_cards, dumps_signal_points, loads_signal_points, combined_timeline_rows


def _card(signals=(), claims=()):
    return MatchIntelligenceCard(
        match_number=1, home='Home', away='Away',
        base_market=(0.5,0.3,0.2), final_model=(0.5,0.3,0.2),
        claims=list(claims), used_signals=list(signals),
    )


def test_verified_injury_signal_preserves_observation_and_verification_times():
    sig = make_signal('injury_suspension','Verifierad spelarfrånvaro',(0.1,0,-0.1),0.9,'API-Football',
                      updated_at='2026-09-05T08:00:00+00:00', is_verified=True)
    points = verified_facts_from_cards([_card(signals=[sig])], coupon_key='abc', captured_at='2026-09-05T08:05:00+00:00')
    model_points=[p for p in points if p.verification_status == 'VERIFIERAD MODELLSIGNAL']
    assert len(model_points)==1
    assert model_points[0].observed_at == '2026-09-05T08:00:00+00:00'
    assert model_points[0].verified_at == '2026-09-05T08:05:00+00:00'
    assert model_points[0].model_usable is True


def test_direct_lineup_observation_is_not_upgraded_to_model_usable():
    obs=Observation('confirmed_lineup','confirmed',DEFAULT_SOURCES['api_football'],'2026-09-05T08:00:00+00:00',confidence=0.9,direct=True)
    claim=IntelligenceClaim('confirmed_lineup','confirmed_lineup',(obs,),None)
    points=verified_facts_from_cards([_card(claims=[claim])], coupon_key='abc', captured_at='2026-09-05T08:05:00+00:00')
    assert len(points)==1
    assert points[0].verification_status == 'LEVERANTÖRSBEKRÄFTAD'
    assert points[0].model_usable is False
    assert points[0].payload['verification_basis'] == 'direct_provider_observation'


def test_indirect_or_unrelated_claims_are_excluded():
    indirect=Observation('confirmed_lineup','confirmed',DEFAULT_SOURCES['api_football'],'2026-09-05T08:00:00+00:00',direct=False)
    unrelated=Observation('weather','rain',DEFAULT_SOURCES['open_meteo'],'2026-09-05T08:00:00+00:00',direct=True)
    cards=[_card(claims=[IntelligenceClaim('confirmed_lineup','confirmed_lineup',(indirect,),None), IntelligenceClaim('weather','weather',(unrelated,),None)])]
    assert verified_facts_from_cards(cards, coupon_key='abc', captured_at='2026-09-05T08:05:00+00:00') == []


def test_roundtrip_and_ui_keep_new_fact_metadata():
    obs=Observation('availability','11:Player X:out',DEFAULT_SOURCES['api_football'],'2026-09-05T08:00:00+00:00',confidence=0.78,direct=True)
    claim=IntelligenceClaim('availability','injury_suspension',(obs,),None)
    points=verified_facts_from_cards([_card(claims=[claim])], coupon_key='abc', captured_at='2026-09-05T08:05:00+00:00')
    restored=loads_signal_points(dumps_signal_points(points))
    assert restored[0].observed_at == points[0].observed_at
    rows=combined_timeline_rows([], restored, coupon_key='abc')
    assert rows[0]['Typ'] == 'Verifierat faktum · frånvaro'
    assert 'Player X' in rows[0]['Signal']
