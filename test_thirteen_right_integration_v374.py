from pathlib import Path
from model_change_registry import get_model_change


def test_release_metadata_v374():
    change = get_model_change("3.74.0")
    assert change is not None
    assert change.predictive_change is False
    assert "13-right-performance-lab" in change.components


def test_facit_ui_wires_performance_lab():
    text=Path("ui_facit.py").read_text()
    assert "13-Rätt Performance Lab" in text
    assert "thirteen_right_performance" in text
    assert "Visa exakt vilka matcher som stoppade 13 rätt" in text


def test_documentation_is_explicitly_prospective():
    text=Path("THIRTEEN_RIGHT_PERFORMANCE_LAB_v3.74.md").read_text()
    assert "Ingen historisk kupong rekonstrueras i efterhand" in text
    assert "Minst 20 kompletta prospektiva kuponger" in text
    assert "ändrar aldrig modell- eller strategivikter automatiskt" in text
