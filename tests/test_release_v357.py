from pathlib import Path
import release_info
from model_change_registry import get_model_change


def test_release_metadata_and_registry():
    assert tuple(map(int, release_info.APP_VERSION.split('.'))) >= (3,57,0)
    assert release_info.RELEASE_NAME
    ch = get_model_change('3.57.0')
    assert ch is not None
    assert ch.predictive_change is False
    assert 'walk-forward-validation' in ch.components


def test_ui_contains_walk_forward_section():
    text = Path('ui_facit.py').read_text(encoding='utf-8')
    assert 'Walk-forward – klarar strategivalet senare kuponger?' in text
    assert 'walk_forward_validation' in text
    assert 'Automatisk strategiändring' in text
