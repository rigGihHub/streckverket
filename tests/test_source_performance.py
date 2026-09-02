from source_performance import SourceObservation, evaluate_source, adjusted_reliability


def obs(source, topic, pred, actual, independent=True, published="2026-09-01T12:00:00Z", resolved="2026-09-01T18:00:00Z"):
    return SourceObservation(
        source_key=source,
        topic=topic,
        predicted_value=pred,
        actual_value=actual,
        published_at=published,
        resolved_at=resolved,
        independent=independent,
    )


def test_small_sample_is_shrunk():
    p = evaluate_source([obs("a","lineup","starts","starts")])[0]
    assert p.accuracy == 1.0
    assert p.shrunk_accuracy < 0.9


def test_good_source_gets_positive_but_bounded_multiplier():
    items = [obs("a","injury","out","out") for _ in range(30)]
    p = evaluate_source(items)[0]
    assert p.reliability_multiplier > 1.0
    assert p.reliability_multiplier <= 1.22


def test_bad_source_is_downweighted():
    items = [obs("a","injury","out","fit") for _ in range(30)]
    p = evaluate_source(items)[0]
    assert p.reliability_multiplier < 1.0
    assert p.reliability_multiplier >= 0.78


def test_timeliness_matters_but_cannot_rescue_wrong_source():
    early_wrong = [
        obs("a","lineup","starts","bench", published="2026-09-01T08:00:00Z", resolved="2026-09-01T18:00:00Z")
        for _ in range(25)
    ]
    late_right = [
        obs("b","lineup","starts","starts", published="2026-09-01T17:30:00Z", resolved="2026-09-01T18:00:00Z")
        for _ in range(25)
    ]
    pa = evaluate_source(early_wrong)[0]
    pb = evaluate_source(late_right)[0]
    assert pb.performance_score > pa.performance_score


def test_independent_reporting_scores_above_republishing_all_else_equal():
    independent = [obs("a","injury","out","out", independent=True) for _ in range(20)]
    copied = [obs("b","injury","out","out", independent=False) for _ in range(20)]
    pa = evaluate_source(independent)[0]
    pb = evaluate_source(copied)[0]
    assert pa.performance_score > pb.performance_score


def test_adjusted_reliability_stays_in_bounds():
    p = evaluate_source([obs("a","injury","out","out") for _ in range(100)])[0]
    x = adjusted_reliability(0.98, p)
    assert 0 <= x <= 1
