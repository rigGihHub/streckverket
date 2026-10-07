from pathlib import Path


def test_release_is_v388_and_non_predictive():
    import release_info
    from model_change_registry import get_model_change
    assert tuple(map(int, release_info.APP_VERSION.split('.'))) >= (3, 88, 0)
    change = get_model_change("3.88.0")
    assert change is not None
    assert change.predictive_change is False


def test_demo_landing_is_not_presented_as_playable_default():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "INGEN AKTUELL KUPONG HÄMTAD" in source
    assert "HÄMTA AKTUELL STRYKTIPSKUPONG" in source
    assert "Jag vill bara prova med testdata" in source
    assert 'st.stop()' in source


def test_novice_diagnostics_are_collapsed():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.expander("Analysstatus & uppdatering", expanded=False)' in source
    assert 'class="novice-summary"' in source
