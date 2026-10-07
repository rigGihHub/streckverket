import pandas as pd
import streamlit as st

from readiness_diagnostics import build_readiness_diagnostics


def render_data_review(matches, expert_mode: bool):
    if expert_mode:
        from expert_decision_summary import build_expert_decision_summary, evidence_snapshot
        from history_store import create_history_store

        st.markdown("### Expertbeslut – börja här")
        _expert_result = st.session_state.get("one_click_result")
        _expert_market_verified = sum(bool(getattr(m, "market_available", True)) for m in matches)
        _expert_priority_text = None
        if _expert_result is not None and len(getattr(_expert_result, "cards", ())) == len(matches):
            _expert_diag = build_readiness_diagnostics(
                getattr(_expert_result, "cards", ()),
                getattr(_expert_result, "stages", ()),
                market_missing_count=max(0, len(matches) - _expert_market_verified),
            )
            _expert_priority_text = _expert_diag.priority_text

        if "facit_store" not in st.session_state:
            try:
                _expert_db_url = ""
                try:
                    _expert_db_url = str(st.secrets.get("STRECKVERKET_DATABASE_URL", "") or "")
                except Exception:
                    _expert_db_url = ""
                st.session_state.facit_store = create_history_store(database_url=_expert_db_url or None)
                st.session_state.facit_store_error = ""
            except Exception as exc:
                st.session_state.facit_store = None
                st.session_state.facit_store_error = f"{type(exc).__name__}: {exc}"

        try:
            _expert_evidence = evidence_snapshot(st.session_state.get("facit_store"))
        except Exception as exc:
            _expert_evidence = {}
            st.caption(f"Historisk evidens kunde inte sammanfattas: {type(exc).__name__}: {exc}")

        _expert_summary = build_expert_decision_summary(
            data_mode=st.session_state.data_mode,
            total_matches=len(matches),
            market_verified=_expert_market_verified,
            analysis_available=_expert_result is not None,
            readiness_priority_text=_expert_priority_text,
            evidence=_expert_evidence,
        )
        ex1, ex2, ex3 = st.columns(3)
        ex1.metric("Aktuell data", _expert_summary.data_status)
        ex2.metric("Historisk evidens", _expert_summary.evidence_status)
        ex3.metric("Edge", "INTE BEVISAD")
        st.info(f"**Nästa bästa åtgärd:** {_expert_summary.next_action}")
        st.caption(
            "Sammanfattningen använder befintliga dataspärrar och historikgränser. Den skapar ingen ny expert-score, "
            "ändrar inga modellvikter och får aldrig uppgradera ett tunt segment till bevisad edge."
        )

    st.markdown("### Kontrollera indata före spel")
    review=[]
    for m in matches:
        review.append({
            "Nr":m.number,"Match":f"{m.home} – {m.away}",
            "Odds 1/X/2":f"{m.odds[0]:.2f} / {m.odds[1]:.2f} / {m.odds[2]:.2f}",
            "Strecksumma":f"{sum(m.public)*100:.1f}%",
            "Modellsumma":f"{sum(m.model)*100:.1f}%",
        })
    st.dataframe(pd.DataFrame(review),use_container_width=True,hide_index=True)
    st.caption("Målet här är att upptäcka felaktig eller ofullständig indata innan optimeraren får påverka systemet.")

    st.subheader("Evidensmotor v0.4")
    st.write(
        "Marknadsoddsen ska vara modellens ankare. Ny information får bara flytta sannolikheten "
        "om den är verifierad, tidsstämplad och har en definierad påverkan. Varje signal viktas efter "
        "både datakvalitet och hur starkt stöd signaltypen normalt ska få."
    )
    evidence_rows = [
        ("Bekräftad startelva", "Hög", "När lineups finns; spelarfrånvaro värderas relativt ersättaren"),
        ("Skador / avstängningar", "Hög", "Verifierad källa + status; rykten flyttar inte modellen"),
        ("Odds-/marknadsrörelse", "Hög", "Flera bookmakers, särskilt nära spelstopp"),
        ("Lagstyrka / xG", "Medel–hög", "Motståndsjusterad och liga-/säsongskalibrerad"),
        ("Hemma- och bortaform", "Medel", "Separat från total form och med regressionsskydd"),
        ("Vila / spelschema", "Medel", "Dagar sedan match, rotation, förlängning och kommande matcher"),
        ("Tränarbyte / taktisk förändring", "Medel–låg", "Kräver konkret belägg; liten initial vikt"),
        ("Domare", "Låg", "Matchup mellan domarprofil och lagens spelstil; inte bara kortsnitt"),
        ("Väder", "Låg", "Väderprognos kombineras med historisk prestation i liknande förhållanden"),
        ("Restid / logistik", "Låg", "Främst extrema resor, kort vila eller ovanliga förutsättningar"),
        ("Supporterforum / socialt sentiment", "Mycket låg", "Early-warning-signal; kräver volym och verifiering via annan källa"),
        ("Motivation", "Mycket låg", "Används inte som fri AI-bedömning; måste operationaliseras"),
    ]
    st.dataframe(pd.DataFrame(evidence_rows, columns=["Signal", "Maxvikt", "Princip"]), use_container_width=True, hide_index=True)

    st.markdown("#### Utanför boxen – signaler värda att testa")
    st.write(
        "• **Lineup surprise index:** hur mycket startelvan avviker från marknadens förväntade elva.  "
        "\n• **Squad continuity:** hur många minuter den sannolika elvan spelat tillsammans.  "
        "\n• **Set-piece mismatch:** lagens styrka/svaghet på fasta situationer, särskilt mot specifik motståndartyp.  "
        "\n• **Pressing mismatch:** om ett lag historiskt har svårt mot hög press eller lågt block.  "
        "\n• **Rest asymmetry:** skillnad i vila, resor och eventuell förlängning/midweek-match.  "
        "\n• **Market disagreement:** när flera seriösa bookmakers skiljer sig ovanligt mycket – tecken på osäker information.  "
        "\n• **Late-information score:** hur mycket ny verifierad information som kommit efter att strecken satt sig.  "
        "\n• **Public-bias profile:** favorit-/storklubbsbias i Svenska folkets streck jämfört med marknaden."
    )
    st.warning(
        "Viktigt: v0.4 bygger själva mekanismen och källadaptrarna, men den lägger inte på artificiella "
        "procentjusteringar på aktuell kupong innan respektive datakälla är kopplad och historiskt kalibrerad."
    )
