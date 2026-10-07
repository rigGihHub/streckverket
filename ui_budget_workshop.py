"""Specialist UI: budget workshop."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from specialist_runtime import specialist_coupon_issues


def render_budget_workshop(matches, locks) -> None:
    _issues = specialist_coupon_issues(matches)
    if _issues:
        st.warning("Specialistverktyget körs inte eftersom kupongunderlaget är ofullständigt.")
        for _issue in _issues:
            st.caption(_issue)
        return
    from budget_workshop import optimize_for_budget, budget_curve, nearby_budgets, best_value_step

    st.markdown("### Budgetverkstaden")
    st.write(
        "Ange vad du maximalt vill spela för. Streckverket söker globalt efter det system som "
        "ger högst modellvärde inom budgeten och respekterar dina låsningar."
    )

    bc1, bc2, bc3 = st.columns([1,1,1])
    with bc1:
        target_budget = st.number_input(
            "Maxbudget (kr)",
            min_value=1,
            max_value=100000,
            value=int(st.session_state.get("budget_target", 192)),
            step=1,
            key="budget_target",
        )
    with bc2:
        budget_strategy = st.radio(
            "Budgetstrategi",
            ["MAX 13", "VÄRDE"],
            horizontal=True,
            key="budget_strategy",
        )
    with bc3:
        st.caption("1 rad = 1 kr i nuvarande kostnadsmodell.")

    budget_result = optimize_for_budget(matches, int(target_budget), budget_strategy, locks)
    unused = budget_result["unused_budget"]

    b1,b2,b3,b4 = st.columns(4)
    b1.metric("Maxbudget", f"{target_budget:.0f} kr")
    b2.metric("Optimalt system", f"{budget_result['rows']} rader")
    b3.metric("Beräknad kostnad", f"{budget_result['cost']:.0f} kr")
    b4.metric("13-rättstäckning", f"{budget_result['coverage']*100:.2f} %")

    if unused > 0:
        st.info(
            f"{unused:.0f} kr blir oanvända. Det beror på kupongens radmultiplikation: "
            "nästa förbättring kan kräva ett större hopp i antal rader."
        )

    if st.button("Använd detta system i Kupongverkstaden", key="apply_budget_system"):
        st.session_state.manual_coupon = [tuple(x) for x in budget_result["selections"]]
        # Keep widget state aligned with the system as far as possible.
        for m, sel in zip(matches, budget_result["selections"]):
            key=f"manual_coupon_{m.number}_{m.home}_{m.away}"
            st.session_state[key]=list(sel)
        st.success("Budgetsystemet är överfört till Kupongverkstaden.")

    st.markdown("#### Vad får jag för nästa 10, 20 eller 50 kr?")
    st.write(
        "Du behöver inte förstå hur systemrader räknas. Streckverket testar i stället hur hela "
        "systemet bör byggas om när du höjer budgeten – och visar om de extra pengarna faktiskt gör nytta."
    )
    from money_impact import spending_options, best_spending_option, explain_option, plain_change

    money_steps = spending_options(
        matches, int(target_budget), (10, 20, 50), budget_strategy, locks
    )
    ms1, ms2, ms3 = st.columns(3)
    for col, option in zip((ms1, ms2, ms3), money_steps):
        with col:
            st.markdown(f"**+{option.requested_extra} kr budget**")
            if option.actual_extra_cost > 0:
                st.metric(
                    "Faktiskt mer spel",
                    f"{option.actual_extra_cost:.0f} kr",
                    f"+{option.coverage_gain_pp:.3f} p.e. täckning",
                )
            else:
                st.metric("Faktiskt mer spel", "0 kr")
            st.caption(explain_option(option))

    best_money_step = best_spending_option(money_steps)
    if best_money_step:
        st.success(
            f"**Mest nytta per extra krona av dessa tre alternativ:** +{best_money_step.requested_extra} kr budget. "
            f"Det använder cirka {best_money_step.actual_extra_cost:.0f} kr extra och ökar modellens "
            f"beräknade 13-rättstäckning med {best_money_step.coverage_gain_pp:.3f} procentenheter."
        )
        if best_money_step.changes:
            with st.expander("Visa exakt hur systemet bör ändras", expanded=False):
                for change in best_money_step.changes:
                    st.write(f"• {plain_change(change)} — {change.home}–{change.away}")
                st.caption(
                    "Streckverket får bygga om hela systemet. Därför kan bästa användningen av mer pengar "
                    "vara att flytta en gardering mellan matcher, inte bara lägga till ett nytt tecken."
                )
    elif money_steps:
        st.info(
            "Ingen av budgetökningarna 10, 20 eller 50 kr ger ett bättre system just här. "
            "Det är helt okej att lämna budget oanvänd – fler kronor är inte automatiskt ett bättre spel."
        )

    st.markdown("#### Vad händer om budgeten ändras?")
    comparison_budgets = nearby_budgets(int(target_budget))
    points = budget_curve(matches, comparison_budgets, budget_strategy, locks)

    curve_rows=[]
    for pt in points:
        curve_rows.append({
            "Budget": pt.budget,
            "Faktisk kostnad": round(pt.cost),
            "Rader": pt.rows,
            "13-rättstäckning %": round(pt.coverage*100, 3),
            "Förändring p.e.": round(pt.delta_coverage_pp, 4),
            "Marginalnytta / kr": round(pt.marginal_pp_per_kr, 6),
        })
    curve_df=pd.DataFrame(curve_rows)
    st.dataframe(curve_df, use_container_width=True, hide_index=True)

    if len(points) >= 2:
        chart_df = pd.DataFrame({
            "Budget": [p.budget for p in points],
            "13-rättstäckning %": [p.coverage*100 for p in points],
        }).set_index("Budget")
        st.line_chart(chart_df)

    value_step=best_value_step(points)
    if value_step:
        st.success(
            f"**Mest täckning per extra krona i jämförelsen:** upp till cirka "
            f"{value_step.cost:.0f} kr / {value_step.rows} rader. "
            f"Det steget gav +{value_step.delta_coverage_pp:.3f} procentenheter "
            f"för {value_step.delta_cost:.0f} extra kr."
        )

    st.markdown("#### Streckverkets budgetrekommendation")
    lower=[p for p in points if p.budget < target_budget]
    higher=[p for p in points if p.budget > target_budget]
    current_pt=min(points, key=lambda p: abs(p.budget-target_budget))
    if lower:
        lo=max(lower,key=lambda p:p.budget)
        saved=current_pt.cost-lo.cost
        lost=(current_pt.coverage-lo.coverage)*100
        st.write(
            f"**Spara:** går du ned mot {lo.budget} kr sparar du cirka {saved:.0f} kr "
            f"och tappar ungefär {lost:.3f} procentenheter modelltäckning."
        )
    if higher:
        hi=min(higher,key=lambda p:p.budget)
        extra=hi.cost-current_pt.cost
        gained=(hi.coverage-current_pt.coverage)*100
        st.write(
            f"**Växla upp:** går du upp mot {hi.budget} kr kostar det cirka {extra:.0f} kr extra "
            f"och ger ungefär +{gained:.3f} procentenheter modelltäckning."
        )

    st.caption(
        "Täckningen är modellens uppskattning av sannolikheten att samtliga 13 utfall ligger inom "
        "systemets valda tecken, under antagandet att matchutfallen kan behandlas som oberoende. "
        "Det är inte en garanti för vinst eller 13 rätt."
    )


