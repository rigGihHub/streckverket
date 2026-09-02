from team_matching import TeamCandidate, normalize_team_name, similarity, match_team

def test_alias_man_utd():
    assert normalize_team_name('Man Utd') == 'manchester united'
    assert similarity('Man Utd', 'Manchester United FC') > .95

def test_spurs_alias():
    assert similarity('Spurs', 'Tottenham Hotspur FC') > .95

def test_high_confidence_requires_margin():
    c=[TeamCandidate(1,'Manchester United FC'),TeamCandidate(2,'Manchester City FC')]
    m=match_team('Man Utd',c)
    assert m.confidence == 'Hög'
    assert m.candidate.team_id == 1

def test_ambiguous_goes_to_review_or_none():
    c=[TeamCandidate(1,'Sheffield United FC'),TeamCandidate(2,'Sheffield Wednesday FC')]
    m=match_team('Sheffield',c)
    assert m.confidence in {'Granska','Ingen'}

def test_low_similarity_not_linked():
    c=[TeamCandidate(1,'Arsenal FC'),TeamCandidate(2,'Chelsea FC')]
    m=match_team('Real Sociedad',c)
    assert m.candidate is None
    assert m.confidence == 'Ingen'
