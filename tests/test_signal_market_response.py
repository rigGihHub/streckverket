from signal_market_response import (
    signal_direction,
    classify_directional_response,
    signal_market_response_rows,
    directional_evidence_rows,
)


def base_row(i=1, *, impact=(0.2,0.0,-0.2), delta=(2.0,-0.5,-1.5), relation='SÄKERT FÖRE RÖRELSEINTERVALL'):
    return {
        'Kupong': f'c{i//13}', 'Nr': (i % 13)+1, 'Kategori': 'injury_suspension',
        'Liga': 'Premier League', 'Källa': 'API-Football', 'Tidsrelation': relation,
        'Signal-impact 1/X/2': impact, 'Marknadsdelta 1/X/2': delta,
    }


def test_signal_direction_comes_from_impact_not_category():
    d = signal_direction((-0.2, 0.0, 0.2))
    assert d is not None
    assert d['outcome'] in {'1','2'}
    assert d['label'] in {'1 ↓','2 ↑'}


def test_aligned_and_opposite_market_response():
    aligned = classify_directional_response((0.2,0,-0.2), (2.0,-0.5,-1.5))
    opposite = classify_directional_response((0.2,0,-0.2), (-2.0,0.5,1.5))
    assert aligned['status'] == 'SAMMA RIKTNING'
    assert opposite['status'] == 'MOTSATT RIKTNING'


def test_unknown_historical_direction_is_not_promoted():
    rows = signal_market_response_rows([base_row(impact=())])
    assert rows[0]['Marknadsrespons'] == 'RIKTNING OKÄND'
    assert rows[0]['Riktningsdata användbar'] is False


def test_ambiguous_timing_is_excluded_from_direction_response():
    assert signal_market_response_rows([base_row(relation='INOM OSÄKERT RÖRELSEINTERVALL')]) == []


def test_directional_evidence_requires_observations_and_unique_matches():
    rows = signal_market_response_rows([base_row(i) for i in range(30)])
    agg = directional_evidence_rows(rows, min_observations=30, min_unique_matches=20)
    assert len(agg) == 1
    assert agg[0]['Status'] == 'TILLRÄCKLIGT FÖR GRANSKNING'
    assert agg[0]['Andel samma riktning'] == 100.0
    assert agg[0]['Edge tillåten'] is False
    assert agg[0]['Orsakspåstående tillåtet'] is False
