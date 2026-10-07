from model_change_registry import change_rows_for_versions, get_model_change, registered_changes


def test_current_release_has_explicit_non_predictive_change_record():
    row = get_model_change("3.45.0")
    assert row is not None
    assert row.parent_version == "3.44.0"
    assert row.predictive_change is False
    assert row.change_type == "PROVENIENS"


def test_registry_does_not_infer_unknown_history():
    assert get_model_change("3.21.0") is None
    row = change_rows_for_versions(["3.21.0"])[0]
    assert row["Typ"] == "OKÄND"
    assert "gissar inte" in row["Dokumenterad ändring"]
    assert row["Ändrade prognosen?"] == "OKÄNT"


def test_blank_version_is_unknown_not_current():
    row = change_rows_for_versions([""])[0]
    assert row["Modellversion"] == "OKÄND VERSION"
    assert row["Typ"] == "OKÄND"


def test_registry_is_unique_and_ordered():
    rows = registered_changes()
    versions = [r.version for r in rows]
    assert versions == sorted(set(versions))
    assert "3.43.0" in versions and "3.44.0" in versions and "3.45.0" in versions
