from streamlit.testing.v1 import AppTest

from core import optimize_system


def expert_app():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    next(x for x in app.toggle if x.label == "Expertläge").set_value(True).run()
    assert not app.exception
    return app


def assert_budget(app, amount):
    assert not app.exception
    assert app.session_state["play_budget"] == amount
    assert app.number_input(key="sidebar_budget").value == amount
    assert app.number_input(key="decision_budget").value == amount
    expected = optimize_system(app.session_state["coupon"], amount, "MAX 13")
    assert next(x.value for x in app.metric if x.label == "Systemkostnad") == f"{expected['rows']} kr"
    assert f"MAX 13 · {expected['rows']} rader" in [x.value for x in app.subheader]
    return expected["rows"]


def test_decision_amount_updates_top_cost_and_system_tab_both_directions():
    app = expert_app()
    before = assert_budget(app, 128)
    app.number_input(key="decision_budget").set_value(512).run()
    assert assert_budget(app, 512) > before
    app.number_input(key="decision_budget").set_value(16).run()
    assert assert_budget(app, 16) <= 16


def test_sidebar_accepts_arbitrary_amount_and_updates_decision_budget():
    app = expert_app()
    app.number_input(key="sidebar_budget").set_value(250).run()
    assert assert_budget(app, 250) <= 250
    app.run()
    assert_budget(app, 250)


def test_amount_survives_switching_modes_and_applies_to_normal_summary():
    app = expert_app()
    app.number_input(key="decision_budget").set_value(512).run()
    app.session_state["show_demo_preview"] = True
    next(x for x in app.toggle if x.label == "Expertläge").set_value(False).run()
    assert not app.exception
    assert app.number_input(key="sidebar_budget").value == 512
    expected = optimize_system(app.session_state["coupon"], 512, "VÄRDE")
    assert any(f"SPELA {expected['rows']} KR" in x.value for x in app.markdown)
    assert any("Maxbudget: 512 kr" in x.value for x in app.caption)
    app.number_input(key="sidebar_budget").set_value(1).run()
    assert not app.exception
    assert any("SPELA 1 KR" in x.value for x in app.markdown)
    next(x for x in app.toggle if x.label == "Expertläge").set_value(True).run()
    assert_budget(app, 1)


def test_amount_survives_landing_screen_where_budget_widget_is_hidden():
    app = expert_app()
    app.number_input(key="sidebar_budget").set_value(192).run()
    next(x for x in app.toggle if x.label == "Expertläge").set_value(False).run()
    assert not app.number_input
    app.run()
    next(x for x in app.toggle if x.label == "Expertläge").set_value(True).run()
    assert_budget(app, 192)
