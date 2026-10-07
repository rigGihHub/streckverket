from dataclasses import replace
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from data_sources import SourceStatus
from demo_data import get_demo_matches


def start():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not app.exception
    return app


def test_first_screen_has_no_play_advice_and_exposes_csv_recovery():
    app = start()
    assert app.session_state["data_mode"] == "Demo"
    assert "Öppna en egen kupong från CSV" in [x.label for x in app.expander]
    assert not any("SPELA " in x.value for x in app.markdown)


def test_failed_fetch_stays_on_start_screen_without_replacing_coupon():
    app = start()
    before = app.session_state["coupon"]
    status = SourceStatus("Svenska Spel", False, None, "Saknas", "Otillgänglig källa")
    with patch("coupon_loader.load_current_coupon", return_value=(None, status)):
        app.button(key="landing_fetch_coupon").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state["data_mode"] == "Demo"
    assert app.session_state["coupon"] == before


def test_real_coupon_exposes_first_analysis_outside_collapsed_diagnostics():
    app = start()
    coupon = [replace(m, home=f"Testlag {m.number}", market_available=False) for m in get_demo_matches()]
    status = SourceStatus("Svenska Spel", True, None, "Hög", "13 matcher hämtade")
    with patch("coupon_loader.load_current_coupon", return_value=(coupon, status)):
        app.button(key="landing_fetch_coupon").click().run()
    assert not app.exception
    assert app.session_state["data_mode"] == "Svenska Spel"
    assert app.button(key="novice_refresh_analysis").label == "Analysera kupongen"
    assert not any(x.key == "novice_refresh_analysis" for e in app.expander for x in e.button)


def test_demo_analysis_cannot_turn_failed_live_fetch_into_real_data():
    app = start()
    app.button(key="landing_demo_preview").click().run()
    status = SourceStatus("Svenska Spel", False, None, "Saknas", "Otillgänglig källa")
    with patch("coupon_loader.load_current_coupon", return_value=(None, status)), patch("analysis_controller.execute_one_click") as execute:
        app.button(key="novice_refresh_analysis").click().run()
    assert not app.exception
    execute.assert_not_called()
    assert app.session_state["data_mode"] == "Demo"
    assert app.session_state.get("one_click_result") is None
    assert any("Testkupongen är kvar i testläge" in x.value for x in app.error)


@pytest.mark.parametrize("payload", [b"", b"wrong,column\n1,2\n", b"nr,hemma,borta,streck1,streckx,streck2\n1,A,B,50,25,25\n"])
def test_invalid_csv_reports_error_and_preserves_coupon(payload):
    with patch("streamlit.file_uploader", side_effect=lambda *a, **kw: BytesIO(payload)):
        app = start()
        before = app.session_state["coupon"]
        app.button(key="landing_csv_open").click().run()
    assert not app.exception
    assert any("CSV-kupongen kunde inte öppnas" in x.value for x in app.error)
    assert app.session_state["coupon"] == before
    assert app.session_state["data_mode"] == "Demo"


def test_uploaded_csv_opens_once_and_survives_a_later_rerun():
    payload = pd.DataFrame([
        {"nr": i, "hemma": f"Hemmalag {i}", "borta": f"Bortalag {i}", "streck1": 50, "streckx": 25, "streck2": 25}
        for i in range(1, 14)
    ]).to_csv(index=False).encode()
    with patch("streamlit.file_uploader", side_effect=lambda *a, **kw: BytesIO(payload)):
        app = start()
        app.button(key="landing_csv_open").click().run()
        assert not app.exception
        assert app.session_state["data_mode"] == "CSV-import"
        marker = "preserve-analysis-on-rerun"
        app.session_state["one_click_coupon_fingerprint"] = marker
        app.run()
    assert not app.exception
    assert app.session_state["one_click_coupon_fingerprint"] == marker
    assert len(app.session_state["coupon"]) == 13
