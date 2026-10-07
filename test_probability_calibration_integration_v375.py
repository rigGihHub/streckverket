from pathlib import Path
from release_info import APP_VERSION, RELEASE_NAME
from model_change_registry import get_model_change

def test_v375_registry_entry_remains_non_predictive():
    c=get_model_change("3.75.0")
    assert c is not None and c.predictive_change is False
    assert "calibration" in c.components[0]

def test_ui_wires_calibration_lab():
    text=Path("ui_facit.py").read_text()
    assert "probability_calibration" in text
    assert "Probability Calibration & Spike Discipline Lab" in text

def test_release_note_states_engines_unchanged():
    text=Path("PROBABILITY_CALIBRATION_SPIKE_DISCIPLINE_v3.75.md").read_text()
    assert "model_engine.py" in text and "strategy_engine.py" in text
