from core import MatchInput
from texttv_view import texttv_guard_efficiency_html, texttv_index_html
from model_change_registry import get_model_change


def m(n, model):
    return MatchInput(n, f"H{n}", f"A{n}", (2.0,3.2,4.0), (.34,.33,.33), model)


def test_texttv_index_has_557_radnytta():
    html=texttv_index_html(rows=64,cost=64,spikes=4,guards=5,fulls=4,readiness_status="SPELK LAR")
    assert "557" in html and "RADNYTTA" in html


def test_557_is_explicitly_not_profit_or_stake_advice():
    matches=[m(1,(.6,.25,.15)),m(2,(.4,.35,.25))]
    system={"rows":2,"coverage":.6*.75,"selections":[("1",),("1","X")],"row_price":1.0}
    html=texttv_guard_efficiency_html(matches,system)
    assert "557 STRECKVERKET" in html
    assert "VINSTPROGNOS" in html
    assert "HÖJA INSATSEN" in html
    assert "+2" in html  # best local added sign in match 2


def test_release_registry_marks_v350_non_predictive():
    change=get_model_change("3.50.0")
    assert change is not None
    assert change.predictive_change is False
    assert "guarderingseffektivitet" in change.components
