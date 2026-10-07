from pathlib import Path
from types import SimpleNamespace

import pytest

from novice_system_board import build_novice_rows, render_novice_system_board, selection_kind, system_instruction


def _matches():
    return [
        SimpleNamespace(number=1, home="Arsenal", away="Fulham"),
        SimpleNamespace(number=2, home="Leeds", away="Derby"),
        SimpleNamespace(number=3, home="Örebro <SK>", away="AIK & Co"),
    ]


def test_selection_kind_uses_beginner_labels():
    assert selection_kind(("1",)) == "SPIK"
    assert selection_kind(("1", "X")) == "HALV"
    assert selection_kind(("1", "X", "2")) == "HEL"


def test_instruction_is_literal_system_choice():
    assert system_instruction(("X", "2")) == "X + 2"
    assert system_instruction(()) == "–"


def test_build_rows_rejects_length_mismatch():
    with pytest.raises(ValueError):
        build_novice_rows(_matches(), [("1",)])


def test_board_marks_only_selected_signs_and_escapes_team_names():
    html = render_novice_system_board(_matches(), [("1",), ("1", "X"), ("1", "X", "2")])
    assert html.count('class="novice-system-row"') == 3
    assert html.count('class="novice-sign on"') == 6
    assert "Örebro &lt;SK&gt;" in html
    assert "AIK &amp; Co" in html
    assert ">SPIK<" in html
    assert ">HALV<" in html
    assert ">HEL<" in html


def test_app_uses_board_not_dataframe_in_novice_system_block():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if not expert_mode:\n    st.markdown("### Kryssa så här")')
    end = source.index('    _spike_candidates = []', start)
    block = source[start:end]
    assert "render_novice_system_board" in block
    assert "st.dataframe" not in block
    assert 'Gula rutor är tecknen' in block
