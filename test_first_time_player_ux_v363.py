from types import SimpleNamespace

from first_time_player_ux import beginner_reason_lines, resolve_strategy, strategy_labels


def test_default_strategy_is_streckverkets_recommendation_and_value_engine():
    labels = strategy_labels()
    assert labels[0] == "Streckverkets rekommendation"
    assert resolve_strategy(labels[0]).engine_strategy == "VÄRDE"


def test_cautious_strategy_maps_to_max_13():
    assert resolve_strategy("Försiktigare").engine_strategy == "MAX 13"


def test_unknown_strategy_falls_back_to_recommendation():
    assert resolve_strategy("något gammalt val").label == "Streckverkets rekommendation"


def test_beginner_reasons_are_compressed_and_plain():
    summary = {
        "spikes": [SimpleNamespace(number=2)],
        "must_guard": [SimpleNamespace(number=4)],
        "traps": [SimpleNamespace(number=9)],
    }
    reasons = beginner_reason_lines(summary, [], "SPELKlar")
    assert len(reasons) == 3
    assert "Match 2" in reasons[0]
    assert "Match 4" in reasons[1]
    assert "Match 9" in reasons[2]
    assert all("Brier" not in text and "modellgap" not in text for text in reasons)
