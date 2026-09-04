from types import SimpleNamespace

from readiness_diagnostics import build_readiness_diagnostics, diagnostics_rows, source_rows


def card(*missing):
    return SimpleNamespace(missing=missing)


def stage(name, ok, matched, attempted, message=""):
    return SimpleNamespace(name=name, ok=ok, matched=matched, attempted=attempted, message=message)


def test_counts_layer_coverage_from_actual_cards():
    diag = build_readiness_diagnostics([
        card("team_strength", "confirmed_lineup"),
        card("confirmed_lineup"),
        card(),
    ])
    layers = {x.key: x for x in diag.layers}
    assert layers["team_strength"].missing == 1
    assert layers["team_strength"].coverage_pct == 67
    assert layers["confirmed_lineup"].missing == 2
    assert layers["confirmed_lineup"].coverage_pct == 33


def test_market_missing_is_explicit_and_has_highest_priority():
    diag = build_readiness_diagnostics([card("confirmed_lineup") for _ in range(13)], market_missing_count=2)
    assert diag.priority_key == "market"
    assert "2 av 13" in diag.priority_text


def test_priority_uses_product_order_not_largest_raw_count():
    cards = [card("team_strength", "confirmed_lineup") for _ in range(4)] + [card("confirmed_lineup") for _ in range(9)]
    diag = build_readiness_diagnostics(cards)
    assert diag.priority_key == "team_strength"


def test_source_coverage_does_not_hide_zero_matching_success():
    diag = build_readiness_diagnostics([card()], [stage("The Odds API", True, 0, 13, "API svarade")])
    row = diag.sources[0]
    assert row.coverage_pct == 0
    assert row.status == "Låg täckning"


def test_source_failure_is_reported_as_failure_even_with_attempts():
    diag = build_readiness_diagnostics([card()], [stage("API-Football", False, 0, 13, "timeout")])
    assert diag.sources[0].status == "Saknas/fel"
    assert source_rows(diag)[0]["Meddelande"] == "timeout"


def test_rows_are_plain_ui_ready_values():
    diag = build_readiness_diagnostics([card(), card("home_away_form")])
    row = next(x for x in diagnostics_rows(diag) if x["Informationslager"] == "Hemma/borta-form")
    assert row["Täckning"] == "1/2"
    assert row["Täckningsgrad"] == "50%"
