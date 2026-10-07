from repeated_signal_evidence import repeated_signal_evidence_rows, repeated_signal_summary


def row(i, *, cat='injury_suspension', league='Premier League', source='API-Football', relation='SÄKERT FÖRE RÖRELSEINTERVALL'):
    return {
        'Kupong': f'c{i//13}', 'Nr': (i % 13) + 1, 'Kategori': cat, 'Liga': league, 'Källa': source,
        'Tidsrelation': relation,
    }


def test_mixed_leagues_do_not_combine_to_reach_threshold():
    rows = [row(i, league='Premier League') for i in range(15)] + [row(100+i, league='Championship') for i in range(15)]
    out = repeated_signal_evidence_rows(rows, min_observations=30, min_unique_matches=10)
    assert len(out) == 2
    assert all(r['Status'] == 'FÖR LITE DATA' for r in out)


def test_mixed_sources_do_not_combine():
    rows = [row(i, source='A') for i in range(20)] + [row(100+i, source='B') for i in range(20)]
    out = repeated_signal_evidence_rows(rows, min_observations=30, min_unique_matches=10)
    assert len(out) == 2
    assert all(r['Status'] == 'FÖR LITE DATA' for r in out)


def test_repeated_same_match_cannot_create_evidence():
    rows = []
    for i in range(30):
        r = row(i)
        r['Kupong'] = 'same'
        r['Nr'] = 1
        rows.append(r)
    out = repeated_signal_evidence_rows(rows, min_observations=30, min_unique_matches=20)
    assert out[0]['Observationer'] == 30
    assert out[0]['Unika matcher'] == 1
    assert out[0]['Status'] == 'FÖR LITE DATA'


def test_homogeneous_segment_can_be_reviewable_but_never_edge_claim():
    rows = [row(i) for i in range(30)]
    out = repeated_signal_evidence_rows(rows, min_observations=30, min_unique_matches=20)
    assert out[0]['Status'] == 'TILLRÄCKLIGT FÖR GRANSKNING'
    assert out[0]['Edge tillåten'] is False
    summary = repeated_signal_summary(out)
    assert summary['reviewable_segments'] == 1
    assert summary['edge_claim_allowed'] is False


def test_ambiguous_rows_not_counted_as_before():
    rows = [row(i, relation='INOM OSÄKERT RÖRELSEINTERVALL') for i in range(30)]
    out = repeated_signal_evidence_rows(rows, min_observations=30, min_unique_matches=20)
    assert out[0]['Säkert före'] == 0
    assert out[0]['Osäker ordning'] == 30
    assert out[0]['Andel före (avgörbar ordning)'] is None
