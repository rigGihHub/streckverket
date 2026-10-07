"""Read-only coupon archive Streamlit surface extracted in v3.39."""

import pandas as pd
import streamlit as st


def render_coupon_archive() -> None:
    from coupon_archive import archive_rows, archive_summary, factor_archive_rows, filter_coupons, match_archive_rows
    from facit import evaluate_coupon
    
    st.subheader("Kupongarkivet")
    st.write(
        "Här kan du gå tillbaka till tidigare sparade kuponger och se **vad Streckverket faktiskt trodde före matcherna**, "
        "hur systemet såg ut och vad som hände efteråt. Arkivet använder bara information som finns i den sparade prognosen."
    )
    
    archived = list(st.session_state.get("facit_coupons", []))
    summary = archive_summary(archived)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Sparade kuponger", summary["coupons"])
    a2.metric("Facit klara", summary["complete"])
    a3.metric("System med 13 täckta", summary["thirteen"], help="Betyder att systemet innehöll rätt utfall i alla 13 matcher. Det säger inte hur hög eventuell vinst blev.")
    a4.metric("Väntar på facit", summary["waiting"])
    
    if not archived:
        st.info("Arkivet är tomt. Spara först en riktig prognos under **Facit & lärande**. Demodata sparas inte som historik.")
    else:
        statuses = ["Alla", "Väntar på facit", "Pågående facit", "Facit klart", "Systemet täckte 13"]
        strategies = ["Alla"] + sorted({c.strategy for c in archived})
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            archive_status = st.selectbox("Visa", statuses, key="archive_status")
        with f2:
            archive_strategy = st.selectbox("Strategi", strategies, key="archive_strategy")
        with f3:
            archive_query = st.text_input("Sök kupong eller lag", placeholder="Exempel: Arsenal", key="archive_query")
    
        filtered = filter_coupons(archived, status=archive_status, strategy=archive_strategy, query=archive_query)
        if not filtered:
            st.warning("Inga sparade kuponger matchar filtret.")
        else:
            table_rows = archive_rows(filtered)
            archive_df = pd.DataFrame([
                {
                    "Sparad": r.captured_label,
                    "Källa": r.source,
                    "Strategi": r.strategy,
                    "Budget": f"{r.budget} kr",
                    "Rader": r.rows,
                    "Modelltäckning": f"{100*r.coverage:.1f} %",
                    "Status": r.status,
                    "Facit": r.result_label,
                    "ID": r.coupon_id,
                }
                for r in table_rows
            ])
            st.dataframe(archive_df, use_container_width=True, hide_index=True)
    
            labels = {
                c.coupon_id: f"{next(r.captured_label for r in table_rows if r.coupon_id == c.coupon_id)} · {c.source} · {c.coupon_id}"
                for c in filtered
            }
            selected_id = st.selectbox(
                "Öppna en sparad kupong",
                [c.coupon_id for c in filtered],
                format_func=lambda cid: labels[cid],
                key="archive_coupon_id",
            )
            selected = next(c for c in filtered if c.coupon_id == selected_id)
            ev = evaluate_coupon(selected)
    
            st.markdown("### Så såg kupongen ut när den sparades")
            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("Budget", f"{selected.budget} kr")
            d2.metric("Rader", selected.rows)
            d3.metric("Beräknad 13-täckning", f"{100*selected.model_coverage:.1f} %", help="Modellens beräknade sannolikhet att systemets val täcker utfallet i samtliga 13 matcher. Inte en garanti för 13 rätt.")
            d4.metric("Facit registrerat", f"{ev['completed']}/13")
            d5.metric("Systemet täckte", f"{ev['system_hits']}/{ev['completed'] or 0}")
            st.caption(f"Sparad {next(r.captured_label for r in table_rows if r.coupon_id == selected.coupon_id)} · Källa: {selected.source} · Strategi: {selected.strategy}")
            st.write(ev["plain_summary"])
    
            match_df = pd.DataFrame(match_archive_rows(selected))
            st.dataframe(match_df, use_container_width=True, hide_index=True)
    
            with st.expander("Vad trodde modellen jämfört med marknaden och folket?", expanded=False):
                st.write(
                    "**Modell** är Streckverkets sparade sannolikhet. **Marknad** är bookmakeroddsens grundbedömning efter att marginalen tagits bort. "
                    "**Streck** visar hur Stryktipsspelarna fördelade sina tecken när prognosen sparades."
                )
                st.dataframe(
                    match_df[["Match", "Möte", "Modell 1/X/2", "Marknad 1/X/2", "Streck 1/X/2", "Modellens förstaval", "Marknadens förstaval", "Folkets förstaval"]],
                    use_container_width=True, hide_index=True,
                )
    
            factors = factor_archive_rows(selected)
            with st.expander("Vilka faktorer påverkade modellen före matcherna?", expanded=False):
                if factors:
                    factor_df = pd.DataFrame(factors)
                    for col in ["Effekt 1", "Effekt X", "Effekt 2"]:
                        factor_df[col] = factor_df[col].map(lambda x: f"{100*x:+.2f} p.e.")
                    factor_df["Styrka"] = factor_df["Styrka"].map(lambda x: f"{x:.2f}")
                    st.dataframe(factor_df, use_container_width=True, hide_index=True)
                    st.caption("Effekt visar den sparade sannolikhetsförändringen i procentenheter för 1, X och 2. Endast de faktoruppgifter som faktiskt sparades före matchen visas.")
                else:
                    st.info("Den här sparade kupongen innehåller inget faktorfacit. Streckverket fyller inte i historiska faktorer i efterhand.")
    
            if ev["completed"] == 13:
                st.markdown("### Vad lärde vi oss av just den här kupongen?")
                l1, l2, l3 = st.columns(3)
                l1.metric("Modellens förstaval rätt", f"{ev['model_pick_hits']}/13")
                l2.metric("Marknadens förstaval rätt", f"{ev['market_pick_hits']}/13")
                l3.metric("Folkets förstaval rätt", f"{ev['public_pick_hits']}/13")
                if ev["model_brier"] is not None:
                    if ev["model_brier"] < ev["market_brier"]:
                        st.success("På den här kupongen gav Streckverkets sannolikheter ett lägre Brier-fel än marknadsbasen. Det är positivt, men en enda kupong är för lite för en modelländring.")
                    elif ev["model_brier"] > ev["market_brier"]:
                        st.warning("På den här kupongen var marknadsbasens sannolikheter bättre än Streckverkets enligt Brier-måttet. Det ska registreras i lärandet, inte döljas.")
                    else:
                        st.info("På den här kupongen låg Streckverket och marknadsbasen lika enligt Brier-måttet.")
                    st.caption(f"Brier: Streckverket {ev['model_brier']:.3f} · marknaden {ev['market_brier']:.3f}. Lägre är bättre.")
            else:
                st.caption("Kupongens lärdomar blir kompletta först när alla 13 slutresultat är registrerade.")
    
    st.caption("Kupongarkivet är läsande: det ändrar inte gamla prognoser eller fyller i information i efterhand. Historiken ska vara ett tidsstämplat facit över vad Streckverket verkligen visste när prognosen sparades.")
    
    
