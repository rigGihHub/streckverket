from enrichment import summarize_team_form, form_signal_from_summaries

def match(home_id,away_id,hg,ag,date):
    return {'utcDate':date,'homeTeam':{'id':home_id},'awayTeam':{'id':away_id},'score':{'fullTime':{'home':hg,'away':ag}}}

def test_summarize_home_form():
    ms=[match(1,2,2,0,'2026-01-01'),match(1,3,1,1,'2026-01-08'),match(1,4,0,1,'2026-01-15')]
    s=summarize_team_form(ms,1)
    assert s['played']==3
    assert 1.2 < s['ppg'] < 1.5
    assert s['weighted_ppg'] < s['ppg']  # senaste förlust får större vikt

def test_form_signal_is_conservative():
    home={'played':10,'weighted_ppg':2.2,'weighted_gd_pg':1.0}
    away={'played':10,'weighted_ppg':0.8,'weighted_gd_pg':-0.7}
    sig=form_signal_from_summaries(home,away)
    assert sig.is_verified
    assert sig.impact[0] > sig.impact[2]
    assert sig.effective_strength < 1
