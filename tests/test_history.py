from history import make_snapshot, save_snapshots, load_snapshots
from demo_data import get_demo_matches

def test_snapshot_roundtrip(tmp_path):
    s=make_snapshot('x',get_demo_matches()[0],'demo','2026-09-01T10:00:00Z')
    p=tmp_path/'history.json'; save_snapshots(p,[s]); rows=load_snapshots(p)
    assert rows[0]['coupon_id']=='x' and rows[0]['match_number']==1
