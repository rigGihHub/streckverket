from pathlib import Path
from types import SimpleNamespace

from specialist_runtime import specialist_coupon_issues, specialist_coupon_ready


def _match(n):
    return SimpleNamespace(number=n, home=f"H{n}", away=f"A{n}", model=(.4,.3,.3), public=(.4,.3,.3), market=(.4,.3,.3))


def test_specialist_guard_requires_exactly_13_matches():
    issues = specialist_coupon_issues([_match(i) for i in range(1, 13)])
    assert any("exakt 13" in x for x in issues)
    assert specialist_coupon_ready([_match(i) for i in range(1, 14)])


def test_specialist_guard_rejects_malformed_match():
    matches = [_match(i) for i in range(1, 14)]
    matches[4] = SimpleNamespace(number=5, home="H5", away="A5")
    issues = specialist_coupon_issues(matches)
    assert any("saknar fält" in x for x in issues)


def test_large_specialist_views_are_extracted_from_app_shell():
    app = Path("app.py").read_text()
    assert "from ui_sources import render_sources" in app
    assert "from ui_budget_workshop import render_budget_workshop" in app
    assert "Source Registry + klubbintelligens" not in app
    assert "Budgetverkstaden" not in app
    assert "specialist_coupon_issues" in Path("ui_sources.py").read_text()
    assert "specialist_coupon_issues" in Path("ui_budget_workshop.py").read_text()
