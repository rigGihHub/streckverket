from core import MatchInput
from data_sources import aggregate_1x2_event
from market_intelligence_architecture import market_confidence, build_market_intelligence, texttv_market_pages_html
from facit import make_coupon_snapshot, dumps_facit, loads_facit


def event():
    bms=[]
    for name,odds in [('A',(2.0,3.5,4.0)),('B',(2.05,3.45,3.9)),('C',(2.02,3.55,3.95)),('OUT',(1.2,8.0,15.0))]:
        bms.append({'title':name,'markets':[{'key':'h2h','outcomes':[{'name':'Home','price':odds[0]},{'name':'Draw','price':odds[1]},{'name':'Away','price':odds[2]}]}]})
    return {'id':'e','home_team':'Home','away_team':'Away','bookmakers':bms}


def match(n=1):
    return MatchInput(n,f'H{n}',f'A{n}',(2,3.5,4),(.55,.25,.20),(.48,.28,.24),market_available=True,market_source='The Odds API',market_bookmaker_count=5,market_dispersion=.02,market_outliers=('OUT',),market_consensus_method='robust median fair-probability consensus')


def test_aggregate_preserves_consensus_diagnostics():
    a=aggregate_1x2_event(event())
    assert a and a['bookmaker_count']==4
    assert a['market_dispersion'] is not None
    assert 'OUT' in a['market_outliers']
    assert 'robust' in a['market_consensus_method']


def test_market_confidence_requires_real_dispersion():
    assert market_confidence(7,None)=='OTILLRÄCKLIG DATA'
    assert market_confidence(5,.02)=='HÖG'
    assert market_confidence(3,.04)=='NORMAL'
    assert market_confidence(3,.08)=='OENIG'


def test_intel_separates_public_and_model_gap():
    r=build_market_intelligence([match()])[0]
    assert r.public_sign=='1' and r.public_gap_pp>0
    assert r.model_sign in ('1','X','2')
    assert r.confidence=='HÖG'


def test_texttv_pages_are_diagnostic_not_edge_claim():
    html=texttv_market_pages_html([match(i) for i in range(1,14)])
    for page in ('560 MARKNAD','561 OENIGHET','563 STRECK vs MARKNAD','564 MODELL vs MARKNAD','566 KONFIDENS'):
        assert page in html
    assert 'INGEN NY MODELLVIKT' in html


def test_facit_roundtrip_market_consensus_provenance():
    ms=[match(i) for i in range(1,14)]
    c=make_coupon_snapshot('x',ms,[('1',)]*13,source='x',strategy='MAX 13',budget=1,rows=1,model_coverage=.1)
    c2=loads_facit(dumps_facit([c]))[0]
    m=c2.matches[0]
    assert m.market_dispersion==.02 and m.market_outliers==('OUT',)
    assert 'robust' in m.market_consensus_method
