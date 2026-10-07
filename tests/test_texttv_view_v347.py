from types import SimpleNamespace
from texttv_view import texttv_system_html, texttv_telegram_rows


def m(n=1):
    return SimpleNamespace(number=n, home="Örebro SK", away="Test FC", model=(.55,.25,.20), public=(.42,.30,.28))


def test_texttv_board_has_page_and_all_signs():
    html = texttv_system_html([m()], [("1","X")])
    assert "551 STRECKTIPS" in html
    assert "01 Örebro SK - Test FC" in html
    assert html.count('texttv-sign on') == 2
    assert "GARD" in html


def test_telegram_is_data_derived():
    row = texttv_telegram_rows([m()], [("1",)])[0]
    assert row["lead"] == "SPIK 1"
    assert row["model_pick"] == "1"
    assert round(row["delta_pp"], 1) == 13.0


def test_html_escapes_team_names():
    x = m(); x.home = "A < B"
    assert "A &lt; B" in texttv_system_html([x], [("1",)])
