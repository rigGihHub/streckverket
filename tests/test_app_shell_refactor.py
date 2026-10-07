from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_app_shell_is_split_into_dedicated_history_ui_modules():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "from ui_facit import render_facit_learning" in app
    assert "from ui_coupon_archive import render_coupon_archive" in app
    assert "render_facit_learning(matches, budget, strategy, system, locks)" in app
    assert "render_coupon_archive()" in app
    assert len(app.splitlines()) < 1800


def test_extracted_ui_modules_are_syntax_valid():
    for name in ("ui_facit.py", "ui_coupon_archive.py"):
        ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)


def test_internal_datetime_and_pool_boundaries_are_not_broad_exception_catches():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    sources = (ROOT / "ui_sources.py").read_text(encoding="utf-8")
    assert "except (TypeError, ValueError):\n                _kickoff_ts = None" in sources
    assert "except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError) as exc:" in app
