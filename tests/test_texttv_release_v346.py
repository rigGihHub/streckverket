from pathlib import Path
from release_info import APP_VERSION
from model_change_registry import get_model_change


def test_texttv_release_lineage_is_346_or_later():
    major, minor, patch = (int(x) for x in APP_VERSION.split("."))
    assert major == 3 and (minor, patch) >= (46, 0)


def test_346_is_non_predictive_change():
    c = get_model_change("3.46.0")
    assert c is not None
    assert c.predictive_change is False


def test_app_has_text_tv_identity_and_game_theory_view():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "STRECKVERKET TEXT-TV" in text
    assert "Spelteori: var trängs motspelarna?" in text
    assert "strategic_coupon_rows" in text
    assert "background:#000" in text
    assert "#ffff00" in text
    assert "#00ffff" in text
