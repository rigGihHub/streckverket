from core import MatchInput
from pipeline import run_match_pipeline
from run_history import serialize_run, append_run, load_runs, compare_latest

def test_run_store_roundtrip(tmp_path):
    m=MatchInput(1,'A','B',(2,3.5,4),(.5,.3,.2),(.5,.3,.2))
    run=serialize_run('c1',run_match_pipeline(m,[]) and [run_match_pipeline(m,[])])
    p=tmp_path/'runs.json'
    append_run(p,run)
    rows=load_runs(p)
    assert len(rows)==1 and rows[0]['coupon_id']=='c1'

def test_compare_latest_finds_material_move():
    a={'matches':[{'number':1,'home':'A','away':'B','model':[.50,.30,.20]}]}
    b={'matches':[{'number':1,'home':'A','away':'B','model':[.42,.30,.28]}]}
    out=compare_latest([a,b])
    assert len(out)==1 and out[0]['material']
