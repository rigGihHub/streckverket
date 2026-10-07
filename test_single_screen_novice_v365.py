from pathlib import Path

from ui_navigation import CORE_TABS, NOVICE_TABS, visible_tab_names, should_render_tab


def test_novice_navigation_is_single_screen():
    assert NOVICE_TABS == ("Vad ska jag spela?",)
    assert visible_tab_names(False) == NOVICE_TABS
    assert should_render_tab("Vad ska jag spela?", False)
    assert not should_render_tab("Mitt system", False)
    assert not should_render_tab("Spikar", False)
    assert not should_render_tab("Fällor & skrällar", False)
    assert not should_render_tab("Varför?", False)


def test_expert_keeps_detailed_core_tabs():
    visible = visible_tab_names(True, False)
    for name in CORE_TABS:
        assert name in visible


def test_app_does_not_build_tabs_for_novice_path():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'if not expert_mode:\n    # v3.65: the novice path already contains the complete answer above.' in source
    assert 'else:\n    st.markdown(hidden_tabs_css(expert_mode, specialist_mode), unsafe_allow_html=True)\n    tab0, tab1' in source
    assert 'Klart. Vill du granska modellen, datakällorna eller historiken' in source


def test_automatic_market_capture_no_longer_depends_on_decision_tab():
    source = Path("app.py").read_text(encoding="utf-8")
    capture_pos = source.index("# v3.65: automatic pre-kickoff market capture")
    tabs_pos = source.index("tab0, tab1")
    assert capture_pos < tabs_pos
    assert "automatic_market_capture(" in source[capture_pos:tabs_pos]
