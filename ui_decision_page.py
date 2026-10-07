from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from analysis_entry import SOURCE_SECRET_KEYS, source_availability, source_status_text
from analysis_controller import build_one_click_config, execute_one_click
from beginner_ux import (
    CouponReadiness, coupon_readiness, confidence_words, edge_explanation, glossary,
    plain_classification, selection_explanation, selection_name, sign_meaning,
)
from core import classify_match
from coupon_state import commit_analysis_state
from data_quality_history import build_quality_snapshot, append_quality_snapshot
from decision_page import summarize_decisions
from match_intelligence import build_match_card
from play_plan import build_play_plan
from readiness_diagnostics import build_readiness_diagnostics, diagnostics_rows
from strategy_engine import (
    coupon_type, best_cross, coupon_cleaners, predictability_ranking, value_ranking,
    three_systems, countercheck,
)


def render_decision_page(matches, locks, configured_secrets):
    from decision_page import summarize_decisions

    # v3.62: passively preserve real pre-kickoff bookmaker observations whenever
    # the normal decision page reruns. This creates the prospective late-market
    # history v3.61 needs without asking a novice to operate an expert control.
    if "facit_store" not in st.session_state:
        try:
            from history_store import create_history_store
            _db_url = ""
            try:
                _db_url = str(st.secrets.get("STRECKVERKET_DATABASE_URL", "") or "")
            except Exception:
                pass
            st.session_state.facit_store = create_history_store(database_url=_db_url or None)
        except Exception:
            st.session_state.facit_store = None
    from automatic_market_capture import automatic_market_capture
    _auto_market = automatic_market_capture(
        st.session_state.get("facit_store"), matches, data_mode=st.session_state.data_mode
    )
    # v3.63: automatic market capture stays silent in the novice path.
    # The expert path can expose provenance; first-time users only need the decision.
    st.markdown("### Få ett färdigt förslag")
    _secret_values = configured_secrets()
    _availability = source_availability(_secret_values)
    _previous_result = st.session_state.get("one_click_result")
    _analysis_running = bool(st.session_state.get("analysis_running", False))
    if st.button("Analysera kupongen", type="primary", key="core_analyze_coupon", use_container_width=True, disabled=_analysis_running):
        st.session_state["analysis_running"] = True
        _cfg = build_one_click_config(
            odds_api_key=_secret_values.get(SOURCE_SECRET_KEYS["odds"], ""),
            football_data_key=_secret_values.get(SOURCE_SECRET_KEYS["football_data"], ""),
            api_football_key=_secret_values.get(SOURCE_SECRET_KEYS["api_football"], ""),
        )
        try:
            _started_from_demo = (st.session_state.data_mode == "Demo")
            _fetch_current_coupon = _started_from_demo
            _execution = execute_one_click(
                _cfg, coupon=st.session_state.coupon,
                fetch_coupon=_fetch_current_coupon,
            )
            _result = _execution.result
            commit_analysis_state(
                st.session_state, enriched_coupon=_result.enriched, result=_result,
                coupon_fingerprint_value=_execution.coupon_fingerprint,
                duration_seconds=_execution.duration_seconds,
                data_mode="Multi-source",
                source_message="Analys genomförd med de datakällor som var tillgängliga och verifierbara.",
            )
            # v3.31: capture exact observation timestamps from verified/direct fact observations
            # at analysis time. Persistence can happen later without rewriting when Streckverket saw them.
            from market_timeline import coupon_market_key as _fact_coupon_key
            from signal_timeline import verified_facts_from_cards, deduplicate_signal_points
            _fact_capture_at = datetime.now(timezone.utc).isoformat()
            _new_fact_points = verified_facts_from_cards(
                _result.cards, coupon_key=_fact_coupon_key(_result.enriched), captured_at=_fact_capture_at, matches=_result.enriched
            )
            _pending_facts = list(st.session_state.get("pending_verified_fact_points", []))
            st.session_state["pending_verified_fact_points"] = _pending_facts + deduplicate_signal_points(_pending_facts, _new_fact_points)
            if (not _started_from_demo) or _fetch_current_coupon:
                _quality_snapshot = build_quality_snapshot(
                    coupon_fingerprint=_execution.coupon_fingerprint, matches=_result.enriched, cards=_result.cards,
                    stages=_result.stages, data_mode="Multi-source", duration_seconds=_execution.duration_seconds, match_provenance=_result.match_provenance,
                )
                append_quality_snapshot("data/data_quality_history.json", _quality_snapshot)
            st.success("Analysen är klar. Streckverket har bara använt de signaler som kunde verifieras.")
            st.rerun()
        except Exception as exc:
            st.error(f"Analysen kunde inte slutföras: {type(exc).__name__}: {exc}")
        finally:
            st.session_state["analysis_running"] = False
    from match_intelligence import build_match_card
    from beginner_ux import (
        coupon_readiness, confidence_words, edge_explanation, glossary, readiness_guidance,
        plain_classification, selection_explanation, selection_name, sign_meaning,
    )

    st.markdown("### Vad ska jag spela?")
    st.write(
        "Välj din maxbudget. Streckverket bygger sedan ett färdigt förslag och säger om underlaget är redo."
    )

    with st.expander("📘 Jag är ny – förklara 1, X, 2 och vanliga spelord", expanded=False):
        st.write("**1** betyder att hemmalaget vinner. **X** betyder oavgjort. **2** betyder att bortalaget vinner.")
        for term, text in glossary().items():
            st.markdown(f"**{term}:** {text}")

    from first_time_player_ux import strategy_labels, resolve_strategy

    play_budget = st.number_input(
        "Hur mycket vill du högst spela för?",
        min_value=1, max_value=100000,
        value=int(st.session_state.get("decision_budget", 192)),
        step=1, key="decision_budget",
        help="Streckverket håller sig inom den här gränsen. Systemet kan ibland kosta lite mindre eftersom radantalet ökar i fasta steg."
    )
    strategy_label = st.radio(
        "Hur vill du spela?",
        strategy_labels(),
        index=0,
        horizontal=True,
        key="decision_strategy_beginner",
        help="Är du osäker: behåll Streckverkets rekommendation."
    )
    _strategy_choice = resolve_strategy(strategy_label)
    play_strategy = _strategy_choice.engine_strategy
    st.caption(_strategy_choice.explanation)

    summary = summarize_decisions(matches, int(play_budget), play_strategy, locks)
    ds = summary["system"]

    # Återanvänd den riktiga one-click-readinessen om den har körts. Annars visar vi öppet
    # att bara marknadsbasen är känd, i stället för att låtsas att externa lager har verifierats.
    one_click_result = st.session_state.get("one_click_result")
    if one_click_result and len(getattr(one_click_result, "cards", [])) == len(matches):
        readiness_cards = list(one_click_result.cards)
    else:
        readiness_cards = [
            build_match_card(match_number=m.number, home=m.home, away=m.away, base_market=m.market)
            for m in matches
        ]

    readiness = coupon_readiness(
        readiness_cards,
        ds["selections"],
        demo=(st.session_state.data_mode == "Demo"),
    )
    _missing_market_count = sum(not getattr(m, "market_available", True) for m in matches)
    if _missing_market_count and st.session_state.data_mode != "Demo":
        readiness = CouponReadiness(
            score=min(readiness.score, 35),
            status="VÄNTA",
            short_reason="Riktiga marknadsodds saknas för delar av kupongen.",
            blockers=(f"aktuella marknadsodds saknas för {_missing_market_count} av 13 matcher",) + tuple(readiness.blockers),
            ready_matches=min(readiness.ready_matches, 13 - _missing_market_count),
            total_matches=readiness.total_matches,
        )

    st.markdown("#### Kan jag lämna in systemet nu?")
    _guidance = readiness_guidance(
        readiness,
        demo=(st.session_state.data_mode == "Demo"),
        market_missing_count=_missing_market_count,
    )
    _status_text = f"**{_guidance.headline}** — {_guidance.message}"
    if _guidance.tone == "success":
        st.success(f"🟢 {_status_text}")
    elif _guidance.tone == "warning":
        st.warning(f"🟡 {_status_text}")
    else:
        st.error(f"🔴 {_status_text}")

    st.markdown(f"**Gör detta nu:** {_guidance.next_step}")

    with st.expander("Se varför Streckverket ger detta besked", expanded=False):
        st.write(
            f"**Underlag:** {confidence_words(readiness.score)} ({readiness.score}/100). "
            f"{readiness.ready_matches} av {readiness.total_matches} matcher har minst 50/100 i datakvalitet."
        )
        st.caption("Datakvalitetspoängen beskriver underlaget – inte hur säker en fotbollsmatch är och inte din chans att vinna.")
        if readiness.blockers:
            st.write("**Det som främst saknas eller behöver kontrolleras:**")
            for blocker in readiness.blockers:
                st.write(f"• {blocker}")

    # v3.49: action-first Text-TV page 100. This is only a compression of the
    # already optimized system and existing decision summary.
    from decision_compression import build_compressed_decision
    from texttv_view import texttv_decision_html
    _quick_decision = build_compressed_decision(matches, summary, readiness)
    st.markdown("#### 100 · BESLUT PÅ NÅGRA SEKUNDER")
    st.markdown(texttv_decision_html(_quick_decision), unsafe_allow_html=True)
    st.caption("Det här är Streckverkets färdiga systemförslag inom din budget.")

    from first_time_player_ux import beginner_reason_lines
    st.markdown("#### Varför just detta?")
    for _reason in beginner_reason_lines(summary, matches, readiness.status):
        st.write(f"• {_reason}")

    with st.expander("SE ALLA 13 MATCHER", expanded=False):
        _simple_rows = []
        for _m, _sel in zip(matches, ds["selections"]):
            _simple_rows.append({
                "Nr": _m.number,
                "Match": f"{_m.home} – {_m.away}",
                "Spela": "".join(_sel),
            })
        st.dataframe(pd.DataFrame(_simple_rows), use_container_width=True, hide_index=True)

    if st.button("ANVÄND DETTA SYSTEM", key="decision_quick_to_coupon", type="primary", use_container_width=True):
        st.session_state.manual_coupon=[tuple(x) for x in ds["selections"]]
        for m,sel in zip(matches,ds["selections"]):
            st.session_state[f"manual_coupon_{m.number}_{m.home}_{m.away}"]=list(sel)
        st.success("Klart. Systemet är sparat som ditt val och kan justeras om du vill.")

    _show_decision_depth = st.toggle(
        "Fördjupad analys", value=False, key="decision_show_depth",
        help="Valfritt. Här finns marknadsdata, jämförelser och tekniska förklaringar. Du behöver inte öppna detta för att använda systemförslaget.",
    )
    if not _show_decision_depth:
        return

    st.caption(source_status_text(_availability))
    if _previous_result is not None and hasattr(_previous_result, "api_stats"):
        _api_stats = _previous_result.api_stats
        st.caption(f"Senaste analys: {_api_stats.network_calls} externa hämtningar · {_api_stats.cache_hits} återanvända svar")
    if not all(_availability.values()):
        st.info("Alla externa datakällor är inte konfigurerade. Grundanalysen fungerar ändå; källstatus och nycklar är ett expert-/driftområde.")
    # Technical diagnostics now live entirely behind the optional deep-analysis gate.
    from market_intelligence_architecture import texttv_market_pages_html, market_architecture_summary
    _market_arch = market_architecture_summary(matches)
    with st.expander("Marknadsdata och bookmakerjämförelse", expanded=False):
        st.markdown(texttv_market_pages_html(matches), unsafe_allow_html=True)
        if int(_market_arch["consensus_known"]) < 13:
            st.caption("Bookmaker-spridning saknas för delar av kupongen. Streckverket gissar inte samstämmighet från en enda aggregerad oddsruta.")
        st.caption("Detta är diagnostik. Marknadsinformationen ändrar inte automatiskt prognosen.")

    if one_click_result and st.session_state.data_mode != "Demo":
        readiness_diag = build_readiness_diagnostics(
            readiness_cards, getattr(one_click_result, "stages", ()), market_missing_count=_missing_market_count
        )
        with st.expander("Vilken data saknas?", expanded=False):
            st.write(readiness_diag.priority_text)
            st.dataframe(pd.DataFrame(diagnostics_rows(readiness_diag)), use_container_width=True, hide_index=True)
            st.caption("Täckningsgrad beskriver om informationslagret finns för matcherna. Den säger inte hur säker matchen är.")

    from play_plan import build_play_plan
    play_plan = build_play_plan(matches, int(play_budget), play_strategy, locks)
    st.markdown("#### Omgångens spelplan")
    st.write("Här kokar Streckverket ner analysen till vad du faktiskt behöver göra. Alla råd nedan kommer från samma modell och systemoptimering som resten av appen.")
    st.info(f"**{play_plan.coupon_type} kupong** — {play_plan.coupon_explanation}")
    if play_plan.items:
        for item in play_plan.items:
            icon = {"SPIK":"📌", "FÄLLA":"⚠️", "X-VÄRDE":"✕", "KUPONGRENSARE":"🧹"}.get(item.kind,"•")
            st.markdown(f"**{icon} {item.title}**")
            st.write(item.action)
            st.caption(item.why)
    else:
        st.caption("Ingen enskild match sticker ut tillräckligt för ett extra strategiråd. Följ det optimerade systemet nedan.")
    st.markdown("**💰 Ska jag lägga mer pengar?**")
    st.write(play_plan.budget_message)
    with st.expander("🔍 Kontrollera spelplanen en sista gång", expanded=False):
        for note in play_plan.countercheck:
            st.write(f"• {note}")

    st.markdown("#### STRECKVERKET TEXT-TV")
    from texttv_view import (
        texttv_index_html, texttv_system_html, texttv_advice_html, texttv_spikes_html,
        texttv_traps_html, texttv_upsets_html, texttv_data_status_html, texttv_guard_efficiency_html,
        texttv_budget_reallocation_html,
    )
    _spike_count = sum(len(sel) == 1 for sel in ds["selections"])
    _guard_count = sum(len(sel) == 2 for sel in ds["selections"])
    _full_count = sum(len(sel) == 3 for sel in ds["selections"])
    st.markdown(texttv_index_html(
        rows=ds["rows"], cost=ds["cost"], spikes=_spike_count, guards=_guard_count,
        fulls=_full_count, readiness_status=readiness.status,
    ), unsafe_allow_html=True)
    _p551, _p552, _p553, _p554, _p555, _p556, _p557, _p558 = st.tabs([
        "551 SYSTEM", "552 MATCHRÅD", "553 SPIKAR", "554 FÄLLOR", "555 SKRÄLLAR", "556 DATASTATUS", "557 RADNYTTA", "558 OMFÖRDELA"
    ])
    with _p551:
        st.markdown(texttv_system_html(matches, ds["selections"]), unsafe_allow_html=True)
    with _p552:
        st.markdown(texttv_advice_html(matches, ds["selections"]), unsafe_allow_html=True)
    with _p553:
        st.markdown(texttv_spikes_html(matches, ds["selections"]), unsafe_allow_html=True)
    with _p554:
        st.markdown(texttv_traps_html(matches, ds["selections"]), unsafe_allow_html=True)
    with _p555:
        st.markdown(texttv_upsets_html(matches, ds["selections"]), unsafe_allow_html=True)
    with _p556:
        st.markdown(texttv_data_status_html(matches, readiness), unsafe_allow_html=True)
    with _p557:
        st.markdown(texttv_guard_efficiency_html(matches, ds), unsafe_allow_html=True)
        st.caption("Radnytta visar hur modellens uppskattade täckning förändras om exakt ett tecken läggs till lokalt. Den räknar inte förväntad utdelning och betyder inte att du bör spela för mer pengar.")
    with _p558:
        st.markdown(texttv_budget_reallocation_html(matches, ds, locks=locks), unsafe_allow_html=True)
        st.caption("Omfördela söker efter en bättre placering av garderingarna med exakt samma radantal. Låsta matcher ändras aldrig. Måttet gäller modellens täckning, inte förväntad utdelning eller vinst.")
    st.caption("Sidorna visar samma grundanalys som resten av Streckverket. Sida 557–558 är diagnostiska budgetmått och ändrar inte prognosmotorn.")

    st.markdown("#### Ditt föreslagna system – enkelt förklarat")
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Antal rader", ds["rows"], help="En rad är en kombination av dina val i alla 13 matcher.")
    k2.metric("Pris", f"{ds['cost']:.0f} kr", help="Appens nuvarande kostnadsmodell räknar 1 rad = 1 kr.")
    k3.metric("Modellens täckning", f"{ds['coverage']*100:.2f} %", help="Modellens uppskattning av chansen att systemets val täcker alla 13 matcher. Ingen garanti.")
    k4.metric("Kvar av budget", f"{ds['unused_budget']:.0f} kr")

    n_spikes = sum(len(sel) == 1 for sel in ds["selections"])
    n_halves = sum(len(sel) == 2 for sel in ds["selections"])
    n_fulls = sum(len(sel) == 3 for sel in ds["selections"])
    st.write(
        f"Systemet innehåller **{n_spikes} spikar** (ett resultat), **{n_halves} halvgarderingar** "
        f"(två resultat) och **{n_fulls} helgarderingar** (alla tre resultat)."
    )

    from strategy_engine import coupon_type, best_cross, coupon_cleaners, predictability_ranking, value_ranking, three_systems, countercheck

    st.markdown("#### Hur ser hela kupongen ut?")
    ctype, ctype_text = coupon_type(matches)
    st.info(f"**{ctype} KUPONG** — {ctype_text}")
    st.caption("Det här beskriver kupongens karaktär, inte om du kommer vinna. En svår kupong kan ge hög utdelning men är också svårare att få 13 rätt på.")

    bx = best_cross(matches)
    cleaners = coupon_cleaners(matches, 3)
    sx1, sx2 = st.columns(2)
    with sx1:
        st.markdown("**✕ OMGÅNGENS KRYSS**")
        if bx:
            st.write(f"**Match {bx.number}: {bx.home} – {bx.away}**")
            st.write(f"Streckverket bedömer oavgjort till **{bx.model_probability*100:.0f} %**, medan **{bx.public_share*100:.0f} %** av strecken ligger på X.")
            st.caption("Ett underspelat kryss kan vara intressant eftersom färre andra system överlever om matchen slutar oavgjort.")
        else:
            st.caption("Inget kryss har just nu både tillräcklig sannolikhet och tydlig understreckning.")
    with sx2:
        st.markdown("**🧹 KUPONGRENSARE**")
        if cleaners:
            c=cleaners[0]
            st.write(f"**Match {c.number}: {c.home} – {c.away} · {c.sign}**")
            st.write(f"Modell **{c.model_probability*100:.0f} %** · streck **{c.public_share*100:.0f} %**.")
            st.caption("Kupongrensare betyder ett mindre populärt resultat som ändå har rimlig chans. Om det inträffar kan många konkurrerande system slås ut. Det väljs aldrig bara för hög utdelning.")
        else:
            st.caption("Ingen tydlig kupongrensare uppfyller våra minimikrav just nu.")

    st.markdown("#### Tre sätt att spela samma kupong")
    variants=three_systems(matches,int(play_budget),locks)
    vc1,vc2,vc3=st.columns(3)
    for col,(name,variant) in zip((vc1,vc2,vc3),variants.items()):
        with col:
            st.markdown(f"**{name}**")
            st.write(f"{variant['rows']} rader · {variant['cost']:.0f} kr")
            st.caption(f"Modellens 13-rättstäckning: {variant['coverage']*100:.2f} %")
            if name=="FÖRSIKTIGT": st.write("Prioriterar högsta möjliga chans enligt modellen.")
            elif name=="STRECKVERKETS VAL": st.write("Balanserar sannolikhet med hur svenska folket har streckat.")
            else: st.write("Söker mer spelvärde och högre utdelningspotential, men hittar inte på slumpmässiga skrällar.")

    with st.expander("Se två olika rankingar – lättast match och bäst spelvärde", expanded=False):
        pr=predictability_ranking(matches); vr=value_ranking(matches)
        r1,r2=st.columns(2)
        with r1:
            st.markdown("**Mest förutsägbar → mest osäker**")
            for i,r in enumerate(pr,1): st.write(f"{i}. Match {r.number}: {r.home} – {r.away} · {r.explanation}")
        with r2:
            st.markdown("**Bäst spelvärde → sämst**")
            for i,r in enumerate(vr,1): st.write(f"{i}. Match {r.number}: {r.home} – {r.away} · {r.explanation}")
        st.caption("Listorna är medvetet separata. En svår match kan samtidigt innehålla ett bra spelvärde.")

    with st.expander("🔍 Streckverkets motkontroll – försök hitta fel i vårt eget system", expanded=False):
        for note in countercheck(matches,ds): st.write(f"• {note}")
        st.caption("Motkontrollen försöker hitta uppenbara strategiska motsägelser. Den ersätter inte färsk data eller verifierade lagnyheter.")

    st.markdown("#### Fyra saker att känna till")
    c1,c2,c3,c4 = st.columns(4)

    with c1:
        st.markdown("**✅ BÄSTA SPIKEN**")
        if summary["spikes"]:
            d = summary["spikes"][0]
            st.write(f"**Match {d.number}: {d.home} – {d.away}**")
            st.write(f"Välj **{d.recommended}**: {sign_meaning(d.recommended, d.home, d.away)}.")
            st.caption(plain_classification(d.classification))
        else:
            st.caption("Ingen match är tillräckligt tydlig för att kallas en bra spik just nu.")

    with c2:
        st.markdown("**🛡️ VIKTIGAST ATT GARDERA**")
        if summary["must_guard"]:
            d = summary["must_guard"][0]
            idx = next((i for i,m in enumerate(matches) if m.number == d.number), None)
            sel = ds["selections"][idx] if idx is not None else ()
            st.write(f"**Match {d.number}: {d.home} – {d.away}**")
            st.write(selection_explanation(sel, d.home, d.away))
        else:
            st.caption("Ingen match sticker ut som extra viktig att gardera.")

    with c3:
        st.markdown("**⚠️ STÖRSTA FÄLLAN**")
        if summary["traps"]:
            d = summary["traps"][0]
            pf_idx = ("1","X","2").index(d.public_favorite)
            m = next(m for m in matches if m.number == d.number)
            st.write(f"**Match {d.number}: {d.home} – {d.away}**")
            st.write(f"Många har valt **{d.public_favorite}** ({sign_meaning(d.public_favorite, d.home, d.away)}).")
            st.caption(edge_explanation(m.model[pf_idx], m.public[pf_idx], d.public_favorite))
        else:
            st.caption("Vi ser ingen tydlig favorit som verkar vara vald av för många spelare.")

    with c4:
        st.markdown("**💥 BÄSTA SKRÄLLCHANSEN**")
        if summary["upsets"]:
            d = summary["upsets"][0]
            idx = ("1","X","2").index(d.recommended)
            m = next(m for m in matches if m.number == d.number)
            st.write(f"**Match {d.number}: {d.home} – {d.away}**")
            st.write(f"Titta extra på **{d.recommended}**: {sign_meaning(d.recommended, d.home, d.away)}.")
            st.caption(edge_explanation(m.model[idx], m.public[idx], d.recommended))
        else:
            st.caption("Ingen tydlig skräll sticker ut i den nuvarande modellen.")

    st.markdown("#### Alla 13 matcher")
    system_rows=[]
    for m, sel in zip(matches, ds["selections"]):
        best_idx=max(range(3), key=lambda i:m.model[i])
        system_rows.append({
            "Nr":m.number,
            "Match":f"{m.home} – {m.away}",
            "Vårt val":" ".join(sel),
            "Vad valet betyder":selection_name(sel),
            "Mest sannolikt enligt modellen":f"{('1','X','2')[best_idx]} · {m.model[best_idx]*100:.0f}%",
            "Kort förklaring":plain_classification(classify_match(m.model,m.public)),
        })
    st.dataframe(pd.DataFrame(system_rows),use_container_width=True,hide_index=True)

    with st.expander("Visa de avancerade siffrorna", expanded=False):
        advanced=[]
        for m, sel in zip(matches, ds["selections"]):
            advanced.append({
                "Nr":m.number,
                "Match":f"{m.home} – {m.away}",
                "Tecken":"".join(sel),
                "Klass":classify_match(m.model,m.public),
                "Modell 1/X/2":f"{m.model[0]*100:.0f}/{m.model[1]*100:.0f}/{m.model[2]*100:.0f}",
                "Streck 1/X/2":f"{m.public[0]*100:.0f}/{m.public[1]*100:.0f}/{m.public[2]*100:.0f}",
            })
        st.dataframe(pd.DataFrame(advanced), use_container_width=True, hide_index=True)
        st.caption("Modell = Streckverkets uppskattade sannolikhet. Streck = hur spelarna har fördelat sina val.")

    if st.button("Skicka systemet till Kupongverkstaden", key="decision_to_coupon"):
        st.session_state.manual_coupon=[tuple(x) for x in ds["selections"]]
        for m,sel in zip(matches,ds["selections"]):
            st.session_state[f"manual_coupon_{m.number}_{m.home}_{m.away}"]=list(sel)
        st.success("Systemet är överfört. I Kupongverkstaden kan du ändra enskilda matcher och direkt se hur priset och täckningen påverkas.")

    st.info(
        "Streckverket kan hjälpa dig att fatta ett mer genomtänkt beslut, men kan aldrig lova vinst. "
        "Fotbollsmatcher är osäkra även när datan är mycket bra."
    )
