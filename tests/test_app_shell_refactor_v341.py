from pathlib import Path


def test_data_enrichment_is_extracted_from_app_shell():
    app = Path("app.py").read_text()
    module = Path("ui_data_enrichment.py").read_text()
    assert "from ui_data_enrichment import render_data_enrichment" in app
    assert "render_data_enrichment(matches)" in app
    assert "Databerikning v0.8" not in app
    assert "Databerikning v0.8" in module


def test_runtime_smoke_harness_covers_all_shell_modes():
    source = Path("runtime_smoke.py").read_text()
    assert '("normal", "expert", "specialist")' in source
    assert "AppTest.from_file" in source
    assert "at.toggle[0].set_value(True)" in source
    assert "at.toggle[1].set_value(True)" in source
