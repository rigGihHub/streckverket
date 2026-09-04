from dataclasses import dataclass
import time

from production_hardening import coupon_fingerprint, analysis_matches_coupon, Timer


@dataclass
class M:
    number: int
    home: str
    away: str
    public: tuple
    odds: tuple
    market_available: bool = True


def _coupon():
    return [M(1, "A", "B", (0.5, 0.3, 0.2), (2.0, 3.2, 4.0))]


def test_fingerprint_is_stable_for_same_coupon():
    assert coupon_fingerprint(_coupon()) == coupon_fingerprint(_coupon())


def test_fingerprint_changes_when_public_changes():
    a = _coupon()
    b = _coupon()
    b[0].public = (0.51, 0.29, 0.20)
    assert coupon_fingerprint(a) != coupon_fingerprint(b)


def test_fingerprint_changes_when_market_availability_changes():
    a = _coupon()
    b = _coupon()
    b[0].market_available = False
    assert coupon_fingerprint(a) != coupon_fingerprint(b)


def test_analysis_matches_coupon_requires_exact_fingerprint():
    c = _coupon()
    fp = coupon_fingerprint(c)
    assert analysis_matches_coupon(fp, c)
    assert not analysis_matches_coupon(None, c)


def test_timer_records_non_negative_duration():
    with Timer("x") as t:
        time.sleep(0.001)
    assert t.result is not None
    assert t.result.seconds >= 0
