from core import MatchInput
from evidence import make_signal
from pipeline import ProviderOutput, run_match_pipeline, recommendation_change


def match():
    return MatchInput(1,'A','B',(2.0,3.5,4.0),(0.5,0.28,0.22),(0.5,0.28,0.22),kickoff='2026-09-05T14:00:00Z',competition='Test League')

def good_provider(m):
    return ProviderOutput('good',[make_signal('team_strength','edge',(0.4,0,-0.4),1.0,'test',is_verified=True)],message='ok',quality='Hög')
good_provider.provider_name='good'

def bad_provider(m):
    raise RuntimeError('source down')
bad_provider.provider_name='bad'

def test_provider_failure_is_isolated():
    r=run_match_pipeline(match(),[bad_provider,good_provider])
    assert 'bad' in r.failed_sources
    assert len(r.card.used_signals)==1
    assert abs(sum(r.enriched_match.model)-1)<1e-9

def test_metadata_survives_pipeline():
    r=run_match_pipeline(match(),[good_provider])
    assert r.enriched_match.kickoff=='2026-09-05T14:00:00Z'
    assert r.enriched_match.competition=='Test League'

def test_recommendation_change_detects_sign_flip():
    x=recommendation_change((.51,.25,.24),(.36,.25,.39))
    assert x['changed_sign'] and x['material']

def test_small_change_can_be_non_material():
    x=recommendation_change((.50,.30,.20),(.505,.297,.198),threshold_pp=2.0)
    assert not x['material']
