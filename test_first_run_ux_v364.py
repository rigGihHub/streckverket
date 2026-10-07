from pathlib import Path

from first_time_player_ux import resolve_strategy, strategy_labels
from ui_navigation import beginner_flow


def test_beginner_flow_is_three_plain_steps():
    flow = beginner_flow()
    assert len(flow) == 3
    assert flow[0] == "1. Hämta kupongen"
    assert "maxbudget" in flow[1].lower()
    assert "spela systemet" in flow[2].lower()


def test_recommendation_remains_default_and_maps_to_existing_value_engine():
    labels = strategy_labels()
    assert labels[0] == "Streckverkets rekommendation"
    assert resolve_strategy(labels[0]).engine_strategy == "VÄRDE"


def test_app_wires_beginner_strategy_into_engine_instead_of_old_public_radio():
    source = Path("app.py").read_text(encoding="utf-8")
    assert '"Spelsätt", strategy_labels()' in source
    assert "strategy = _first_time_strategy.engine_strategy" in source
    assert '"Systemstrategi", ["MAX 13", "VÄRDE"]' in source


def test_beginner_primary_action_is_fetch_current_coupon():
    source = Path("app.py").read_text(encoding="utf-8")
    assert '"HÄMTA AKTUELL STRYKTIPSKUPONG"' in source
    assert 'with st.expander("Jag vill bara prova med testdata"' in source
    assert 'with st.expander("Byt eller öppna kupong"' in source


def test_technical_odds_controls_are_expert_only():
    source = Path("app.py").read_text(encoding="utf-8")
    expert_start = source.index('    else:\n        st.caption("Expertläget visar hela analysapparaten.")')
    odds_pos = source.index('with st.expander("Odds & datakällor"', expert_start)
    expert_budget_pos = source.index('        budget = render_budget_input(', odds_pos)
    assert expert_start < odds_pos < expert_budget_pos


def test_beginner_has_action_first_system_summary():
    source = Path("app.py").read_text(encoding="utf-8")
    summary_pos = source.index('class="novice-summary"')
    board_pos = source.index('st.markdown("### Kryssa så här")')
    detail_pos = source.index('with st.expander("Fördjupad analys"')
    assert summary_pos < board_pos < detail_pos
    assert 'st.markdown("### Varför just detta?")' in source
