from types import SimpleNamespace

import analysis_controller as ac


def test_build_one_click_config_normalizes_input():
    cfg = ac.build_one_click_config(
        odds_api_key="  odds  ",
        football_data_key=" fd ",
        api_football_key=" af ",
        odds_sport_keys=[" soccer_epl ", "", "soccer_efl_champ"],
        odds_regions="  ",
        max_competitions=7,
    )
    assert cfg.odds_api_key == "odds"
    assert cfg.football_data_key == "fd"
    assert cfg.api_football_key == "af"
    assert cfg.odds_sport_keys == ("soccer_epl", "soccer_efl_champ")
    assert cfg.odds_regions == "uk,eu"
    assert cfg.max_competitions == 7


def test_build_one_click_config_uses_default_sports_when_empty():
    cfg = ac.build_one_click_config(odds_sport_keys=[])
    assert cfg.odds_sport_keys == ac.DEFAULT_ODDS_SPORT_KEYS


def test_execute_one_click_returns_shared_state_payload(monkeypatch):
    enriched = [
        SimpleNamespace(number=1, home="A", away="B", public=(.5,.3,.2), odds=(2.0,3.0,4.0), market_available=True)
    ]
    fake_result = SimpleNamespace(enriched=enriched)
    seen = {}

    def fake_run(config, coupon, fetch_coupon):
        seen["config"] = config
        seen["coupon"] = coupon
        seen["fetch_coupon"] = fetch_coupon
        return fake_result

    monkeypatch.setattr(ac, "run_one_click", fake_run)
    cfg = ac.build_one_click_config()
    coupon = ["coupon"]
    execution = ac.execute_one_click(cfg, coupon=coupon, fetch_coupon=True)

    assert execution.result is fake_result
    assert execution.duration_seconds is not None
    assert execution.duration_seconds >= 0
    assert execution.coupon_fingerprint
    assert seen == {"config": cfg, "coupon": coupon, "fetch_coupon": True}
