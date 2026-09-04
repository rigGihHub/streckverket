from api_cache import CachePolicy, cached_call, cache_stats, clear_cache


def test_cached_call_avoids_duplicate_loader_calls():
    clear_cache(); calls=[]
    def loader():
        calls.append(1); return {"ok": True}
    policy=CachePolicy("x",60)
    assert cached_call(policy,"same",loader)=={"ok": True}
    assert cached_call(policy,"same",loader)=={"ok": True}
    assert len(calls)==1
    stats=cache_stats()
    assert stats.network_calls==1
    assert stats.cache_hits==1


def test_failed_loader_is_not_cached():
    clear_cache(); calls=[]
    def loader():
        calls.append(1)
        if len(calls)==1: raise RuntimeError("boom")
        return 7
    policy=CachePolicy("x",60)
    try: cached_call(policy,"same",loader)
    except RuntimeError: pass
    assert cached_call(policy,"same",loader)==7
    assert len(calls)==2
