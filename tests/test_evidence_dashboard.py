from evidence_dashboard import evidence_dashboard_rows, evidence_dashboard_summary, public_dashboard_rows


def timing(*, obs=30, matches=20, league='Premier League', source='API-Football', cat='injury_suspension'):
    return {
        'Signaltyp': cat, 'Liga': league, 'Källa': source,
        'Observationer': obs, 'Unika matcher': matches,
        'Säkert före': min(obs, 20), 'Osäker ordning': 0,
    }


def direction(*, obs=30, matches=20, same=70.0, league='Premier League', source='API-Football', cat='injury_suspension'):
    return {
        'Signaltyp': cat, 'Liga': league, 'Källa': source,
        'Riktningsobservationer': obs, 'Unika matcher': matches,
        'Andel samma riktning': same,
    }


def test_review_now_requires_both_sufficient_timing_and_direction():
    rows = evidence_dashboard_rows([timing()], [direction()])
    assert rows[0]['Status'] == 'GRANSKA NU'
    assert rows[0]['Prioritet'] == 'HÖG'
    assert rows[0]['Edge tillåten'] is False


def test_high_direction_rate_on_thin_data_does_not_raise_priority():
    rows = evidence_dashboard_rows([timing(obs=8, matches=8)], [direction(obs=8, matches=8, same=100.0)])
    assert rows[0]['Status'] == 'SAMLA MER DATA'
    assert rows[0]['Prioritet'] == 'VÄNTA'
    assert rows[0]['Saknar observationer'] == 22
    assert rows[0]['Saknar matcher'] == 12


def test_unknown_provenance_is_a_data_quality_issue_even_with_volume():
    rows = evidence_dashboard_rows(
        [timing(obs=50, matches=30, league='Okänd liga')],
        [direction(obs=40, matches=25, league='Okänd liga')],
    )
    assert rows[0]['Status'] == 'FIXA PROVENIENS'
    assert rows[0]['Prioritet'] == 'DATAKVALITET'


def test_timing_can_be_reviewable_while_direction_still_needs_data():
    rows = evidence_dashboard_rows([timing()], [direction(obs=12, matches=10)])
    assert rows[0]['Status'] == 'GRANSKA TIDSMÖNSTER'
    assert rows[0]['Prioritet'] == 'MEDEL'


def test_summary_and_public_rows_are_safe_for_ui():
    rows = evidence_dashboard_rows(
        [timing(), timing(obs=5, matches=5, cat='lineup')],
        [direction(), direction(obs=5, matches=5, cat='lineup')],
    )
    summary = evidence_dashboard_summary(rows)
    assert summary['segments'] == 2
    assert summary['review_now'] == 1
    assert summary['collect_more'] == 1
    assert summary['edge_claim_allowed'] is False
    assert all('_rank' not in row for row in public_dashboard_rows(rows))
