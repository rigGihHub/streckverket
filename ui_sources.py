"""Specialist UI: source registry, club intelligence and Supporter Pulse."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from specialist_runtime import specialist_coupon_issues

from source_consensus import provider_matrix


def render_sources(matches, data_mode: str) -> None:
    _issues = specialist_coupon_issues(matches)
    if _issues:
        st.warning("Specialistverktyget körs inte eftersom kupongunderlaget är ofullständigt.")
        for _issue in _issues:
            st.caption(_issue)
        return
    from source_registry import TeamRegistry, TeamSource, registry_quality
    from club_intelligence import ClubClaim, assess_claims, intelligence_summary

    st.markdown("### Source Registry + klubbintelligens · v1.4")
    st.write(
        "Varje klubb får en egen källprofil: officiell klubb, liga/förbund, lokalmedia, nationell media, "
        "dataleverantörer och supporterforum. Appen skiljer dessutom mellan **publicerande sajt** och "
        "**ursprungskälla**, så tre artiklar som bygger på samma journalist eller nyhetsbyrå inte räknas tre gånger."
    )
    st.dataframe(pd.DataFrame(provider_matrix()), use_container_width=True, hide_index=True)

    st.markdown("#### Källprofil – exempel")
    selected_source_match = st.selectbox("Välj klubb", [x for m in matches for x in (m.home, m.away)], key="source_registry_team")
    team_key = selected_source_match.lower().replace(" ", "-")
    demo_registry = TeamRegistry(team_key=team_key, display_name=selected_source_match)
    demo_registry.add_source(TeamSource(team_key, "Officiell klubbkälla", f"https://{team_key}.example", "official_club"))
    demo_registry.add_source(TeamSource(team_key, "Lokal sportredaktion", f"https://local-{team_key}.example", "local_media"))
    demo_registry.add_source(TeamSource(team_key, "Supportercommunity", f"https://fans-{team_key}.example", "supporter_forum"))
    quality = registry_quality(demo_registry)
    q1,q2,q3 = st.columns(3)
    q1.metric("Källprofil", f"{quality['score']}/100", quality["label"])
    q2.metric("Oberoende ursprung", quality["independent_origins"])
    q3.metric("Aktiva källor", quality["source_count"])
    st.caption("Exempelprofilen är demo. I liveflödet seedas officiell klubbwebb från lagmetadata när sådan finns och kan kompletteras med verifierade lokala/community-källor.")

    st.markdown("#### Så hanteras ett klubbrykte")
    fan = TeamSource(team_key, "Supporterforum", f"https://fans-{team_key}.example", "supporter_forum")
    media = TeamSource(team_key, "Lokalmedia", f"https://local-{team_key}.example", "local_media")
    sample_claims = [
        ClubClaim(team_key, "injury", "Nyckelspelare", "out", fan, confidence=0.8),
        ClubClaim(team_key, "injury", "Nyckelspelare", "out", media, confidence=0.9),
    ]
    assessments = assess_claims(sample_claims)
    summary = intelligence_summary(assessments)
    st.dataframe(pd.DataFrame([{
        "Ämne": a.topic, "Spelare/objekt": a.subject, "Uppgift": a.value,
        "Status": a.label, "Confidence": f"{100*a.confidence:.0f}%",
        "Oberoende ursprung": a.independent_origins,
        "Konflikt": "Ja" if a.conflict else "Nej",
        "Får påverka modellen": "Ja" if a.model_usable else "Nej",
        "Varför": a.reason,
    } for a in assessments]), use_container_width=True, hide_index=True)
    st.warning(
        "Forum + en lokal artikel räcker inte automatiskt. Om den lokala artikeln bara återger samma forumrykte "
        "ska båda få samma upstream-origin och då räknas de som **ett** ursprung. För skador/startelvor krävs "
        "officiell bekräftelse eller minst två verkligt oberoende ursprung utan konflikt."
    )

    st.markdown("#### Supporter Pulse – ton är mer än positiv/negativ")
    st.write("Supporter Pulse skiljer mellan **självsäkerhet, uppgivenhet, oro, optimism och ilska**. Konsensus och förändring mot forumets normalton vägs också in. Enstaka högljudda inlägg ska inte få styra.")
    st.info("Supporter Pulse är tills vidare en radar: den kan säga **undersök varför**, men får inte flytta 1/X/2 förrän signaltypen både är oberoende verifierad och historiskt visat marginalnytta mot bookmakerbasen.")
    st.caption("Källoberoende mäter om diskussionen bygger på flera ursprung. Tio Reddit-inlägg som länkar samma artikel räknas inte som tio oberoende nyhetsursprung. Det verifierar fortfarande inte att artikeln eller ryktet är sant.")

    from supporter_sources import load_supporter_sources, sources_for_team, collection_rows, collect_team_pulse
    _supporter_sources_json = ""
    try:
        _supporter_sources_json = str(st.secrets.get("SUPPORTER_SOURCES_JSON", "") or "")
    except Exception:
        pass
    _supporter_sources = load_supporter_sources("data/supporter_sources.json", extra_json=_supporter_sources_json)
    _covered = sum(bool(sources_for_team(team, _supporter_sources)) for team in {x.home for x in matches} | {x.away for x in matches})
    st.caption(f"Verifierade supporterkällor för aktuell kupong: {_covered}/{len({x.home for x in matches} | {x.away for x in matches})} lag. Okända lag gissas aldrig fram.")

    if st.button("Hämta Supporter Pulse för registrerade lag", key="supporter_pulse_collect"):
        from datetime import datetime, timezone
        from production_hardening import coupon_fingerprint
        from supporter_pulse_history import load_pulse_history, make_pulse_snapshot, append_pulse_snapshots
        _history_path = "data/supporter_pulse_history.json"
        _history = load_pulse_history(_history_path)
        _collections = []
        _snapshots = []
        for _m in matches:
            _kickoff_ts = None
            try:
                if getattr(_m, "kickoff", None):
                    _kickoff_ts = datetime.fromisoformat(str(_m.kickoff).replace("Z", "+00:00")).timestamp()
            except (TypeError, ValueError):
                _kickoff_ts = None
            for _team, _opp in ((_m.home, _m.away), (_m.away, _m.home)):
                _c = collect_team_pulse(team=_team, opponent=_opp, sources=_supporter_sources, history=_history, kickoff_ts=_kickoff_ts)
                _collections.append(_c)
                if _c.available and data_mode != "Demo":
                    try:
                        _snapshots.append(make_pulse_snapshot(
                            coupon_fingerprint=coupon_fingerprint(matches), match=_m, team=_team,
                            pulse=_c.pulse, data_mode=data_mode,
                            independent_origins=_c.independent_origins,
                            independence_rate=_c.independence_rate,
                            dominant_origin_share=_c.dominant_origin_share,
                        ))
                    except ValueError:
                        pass
        st.dataframe(pd.DataFrame(collection_rows(_collections)), use_container_width=True, hide_index=True)
        if _snapshots:
            append_pulse_snapshots(_history_path, _snapshots)
            st.success(f"{len(_snapshots)} riktiga Supporter Pulse-observationer sparades före match.")
        elif data_mode == "Demo":
            st.info("Demo analyseras men sparas aldrig som riktig Supporter Pulse-historik.")
        else:
            st.info("Ingen observation sparades. Vanligaste orsaken är saknad verifierad lagkälla, tomt färskt underlag eller saknad bookmakerbas.")

    from supporter_pulse_history import load_pulse_history, signal_history_rows, competition_pulse_rows
    st.markdown("##### Supporter Pulse – historisk validering mot marknaden")
    _pulse_history = load_pulse_history("data/supporter_pulse_history.json")
    if _pulse_history:
        st.dataframe(pd.DataFrame(signal_history_rows(_pulse_history)), use_container_width=True, hide_index=True)
        _pulse_comp_rows = competition_pulse_rows(_pulse_history)
        if _pulse_comp_rows:
            st.dataframe(pd.DataFrame(_pulse_comp_rows), use_container_width=True, hide_index=True)
        st.caption("Bedömningen använder marknadsjusterat utfall: faktisk vinst minus bookmaker-marknadens förväntade vinstsannolikhet. Rå vinstprocent används inte som bevis för supporter-edge.")
    else:
        st.info("Ingen riktig Supporter Pulse-historik finns ännu. Historiken fylls först när en live supporter-källa har fångat ett verkligt tonläge före match; demo får aldrig räknas.")

    from source_performance import SourceObservation, evaluate_source
    st.markdown("#### Source Performance – historisk träffsäkerhet")
    perf_demo = [
        SourceObservation("Lokal reporter A", "lineup", "starts", "starts", "2026-08-01T14:00:00Z", "2026-08-01T17:00:00Z", independent=True),
        SourceObservation("Lokal reporter A", "lineup", "bench", "bench", "2026-08-08T14:30:00Z", "2026-08-08T17:00:00Z", independent=True),
        SourceObservation("Lokal reporter A", "lineup", "starts", "starts", "2026-08-15T14:20:00Z", "2026-08-15T17:00:00Z", independent=True),
        SourceObservation("Aggregator B", "lineup", "starts", "bench", "2026-08-01T15:30:00Z", "2026-08-01T17:00:00Z", independent=False),
        SourceObservation("Aggregator B", "lineup", "starts", "starts", "2026-08-08T16:45:00Z", "2026-08-08T17:00:00Z", independent=False),
        SourceObservation("Aggregator B", "lineup", "bench", "starts", "2026-08-15T16:40:00Z", "2026-08-15T17:00:00Z", independent=False),
    ]
    perf_rows = evaluate_source(perf_demo)
    st.dataframe(pd.DataFrame([{
        "Källa": p.source_key,
        "Ämne": p.topic,
        "Observationer": p.observations,
        "Rå träff": f"{100*p.accuracy:.0f}%",
        "Regressionsskyddad träff": f"{100*p.shrunk_accuracy:.0f}%",
        "Tidighet": f"{100*p.timeliness_score:.0f}%",
        "Oberoende": f"{100*p.independence_rate:.0f}%",
        "Källscore": f"{100*p.performance_score:.0f}%",
        "Viktjustering": f"{p.reliability_multiplier:.2f}×",
    } for p in perf_rows]), use_container_width=True, hide_index=True)
    st.caption(
        "Små urval shrinkas mot en konservativ prior. En källa kan därför inte få 100 % historisk trovärdighet "
        "efter två lyckade tips. Viktjusteringen är medvetet begränsad till 0,78–1,22×."
    )


