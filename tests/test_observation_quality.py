from core import MatchInput
from facit import make_coupon_snapshot, observation_quality_for_match, observation_quality_summary
from observation_quality import assess_observation_quality
from verification_engine import benchmark_against_market
from facit import with_results


def test_high_quality_observation_scores_high():
    q = assess_observation_quality(
        market_available=True,
        captured_at="2026-09-04T12:00:00+00:00",
        kickoff="2026-09-04T13:00:00+00:00",
        market_source="The Odds API",
        market_bookmaker_count=5,
        market_last_update="2026-09-04T11:50:00+00:00",
        market_match_confidence=1.0,
        public_last_update="2026-09-04T11:55:00+00:00",
    )
    assert q.score == 100
    assert q.label == "HÖG"
    assert q.evidence_coverage == 100
    assert not q.missing


def test_unknown_metadata_is_missing_not_invented():
    q = assess_observation_quality(
        market_available=True,
        captured_at="2026-09-04T12:00:00+00:00",
        kickoff=None,
    )
    assert q.score == 20
    assert q.label == "MYCKET LÅG"
    assert "marknadskälla" in q.missing
    assert "streckens färskhet" in q.missing


def _coupon(quality: bool):
    rows=[]
    for i in range(13):
        rows.append(MatchInput(
            i+1,"H","A",(2.0,3.5,4.0),(.5,.25,.25),(.55,.25,.20),
            kickoff="2026-09-04T13:00:00+00:00", market_available=True,
            market_source="The Odds API" if quality else "",
            market_bookmaker_count=5 if quality else None,
            market_last_update="2026-09-04T11:50:00+00:00" if quality else None,
            market_match_confidence=1.0 if quality else None,
            public_last_update="2026-09-04T11:55:00+00:00" if quality else None,
        ))
    c=make_coupon_snapshot("q" if quality else "legacy", rows, [("1",)]*13, source="test", strategy="MAX 13", budget=13, rows=1, model_coverage=.1, captured_at="2026-09-04T12:00:00+00:00")
    return with_results(c,{i:"1" for i in range(1,14)})


def test_snapshot_preserves_quality_provenance():
    c=_coupon(True)
    q=observation_quality_for_match(c.matches[0],c.captured_at)
    assert q.score == 100
    s=observation_quality_summary([c])
    assert s["high"] == 13


def test_quality_filter_is_explicit_and_does_not_change_default_benchmark():
    good=_coupon(True); legacy=_coupon(False)
    default=benchmark_against_market([good,legacy], min_sample=100)
    filtered=benchmark_against_market([good,legacy], min_sample=100, min_quality_score=60)
    assert default.matches == 26
    assert filtered.matches == 13
