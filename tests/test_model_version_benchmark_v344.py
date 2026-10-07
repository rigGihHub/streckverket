from dataclasses import replace
from datetime import datetime, timedelta, timezone

from core import MatchInput
from facit import make_coupon_snapshot, with_results
from model_version_benchmark import UNKNOWN_VERSION, group_coupons_by_model_version, model_version_benchmarks, public_version_rows


def _coupon(n: int, version: str, model=(.70,.20,.10)):
    captured=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=n)
    market=(.45,.30,.25)
    matches=[]
    for i in range(13):
        m=MatchInput(i+1,f'H{i}',f'A{i}',odds=tuple(1/p for p in market),public=(.5,.3,.2),model=model,market_available=True)
        m=replace(m,kickoff=(captured+timedelta(hours=2)).isoformat(),market_source='The Odds API',market_bookmaker_count=5,market_last_update=captured.isoformat(),market_match_confidence=.99)
        matches.append(m)
    c=make_coupon_snapshot(str(n),matches,[('1',)]*13,source='test',strategy='MAX13',budget=13,rows=1,model_coverage=.1,captured_at=captured.isoformat(),model_version=version)
    return with_results(c,{i:'1' for i in range(1,14)})


def test_versions_are_never_mixed():
    coupons=[_coupon(i,'3.43.0') for i in range(10)] + [_coupon(100+i,'3.44.0') for i in range(10)]
    rows=model_version_benchmarks(coupons,min_sample=100,min_coupons=20)
    assert {r.version for r in rows} == {'3.43.0','3.44.0'}
    assert all(r.matches == 130 for r in rows)
    assert all(r.coupons == 10 for r in rows)
    assert all(not r.comparable for r in rows)


def test_version_needs_own_20_coupons_before_comparable():
    rows=model_version_benchmarks([_coupon(i,'3.44.0') for i in range(20)],min_sample=100,min_coupons=20)
    assert len(rows)==1
    assert rows[0].matches==260 and rows[0].coupons==20
    assert rows[0].comparable is True


def test_unknown_legacy_version_is_isolated_and_never_comparable():
    groups=group_coupons_by_model_version([_coupon(1,''),_coupon(2,'3.44.0')])
    assert UNKNOWN_VERSION in groups
    rows=model_version_benchmarks([_coupon(i,'') for i in range(20)],min_sample=100,min_coupons=20)
    assert rows[0].version == UNKNOWN_VERSION
    assert rows[0].comparable is False
    assert 'saknar modellversion' in rows[0].summary


def test_public_rows_are_plain_swedish_and_explicit_about_comparability():
    rows=model_version_benchmarks([_coupon(i,'3.44.0') for i in range(2)],min_sample=100,min_coupons=20)
    public=public_version_rows(rows)[0]
    assert public['Jämförbar']=='NEJ'
    assert public['Modellversion']=='3.44.0'
    assert 'Minst 100 matcher och 20 kuponger' in public['Tolkning']
