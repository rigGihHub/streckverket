from analysis_entry import source_availability, source_status_text


def test_no_secrets_is_explicitly_incomplete():
    a = source_availability({})
    assert not any(a.values())
    assert "Inga externa" in source_status_text(a)


def test_all_sources_configured():
    a = source_availability({
        "THE_ODDS_API_KEY": "a",
        "FOOTBALL_DATA_API_KEY": "b",
        "API_FOOTBALL_KEY": "c",
    })
    assert all(a.values())
    assert "Alla tre" in source_status_text(a)


def test_partial_configuration_names_missing_layers():
    a = source_availability({"THE_ODDS_API_KEY": "a"})
    text = source_status_text(a)
    assert "lag/form" in text
    assert "skador/startelvor" in text
