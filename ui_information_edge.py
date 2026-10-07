import pandas as pd
import streamlit as st

from claim_resolution import ClaimRecord, resolve_claim, summarize_information_edge, information_edge_label


def render_information_edge():
    from claim_resolution import ClaimRecord, resolve_claim, summarize_information_edge, information_edge_label
    st.markdown("### Information Edge")
    st.write("Här mäts inte bara om en källa hade rätt, utan **hur tidigt** den korrekta informationen kom jämfört med när oddsmarknaden och Svenska folkets streck började reagera.")
    demo_claims=[
        ClaimRecord(claim_id="edge-1",source_key="Lokal reporter A",topic="lineup",subject="Nyckelspelare",predicted_value="bench",published_at="2026-08-22T14:00:00Z",market_reaction_at="2026-08-22T16:40:00Z",public_reaction_at="2026-08-22T17:05:00Z"),
        ClaimRecord(claim_id="edge-2",source_key="Officiell klubb",topic="injury",subject="Mittback",predicted_value="out",published_at="2026-08-29T09:00:00Z",market_reaction_at="2026-08-29T10:20:00Z",public_reaction_at="2026-08-29T11:10:00Z"),
        ClaimRecord(claim_id="edge-3",source_key="Supporterforum",topic="lineup",subject="Anfallare",predicted_value="starts",published_at="2026-08-30T13:30:00Z",market_reaction_at="2026-08-30T13:10:00Z",public_reaction_at="2026-08-30T13:25:00Z"),
    ]
    resolved=[resolve_claim(demo_claims[0],"bench","2026-08-22T17:30:00Z"),resolve_claim(demo_claims[1],"out","2026-08-29T12:00:00Z"),resolve_claim(demo_claims[2],"starts","2026-08-30T14:00:00Z")]
    summary=summarize_information_edge(resolved)
    a,b,c,d=st.columns(4); a.metric("Lösta claims",summary["resolved_claims"]); b.metric("Korrekta",f"{100*summary['correct_rate']:.0f}%"); c.metric("Snitt före marknaden",f"{summary['avg_market_edge_minutes']:.0f} min" if summary["avg_market_edge_minutes"] is not None else "–"); d.metric("Snitt före strecken",f"{summary['avg_public_edge_minutes']:.0f} min" if summary["avg_public_edge_minutes"] is not None else "–")
    rows_edge=[]
    for record,result in zip(demo_claims,resolved):
        rows_edge.append({"Källa":record.source_key,"Ämne":record.topic,"Uppgift":f"{record.subject}: {record.predicted_value}","Rätt?":"Ja" if result.correct else "Nej","Före marknad":result.information_edge_market_minutes if result.information_edge_market_minutes is not None else "–","Marknadsetikett":information_edge_label(result.information_edge_market_minutes),"Före streck":result.information_edge_public_minutes if result.information_edge_public_minutes is not None else "–"})
    st.dataframe(pd.DataFrame(rows_edge),use_container_width=True,hide_index=True)
    st.caption("Endast korrekta claims räknas som positiv information edge. En källa som gissar tidigt men ofta fel ska alltså inte belönas för att vara först.")
