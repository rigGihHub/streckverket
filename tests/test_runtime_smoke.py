import pytest

from runtime_smoke import APP_FILE, SmokeResult, available, run_smoke


def test_runtime_smoke_contract_exists_and_has_expected_result_rules():
    assert APP_FILE.exists()
    assert SmokeResult("normal", 0, 0, 0, start_action_count=1).ok is True
    assert SmokeResult("normal", 0, 0, 0).ok is False
    assert SmokeResult("normal", 1, 0, 0, start_action_count=1).ok is False
    assert SmokeResult("normal", 0, 1, 0, start_action_count=1).ok is False
    assert SmokeResult("expert", 0, 0, 19).ok is True
    assert SmokeResult("expert", 0, 1, 19, demo_notice_count=1).ok is True
    assert SmokeResult("expert", 0, 2, 19, demo_notice_count=1).ok is False
    assert SmokeResult("expert", 0, 0, 18).ok is False


@pytest.mark.parametrize("mode", ["normal", "expert", "specialist"])
def test_streamlit_runtime_smoke(mode):
    if not available():
        pytest.skip("Streamlit testing är inte installerat i denna byggmiljö.")
    result = run_smoke(mode)
    assert result.ok, result
