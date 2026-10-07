from types import SimpleNamespace

from novice_system_board import build_novice_rows, explain_match


def m(number=1, model=(0.62, 0.22, 0.16), public=(0.50, 0.27, 0.23)):
    return SimpleNamespace(number=number, home="Hemma", away="Borta", model=model, public=public)


def test_spike_explanation_uses_real_model_and_public_numbers():
    text = explain_match(m(), ("1",))
    assert "62 %" in text
    assert "50 %" in text
    assert "Spik 1" in text


def test_half_guard_can_explain_avoiding_overplayed_public_favourite():
    match = m(model=(0.40, 0.33, 0.27), public=(0.55, 0.25, 0.20))
    text = explain_match(match, ("X", "2"))
    assert "folkets favorit" in text
    assert "55 %" in text
    assert "40 %" in text


def test_full_guard_explains_open_match_without_claiming_edge():
    match = m(model=(0.39, 0.34, 0.27), public=(0.40, 0.33, 0.27))
    text = explain_match(match, ("1", "X", "2"))
    assert "Helgardering" in text
    assert "inget utfall når 45 %" in text
    assert "edge" not in text.lower()


def test_rows_carry_explanation_for_each_match():
    rows = build_novice_rows([m(1), m(2)], [("1",), ("1", "X")])
    assert len(rows) == 2
    assert all(row["explanation"] for row in rows)
