from demo_data import get_demo_matches
from play_plan import build_play_plan


def test_plan_builds_for_all_get_demo_matches():
    plan=build_play_plan(get_demo_matches(),192,"MAX 13")
    assert plan.coupon_type
    assert plan.coupon_explanation
    assert plan.budget_message
    assert plan.countercheck


def test_plan_actions_reference_real_matches():
    matches=get_demo_matches(); numbers={m.number for m in matches}
    plan=build_play_plan(matches,192,"MAX 13")
    assert all(i.match_number in numbers for i in plan.items if i.match_number is not None)


def test_plan_spikes_are_actual_system_spikes():
    from decision_page import summarize_decisions
    matches=get_demo_matches(); system=summarize_decisions(matches,192,"MAX 13")["system"]
    by_nr={m.number:sel for m,sel in zip(matches,system["selections"])}
    plan=build_play_plan(matches,192,"MAX 13")
    for item in plan.items:
        if item.kind=="SPIK":
            assert len(by_nr[item.match_number])==1


def test_budget_message_is_plain_language():
    plan=build_play_plan(get_demo_matches(),192,"MAX 13")
    assert "budget" in plan.budget_message.lower()
    assert "kr" in plan.budget_message.lower()
