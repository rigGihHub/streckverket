import pandas as pd
import streamlit as st

from competition_discovery import fetch_competitions, build_catalog, discover_coupon, TeamMappingCache
from enrichment import fetch_team_finished_matches, summarize_team_form, form_signal_from_summaries
from model_engine import fetch_competition_standings, build_match_signals, enriched_probabilities, probability_delta
from explainable_model import explain_probability_change, plain_delta, plain_summary


def render_data_enrichment(matches):
    st.subheader("Databerikning v0.8 – styrka, form och modellpåverkan")
    st.write(
        "Appen kan nu söka över flera tävlingar i football-data.org och koppla varje kuponglag till "
        "ett externt lag-ID och rätt tävlingskontext. Endast säkra träffar får användas automatiskt."
    )
    api_key = st.text_input("football-data.org API-nyckel", type="password", key="fd_api_key_v07")
    max_comp = st.slider("Max antal tävlingar att skanna", 5, 60, 25, 5, help="Fler tävlingar ökar chansen att hitta alla lag men använder fler API-anrop.")

    if st.button("Skanna tävlingar och matcha alla 26 lag", type="primary"):
        if not api_key.strip():
            st.error("API-nyckel saknas.")
        else:
            try:
                competitions = fetch_competitions(api_key)
                if not competitions:
                    st.error("Inga tävlingar kunde hämtas.")
                else:
                    # Prioritera engelska tävlingar först eftersom Stryktipset ofta innehåller många sådana,
                    # men behåll övriga länder så kupongen kan vara blandad.
                    comps = sorted(competitions, key=lambda c: (0 if c.country == "England" else 1, c.country, c.name))[:max_comp]
                    candidates, team_comp, errors = build_catalog(api_key, comps)
                    discovered = discover_coupon(matches, candidates, team_comp)
                    st.session_state["v07_discovery"] = discovered
                    st.session_state["v07_errors"] = errors
                    st.session_state["v07_api_key"] = api_key
            except Exception as exc:
                st.error(f"Tävling/upptäckt misslyckades: {type(exc).__name__}")

    discovered = st.session_state.get("v07_discovery")
    if discovered:
        records=[]; high=review=missing=0
        cache = TeamMappingCache(".stryktips13/team_mappings.json")
        for row in discovered:
            for side in ("home","away"):
                dr=row[side]; tm=dr.match; comp=dr.competition
                if tm.confidence == "Hög": high += 1
                elif tm.confidence == "Granska": review += 1
                else: missing += 1
                records.append({
                    "Match": row["match_number"],
                    "Sida": "Hemma" if side=="home" else "Borta",
                    "Kupongnamn": tm.query,
                    "Extern klubb": tm.candidate.name if tm.candidate else "–",
                    "Lag-ID": tm.candidate.team_id if tm.candidate else "–",
                    "Tävling": comp.name if comp else "–",
                    "Land": comp.country if comp else "–",
                    "Score": f"{tm.score:.3f}",
                    "Säkerhet": tm.confidence,
                    "Kommentar": dr.ambiguity or tm.reason,
                })
        st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)
        a,b,c=st.columns(3)
        a.metric("Automatiskt godkända", f"{high}/26")
        b.metric("Granska", review)
        c.metric("Saknas", missing)
        if review or missing:
            st.warning("Gråzon eller saknade träffar används inte automatiskt. Det är avsiktligt för att undvika att data kopplas till fel klubb.")

        st.markdown("#### Spara säkra lagmatchningar")
        if st.button("Cachelagra alla Hög-träffar"):
            saved=0
            for row in discovered:
                for side in ("home","away"):
                    dr=row[side]; tm=dr.match; comp=dr.competition
                    if tm.confidence == "Hög" and tm.candidate and comp:
                        cache.remember(tm.query, tm.candidate.team_id, tm.candidate.name, comp.id, comp.name, comp.country)
                        saved += 1
            st.success(f"Sparade {saved} godkända lagmatchningar lokalt. De kan återanvändas nästa kupong.")

        st.markdown("#### Venue-form för säkra träffar")
        if st.button("Hämta hemma-/bortaform"):
            key=st.session_state.get("v07_api_key", "")
            form_rows=[]
            by_match={m.number:m for m in matches}
            for row in discovered:
                h=row["home"]; a=row["away"]
                if h.match.confidence != "Hög" or a.match.confidence != "Hög" or not h.match.candidate or not a.match.candidate:
                    continue
                hm, hs = fetch_team_finished_matches(key, h.match.candidate.team_id, "HOME", 12)
                am, ass = fetch_team_finished_matches(key, a.match.candidate.team_id, "AWAY", 12)
                hsum=summarize_team_form(hm, h.match.candidate.team_id)
                asum=summarize_team_form(am, a.match.candidate.team_id)
                match=by_match[row["match_number"]]
                form_rows.append({
                    "Nr": match.number,
                    "Match": f"{match.home} – {match.away}",
                    "Hemma n": hsum["played"],
                    "Hemma viktad PPG": round(hsum["weighted_ppg"],2),
                    "Hemma GD/m": round(hsum["weighted_gd_pg"],2),
                    "Borta n": asum["played"],
                    "Borta viktad PPG": round(asum["weighted_ppg"],2),
                    "Borta GD/m": round(asum["weighted_gd_pg"],2),
                })
            if form_rows:
                st.dataframe(pd.DataFrame(form_rows), use_container_width=True, hide_index=True)
                st.caption("Formen är venue-specifik och recency-viktad. Små urval ska fortfarande krympas innan de får påverka sannolikhetsmodellen.")
            else:
                st.warning("Ingen match hade två säkra lag-ID:n att berika.")

        errs=st.session_state.get("v07_errors", [])
        if errs:
            with st.expander("Tävlingar som inte kunde läsas"):
                st.write(" · ".join(errs))

        st.markdown("#### Bygg berikad sannolikhet för säkra lagträffar")
        st.caption("Den här körningen använder aktuell ligatabell + venue-form. Frånvaro kopplas in när fixture-ID kan matchas säkert mot API-Football. Modellen visar exakt hur mycket varje signal flyttar marknadsankaret.")
        if st.button("Beräkna v0.8-modell för säkra matcher"):
            key=st.session_state.get("v07_api_key", "")
            if not key:
                st.error("Kör först lagmatchningen med football-data.org-nyckeln.")
            else:
                by_comp={}
                out_rows=[]
                audit_rows=[]
                by_match={m.number:m for m in matches}
                for row in discovered:
                    h=row["home"]; a=row["away"]
                    if h.match.confidence != "Hög" or a.match.confidence != "Hög" or not h.match.candidate or not a.match.candidate or not h.competition or not a.competition:
                        continue
                    # En match bör normalt ligga i samma tävling; om discovery säger olika avstår vi hellre.
                    if h.competition.id != a.competition.id:
                        continue
                    cid=h.competition.id
                    if cid not in by_comp:
                        try:
                            by_comp[cid]=fetch_competition_standings(key,cid)[0]
                        except Exception as exc:
                            by_comp[cid] = {}
                            st.caption(
                                f"Tabellunderlag saknas för tävling {cid}: {type(exc).__name__}. "
                                "Streckverket fortsätter utan att gissa tabellpositioner."
                            )
                    standings=by_comp[cid]
                    hs=standings.get(h.match.candidate.team_id); aws=standings.get(a.match.candidate.team_id)
                    hm,_=fetch_team_finished_matches(key,h.match.candidate.team_id,"HOME",12)
                    am,_=fetch_team_finished_matches(key,a.match.candidate.team_id,"AWAY",12)
                    hsum=summarize_team_form(hm,h.match.candidate.team_id); asum=summarize_team_form(am,a.match.candidate.team_id)
                    fsig=form_signal_from_summaries(hsum,asum)
                    signals=build_match_signals(home_strength=hs.strength if hs else None, away_strength=aws.strength if aws else None, form_signal=fsig)
                    match=by_match[row["match_number"]]
                    final,audit=enriched_probabilities(match.market,signals)
                    explained_final, factor_rows = explain_probability_change(match.market, signals)
                    delta=probability_delta(match.market,final)
                    out_rows.append({
                        "Nr":match.number,"Match":f"{match.home} – {match.away}",
                        "Marknad":f"{match.market[0]*100:.1f}/{match.market[1]*100:.1f}/{match.market[2]*100:.1f}",
                        "v0.8":f"{final[0]*100:.1f}/{final[1]*100:.1f}/{final[2]*100:.1f}",
                        "Δ1":f"{delta[0]*100:+.1f} p.e.","ΔX":f"{delta[1]*100:+.1f} p.e.","Δ2":f"{delta[2]*100:+.1f} p.e.",
                        "Styrka H/B":f"{hs.strength:.2f}/{aws.strength:.2f}" if hs and aws else "saknas",
                    })
                    out_rows[-1]["Varför?"] = plain_summary(match.market, explained_final, factor_rows, match.home, match.away)
                    for fr in factor_rows:
                        audit_rows.append({
                            "Nr":match.number,
                            "Faktor":fr.name,
                            "Källa":fr.source,
                            "Verifierad":"Ja" if fr.verified else "Nej",
                            "Påverkan 1":plain_delta(fr.delta[0], "1"),
                            "Påverkan X":plain_delta(fr.delta[1], "X"),
                            "Påverkan 2":plain_delta(fr.delta[2], "2"),
                            "Förklaring":fr.explanation,
                        })
                if out_rows:
                    st.dataframe(pd.DataFrame(out_rows),use_container_width=True,hide_index=True)
                    with st.expander("Varför ändrade modellen sannolikheten?"):
                        st.dataframe(pd.DataFrame(audit_rows),use_container_width=True,hide_index=True)
                    st.info("Så läser du detta: marknaden är startpunkten. Varje verifierad faktor får sedan bara göra en begränsad justering. Ogranskade rykten påverkar inte sannolikheten alls.")
                    st.warning("Detta är fortfarande en kandidatmodell. Förklaringen visar hur modellen räknar – inte att utfallet är säkert. Vikterna ska backtestas mot verkliga resultat innan de höjs.")
                else:
                    st.warning("Inga matcher hade två säkra lagträffar i samma tävling med tillräcklig data.")

    st.caption("football-data.org dokumenterar /v4/competitions/{id}/standings, /teams och lagmatcher med status/venue-filter. v0.8 håller discovery, datahämtning och prognosjustering som separata steg så fel i en källa inte smittar hela modellen.")
