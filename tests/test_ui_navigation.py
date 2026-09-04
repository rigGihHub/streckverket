from ui_navigation import ALL_TABS, CORE_TABS, EXPERT_TABS, beginner_flow, hidden_tabs_css, visible_tab_count


def test_normal_mode_only_exposes_core_tabs():
    assert visible_tab_count(False) == 5
    assert visible_tab_count(False) < visible_tab_count(True)


def test_expert_mode_exposes_everything():
    assert visible_tab_count(True) == len(ALL_TABS)
    assert len(ALL_TABS) == len(CORE_TABS) + len(EXPERT_TABS)


def test_normal_css_hides_from_sixth_tab():
    css = hidden_tabs_css(False)
    assert "nth-child(n+6)" in css
    assert "display:none" in css
    assert hidden_tabs_css(True) == ""


def test_beginner_flow_is_short_and_task_oriented():
    flow = beginner_flow()
    assert len(flow) == 4
    assert flow[0].startswith("1.")
    assert "budget" in flow[1].lower()
    assert "förslag" in flow[2].lower()
