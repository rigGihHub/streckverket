from claim_resolution import ClaimRecord, resolve_claim, information_edge_label, summarize_information_edge

def rec(**kw):
    base=dict(claim_id='c1',source_key='Reporter A',topic='lineup',subject='Player A',predicted_value='starts',published_at='2026-09-01T16:00:00Z',market_reaction_at='2026-09-01T18:30:00Z',public_reaction_at='2026-09-01T18:45:00Z')
    base.update(kw); return ClaimRecord(**base)

def test_resolution_correctness_and_edges():
    r=resolve_claim(rec(),'starts','2026-09-01T19:00:00Z'); assert r.correct; assert r.information_edge_market_minutes==150; assert r.information_edge_public_minutes==165

def test_wrong_claim_not_edge_sample():
    r=resolve_claim(rec(),'bench','2026-09-01T19:00:00Z'); s=summarize_information_edge([r]); assert s['correct_claims']==0; assert s['market_edge_samples']==0

def test_edge_labels():
    assert information_edge_label(200)=='Mycket tidig'; assert information_edge_label(80)=='Tidig'; assert information_edge_label(20)=='Liten edge'; assert information_edge_label(2)=='Samtidigt'; assert information_edge_label(-10)=='Efter marknaden'

def test_missing_reaction_safe():
    r=resolve_claim(rec(market_reaction_at=None),'starts','2026-09-01T19:00:00Z'); assert r.information_edge_market_minutes is None

def test_summary_correct_only():
    a=resolve_claim(rec(claim_id='a'),'starts','2026-09-01T19:00:00Z'); b=resolve_claim(rec(claim_id='b',published_at='2026-09-01T17:00:00Z'),'starts','2026-09-01T19:00:00Z'); c=resolve_claim(rec(claim_id='c'),'bench','2026-09-01T19:00:00Z'); s=summarize_information_edge([a,b,c]); assert s['resolved_claims']==3; assert s['correct_claims']==2; assert s['avg_market_edge_minutes']==120.0
