from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_v340_extracts_primary_decision_and_expert_review_surfaces():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "from ui_decision_page import render_decision_page" in app
    assert "render_decision_page(matches, locks, _configured_secrets)" in app
    assert "from ui_data_review import render_data_review" in app
    assert "render_data_review(matches, expert_mode)" in app
    assert "from ui_information_edge import render_information_edge" in app
    assert "render_information_edge()" in app
    assert len(app.splitlines()) < 1300


def test_v340_extracted_ui_modules_are_syntax_valid():
    for name in ("ui_decision_page.py", "ui_data_review.py", "ui_information_edge.py"):
        ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)


def test_missing_market_readiness_constructor_is_explicitly_imported():
    decision = (ROOT / "ui_decision_page.py").read_text(encoding="utf-8")
    assert "CouponReadiness" in decision
    assert "from beginner_ux import (" in decision
    assert "CouponReadiness, coupon_readiness" in decision
    assert "readiness = CouponReadiness(" in decision
