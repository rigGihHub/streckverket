from core import MatchInput
from market_timeline import MarketPoint
from signal_timeline import SignalPoint, supporter_history_to_signal_points, deduplicate_signal_points, combined_timeline_rows
from history_store import SQLiteHistoryStore


def matches():
    return [MatchInput(i+1, f'H{i}', f'A{i}', (2.0,3.4,4.2), (0.48,0.30,0.22), (0.5,0.3,0.2), market_available=True) for i in range(13)]


def test_supporter_projection_is_non_model_usable():
    rows=[{'match_number':1,'home':'H0','away':'A0','team':'H0','captured_at':'2026-09-05T10:00:00+00:00','source':'r/test','confidence':.7,'worry':.2}]
    points=supporter_history_to_signal_points(rows,coupon_key='c',matches=matches())
    assert len(points)==1
    assert points[0].signal_type=='supporter_pulse'
    assert points[0].model_usable is False
    assert points[0].verification_status=='observerad_ton'


def test_signal_dedup_uses_stable_identity():
    p=SignalPoint('c',1,'A','B','2026-09-05T10:00:00+00:00','supporter_pulse','A','r/a','observerad_ton','r/a',False,{'confidence':.5})
    assert deduplicate_signal_points([p],[p]) == []


def test_sqlite_signal_roundtrip_and_dedup(tmp_path):
    store=SQLiteHistoryStore(str(tmp_path/'h.db'))
    p=SignalPoint('c',1,'A','B','2026-09-05T10:00:00+00:00','supporter_pulse','A','r/a','observerad_ton','r/a',False,{'confidence':.5})
    assert store.save_signal_points([p])==1
    assert store.save_signal_points([p])==0
    loaded=store.load_signal_points('c')
    assert len(loaded)==1 and loaded[0].payload['confidence']==.5


def test_combined_timeline_orders_market_and_signal():
    m=MarketPoint('c',1,'A','B','2026-09-05T10:00:00+00:00','2026-09-05T15:00:00+00:00',(0.5,.3,.2),True,'book')
    s=SignalPoint('c',1,'A','B','2026-09-05T09:00:00+00:00','supporter_pulse','A','r/a','observerad_ton','r/a',False,{'team':'A','confidence':.6,'worry':.1})
    rows=combined_timeline_rows([m],[s],coupon_key='c')
    assert [r['Typ'] for r in rows]==['Supporter Pulse','Bookmaker-marknad']
    assert rows[0]['Modellpåverkan']=='Nej'
