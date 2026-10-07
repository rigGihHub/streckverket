from dataclasses import replace

from analysis_refresh import coupon_fixture_signature, same_coupon_fixtures, choose_refresh_coupon
from analysis_controller import build_one_click_config
from demo_data import get_demo_matches
from api_cache import CachePolicy, cached_call, clear_cache, clear_cache_policies, cache_stats


def _coupon():
    return list(get_demo_matches())


def test_same_coupon_fixtures_ignores_changeable_probabilities():
    left = _coupon()
    right = [replace(m, public=(0.50, 0.25, 0.25)) for m in left]
    assert same_coupon_fixtures(left, right)
    assert coupon_fixture_signature(left) == coupon_fixture_signature(right)


def test_refresh_never_switches_to_different_fixture_set():
    current = _coupon()
    fetched = _coupon()
    fetched[0] = replace(fetched[0], home="Helt annat lag")
    choice = choose_refresh_coupon(current, fetched)
    assert choice.used_fresh_coupon is False
    assert choice.coupon[0].home == current[0].home
    assert "byter aldrig matchuppsättning" in choice.message


def test_refresh_uses_fresh_values_for_same_fixture_set():
    current = _coupon()
    fetched = [replace(m, public=(0.52, 0.24, 0.24)) for m in current]
    choice = choose_refresh_coupon(current, fetched)
    assert choice.used_fresh_coupon is True
    assert choice.coupon[0].public == (0.52, 0.24, 0.24)


def test_force_live_refresh_is_explicit_in_one_click_config():
    config = build_one_click_config(force_live_refresh=True)
    assert config.force_live_refresh is True


def test_selected_cache_policy_can_be_invalidated_without_clearing_others():
    clear_cache()
    calls = {"odds": 0, "meta": 0}

    def odds_loader():
        calls["odds"] += 1
        return calls["odds"]

    def meta_loader():
        calls["meta"] += 1
        return calls["meta"]

    odds = CachePolicy("odds", 999)
    meta = CachePolicy("competitions", 999)
    assert cached_call(odds, "x", odds_loader) == 1
    assert cached_call(meta, "x", meta_loader) == 1
    assert cached_call(odds, "x", odds_loader) == 1
    assert cached_call(meta, "x", meta_loader) == 1

    removed = clear_cache_policies(("odds", "fixtures"))
    assert removed == 1
    assert cached_call(odds, "x", odds_loader) == 2
    assert cached_call(meta, "x", meta_loader) == 1
