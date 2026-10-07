from dataclasses import replace
from datetime import datetime, timedelta, timezone

from core import MatchInput
from facit import dumps_facit, loads_facit, make_coupon_snapshot, with_results
from validation_reality import assess_validation_reality
from verification_engine import benchmark_against_market


def _coupon(n: int, *, version: str = "3.43.0"):
    market=(0.45,0.30,0.25); model=(0.70,0.20,0.10)
    matches=[]
    captured=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=n)
    for i in range(13):
        m=MatchInput(i+1,f"H{i}",f"A{i}",odds=tuple(1/p for p in market),public=(.5,.3,.2),model=model,market_available=True)
        m=replace(m,kickoff=(captured+timedelta(hours=2)).isoformat(),market_source="The Odds API",market_bookmaker_count=5,market_last_update=captured.isoformat(),market_match_confidence=.99)
        matches.append(m)
    c=make_coupon_snapshot(str(n),matches,[("1",)]*13,source="test",strategy="MAX13",budget=13,rows=1,model_coverage=.1,captured_at=captured.isoformat(),model_version=version)
    return with_results(c,{i:"1" for i in range(1,14)})


def test_100_matches_from_only_eight_coupons_is_not_lovande_anymore():
    coupons=[_coupon(i) for i in range(8)]
    r=benchmark_against_market(coupons,min_sample=100,min_coupons=20)
    assert r.matches == 104
    assert r.coupons == 8
    assert r.verdict == "FÖR LITE OBEROENDE HISTORIK"
    assert not r.coupon_diversity_ok


def test_positive_pattern_requires_coupon_diversity_and_recent_consistency():
    coupons=[_coupon(i) for i in range(20)]
    r=benchmark_against_market(coupons,min_sample=100,min_coupons=20)
    assert r.coupons == 20
    assert r.brier_gain > 0 and r.recent_brier_gain > 0
    assert r.verdict == "LOVANDE MÖNSTER"
    assert "inte bevisad edge" in r.plain_summary.lower()


def test_reality_check_surfaces_version_provenance_gap():
    coupons=[_coupon(i,version=("3.43.0" if i else "")) for i in range(20)]
    reality=assess_validation_reality(coupons,min_matches=100,min_coupons=20)
    assert reality.eligible_coupons == 20
    assert reality.unknown_version_coupons == 1
    assert "VERSIONSPROVENIENS" in reality.status
    assert reality.edge_claim_allowed is False


def test_model_version_roundtrips_and_legacy_is_unknown():
    c=_coupon(1,version="3.43.0")
    loaded=loads_facit(dumps_facit([c]))[0]
    assert loaded.model_version == "3.43.0"
    legacy=dumps_facit([c]).replace(',\n    "model_version": "3.43.0"','')
    loaded_legacy=loads_facit(legacy)[0]
    assert loaded_legacy.model_version == ""
