from ui_navigation import (
    ALL_TABS, CORE_TABS, NOVICE_TABS, EXPERT_TABS, PRIMARY_EXPERT_TABS, SPECIALIST_EXPERT_TABS,
    beginner_flow, expert_flow, hidden_tabs_css, visible_tab_count, visible_tab_names,
)


def test_normal_mode_is_single_screen():
    assert visible_tab_count(False) == 1
    assert visible_tab_names(False) == NOVICE_TABS


def test_default_expert_mode_is_curated_not_everything():
    names = visible_tab_names(True, False)
    assert all(tab in names for tab in PRIMARY_EXPERT_TABS)
    assert all(tab not in names for tab in SPECIALIST_EXPERT_TABS)
    assert visible_tab_count(True, False) < len(ALL_TABS)


def test_specialist_mode_exposes_everything():
    assert visible_tab_count(True, True) == len(ALL_TABS)
    assert visible_tab_names(True, True) == tuple(ALL_TABS)
    assert len(ALL_TABS) == len(CORE_TABS) + len(EXPERT_TABS)


def test_normal_css_hides_every_tab_except_first():
    css = hidden_tabs_css(False)
    assert "nth-child(2)" in css
    assert "nth-child(19)" in css
    assert "display:none" in css


def test_default_expert_css_hides_specialist_tabs_only():
    css = hidden_tabs_css(True, False)
    assert "display:none" in css
    # Datagranskning is tab 6 and must remain visible; Modell-labb is tab 7 and hidden.
    assert "nth-child(7)" in css
    assert "nth-child(6)" not in css
    assert hidden_tabs_css(True, True) == ""


def test_beginner_flow_is_short_and_task_oriented():
    flow = beginner_flow()
    assert len(flow) == 3
    assert flow[0].startswith("1.")
    assert "maxbudget" in flow[1].lower()
    assert "spela systemet" in flow[2].lower()


def test_expert_flow_is_short_and_evidence_ordered():
    flow = expert_flow()
    assert len(flow) == 3
    assert "Datagranskning" in flow[0]
    assert "Information Edge" in flow[1]
    assert "Facit" in flow[2]


def test_should_render_tab_matches_visible_policy():
    from ui_navigation import ALL_TABS, CORE_TABS, NOVICE_TABS, PRIMARY_EXPERT_TABS, should_render_tab

    for name in ALL_TABS:
        assert should_render_tab(name, False, False) is (name in NOVICE_TABS)
        assert should_render_tab(name, True, False) is (name in CORE_TABS or name in PRIMARY_EXPERT_TABS)
        assert should_render_tab(name, True, True) is True
