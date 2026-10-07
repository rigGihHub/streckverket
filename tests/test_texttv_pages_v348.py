from types import SimpleNamespace

from texttv_view import (
    texttv_index_html, texttv_system_html, texttv_advice_html, texttv_spikes_html,
    texttv_traps_html, texttv_upsets_html, texttv_data_status_html,
)


def m(n=1, model=(.55,.25,.20), public=(.42,.30,.28), market_available=True):
    return SimpleNamespace(number=n, home=f"Hem {n}", away=f"Borta {n}", model=model, public=public, market=model, market_available=market_available)


def readiness(status="SPELKlar".upper(), score=82, blockers=()):
    return SimpleNamespace(status=status, score=score, ready_matches=12, total_matches=13, blockers=blockers)


def test_index_lists_all_texttv_pages_and_summary():
    html = texttv_index_html(rows=192, cost=192, spikes=4, guards=7, fulls=2, readiness_status="SPELKlar".upper())
    for page in (551, 552, 553, 554, 555, 556):
        assert str(page) in html
    assert "192 RADER" in html and "4 SPIK" in html


def test_spikes_page_uses_actual_system_selections_only():
    html = texttv_spikes_html([m(1), m(2)], [("1",), ("1", "X")])
    assert "01" in html and "SPIK 1" in html
    assert "02" not in html


def test_traps_page_is_existing_classification_not_new_rule():
    trap = m(4, model=(.46,.30,.24), public=(.64,.20,.16))
    html = texttv_traps_html([trap], [("1", "X")])
    assert "554 STRECKVERKET" in html
    assert "FÄLLA 1" in html
    assert "STRECK 64% / MODELL 46%" in html


def test_upsets_page_respects_core_thresholds():
    upset = m(5, model=(.30,.45,.25), public=(.17,.66,.17))
    html = texttv_upsets_html([upset], [("1", "X")])
    assert "555 STRECKVERKET" in html
    assert "SKRÄLL 1" in html


def test_data_status_never_turns_readiness_into_prediction_confidence():
    matches = [m(i, market_available=(i != 13)) for i in range(1, 14)]
    html = texttv_data_status_html(matches, readiness(blockers=("Bookmaker-marknad saknas",)))
    assert "12/13" in html
    assert "SAKNAR MARKNAD" in html and ">1<" in html
    assert "DATAKVALITET ÄR INTE SAMMA SAK SOM SÄKER FOTBOLLSPROGNOS" in html


def test_all_pages_escape_team_names():
    x = m(); x.home = "A < B"
    sels = [("1",)]
    assert "A &lt; B" in texttv_system_html([x], sels)
    assert "A &lt; B" in texttv_advice_html([x], sels)
    assert "A &lt; B" in texttv_spikes_html([x], sels)
