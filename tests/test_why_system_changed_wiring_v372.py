from pathlib import Path


def test_normal_ui_surfaces_change_reasons_and_causality_guard():
    src = Path("app.py").read_text(encoding="utf-8")
    assert "Varför ändrades systemet?" in src
    assert "_change_report.reasons" in src
    assert "De bevisar inte att en enskild faktor ensam orsakade ändringen" in src


def test_v372_remains_registered_as_historical_release():
    from model_change_registry import get_model_change
    change = get_model_change("3.72.0")
    assert change is not None
    assert change.parent_version == "3.71.0"
    assert "analysis-change-reasons" in change.components
