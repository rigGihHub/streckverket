from model_coach import build_model_coach
from facit import FacitCoupon, FacitMatch


def coupon(n, model=(.8,.1,.1), market=(.4,.3,.3), result="1"):
    matches=tuple(FacitMatch(i+1,"A","B",model,market,(.5,.25,.25),("1",),result) for i in range(13))
    return FacitCoupon(str(n),"now","test","MAX13",13,1,0.1,matches)


def test_empty_coach_is_safe():
    r=build_model_coach([])
    assert r["completed_matches"] == 0
    assert r["findings"] == []


def test_coach_finds_mature_segment():
    r=build_model_coach([coupon(i) for i in range(3)], min_segment=30)
    assert r["completed_matches"] == 39
    assert any(x.status == "Ser lovande ut" for x in r["findings"])


def test_coach_never_auto_changes_weights():
    r=build_model_coach([coupon(i) for i in range(3)], min_segment=30)
    assert "automatiskt" in r["recommended_action"].lower() or "observation" in r["recommended_action"].lower()
