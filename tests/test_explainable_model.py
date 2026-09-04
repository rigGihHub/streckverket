import pytest
from evidence import make_signal
from explainable_model import explain_probability_change, plain_delta, plain_summary, biggest_reason


def test_contributions_sum_to_final_change():
    base=(0.50,0.28,0.22)
    signals=[
        make_signal("team_strength","styrka",(0.25,0,-0.25),1,"källa",sample_size=20),
        make_signal("home_away_form","form",(0.15,0,-0.15),1,"källa",sample_size=20),
    ]
    final, rows=explain_probability_change(base,signals)
    for i in range(3):
        assert sum(r.delta[i] for r in rows) == pytest.approx(final[i]-base[i])


def test_unverified_signal_has_zero_effect():
    base=(0.45,0.30,0.25)
    s=make_signal("injury_suspension","rykte",(1,0,-1),1,"forum",is_verified=False)
    final, rows=explain_probability_change(base,[s])
    assert final == pytest.approx(base)
    assert rows[0].delta == pytest.approx((0,0,0))


def test_biggest_reason_and_plain_language():
    base=(0.50,0.30,0.20)
    signals=[
        make_signal("team_strength","styrka",(0.30,0,-0.30),1,"källa",sample_size=20),
        make_signal("weather","väder",(0.05,0,-0.05),1,"källa",sample_size=20),
    ]
    final, rows=explain_probability_change(base,signals)
    assert biggest_reason(rows,0).category == "team_strength"
    assert "procentenheter" in plain_delta(rows[0].delta[0],"1")
    assert "Streckverket" in plain_summary(base,final,rows,"Hemma","Borta")
