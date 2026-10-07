from pathlib import Path


def test_normal_app_wires_change_report_after_refresh():
    text = Path("app.py").read_text()
    assert "make_analysis_snapshot" in text
    assert "compare_analysis_snapshots" in text
    assert "Vad ändrades sedan förra analysen?" in text
    assert "SYSTEMET ÄR OFÖRÄNDRAT" not in text  # comes from pure helper, not hard-coded UI logic


def test_v371_release_remains_registered():
    from model_change_registry import get_model_change
    change = get_model_change("3.71.0")
    assert change is not None
    assert change.parent_version == "3.70.0"
    assert "analysis-change-report" in change.components
