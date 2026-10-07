"""Facit & learning Streamlit surface.

Extracted from app.py in v3.39 so the application shell no longer owns the
largest history/validation UI block. This module is presentation/orchestration
only; model_engine and strategy_engine are deliberately untouched.
"""

import pandas as pd
import streamlit as st


def render_facit_learning(matches, budget, strategy, system, locks=None) -> None:
    from datetime import datetime, timezone
    from facit import (
        aggregate_performance, calibration_rows, dumps_facit, evaluate_coupon,
        loads_facit, make_coupon_snapshot, with_results, observation_quality_summary,
    )
    
    st.subheader("Streckverkets facit")
    st.write(
        "Här jämför Streckverket vad modellen trodde **före matcherna** med vad som faktiskt hände. "
        "Det är så vi kan upptäcka om våra justeringar verkligen gör prognoserna bättre – i stället för att bara låta smarta i efterhand."
    )
    st.info(
        "Enkelt förklarat: innan spelstopp sparar vi en kopia av prognosen. Efter matcherna fyller vi i facit. "
        "Sedan jämför vi Streckverket med marknadens grundbedömning och med folkets vanligaste val."
    )
    
    from history_store import create_history_store
    
    if "facit_store" not in st.session_state:
        try:
            secret_url = ""
            try:
                secret_url = str(st.secrets.get("STRECKVERKET_DATABASE_URL", "") or "")
            except Exception:
                secret_url = ""
            st.session_state.facit_store = create_history_store(database_url=secret_url or None)
            st.session_state.facit_store_error = ""
        except Exception as exc:
            st.session_state.facit_store = None
            st.session_state.facit_store_error = f"{type(exc).__name__}: {exc}"
    
    facit_store = st.session_state.facit_store
    if "facit_coupons" not in st.session_state:
        if facit_store is not None:
            try:
                st.session_state.facit_coupons = facit_store.load_coupons()
            except Exception as exc:
                st.session_state.facit_coupons = []
                st.session_state.facit_store_error = f"{type(exc).__name__}: {exc}"
        else:
            st.session_state.facit_coupons = []
    
    def _save_to_history(coupon):
        if facit_store is not None:
            facit_store.save_coupon(coupon)
    
    if facit_store is not None and facit_store.persistent_cloud:
        st.success("☁️ Molnhistorik är aktiv. Sparade prognoser och facit skrivs direkt till PostgreSQL-databasen.")
    elif facit_store is not None:
        st.info(
            "💾 Lagringsmotorn är aktiv med lokal SQLite. Den överlever vanliga omkörningar, men Streamlit Community Cloud "
            "kan rensa den lokala disken vid omstart. JSON-säkerhetskopian finns därför kvar tills en molndatabas är ansluten."
        )
    else:
        st.warning(
            "Lagringsmotorn kunde inte starta. Historiken fungerar i den här sessionen, men sparas inte till databas. "
            f"Teknisk information: {st.session_state.facit_store_error}"
        )
    
    from capture_quality import assess_capture_quality
    capture_now = datetime.now(timezone.utc)
    capture_gate = assess_capture_quality(matches, captured_at=capture_now.isoformat())
    
    from snapshot_timing import classify_snapshot_timing
    current_timings = [classify_snapshot_timing(capture_now.isoformat(), getattr(m, "kickoff", None)) for m in matches]
    known_pre_timings = [t for t in current_timings if t.eligible_pre_match and t.hours_before_kickoff is not None]
    nearest_timing = min(known_pre_timings, key=lambda t: t.hours_before_kickoff) if known_pre_timings else None
    
    st.markdown("### Kvalitet innan sparning")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Status", capture_gate.status)
    q2.metric("Datakvalitet", f"{capture_gate.average_score}/100")
    q3.metric("Verifierad marknad", f"{capture_gate.verified_market_matches}/13")
    q4.metric("Närmaste avspark", "–" if nearest_timing is None else nearest_timing.label)
    if capture_gate.can_save:
        if capture_gate.status == "BRA":
            st.success(capture_gate.message)
        else:
            st.warning(capture_gate.message)
    else:
        st.error(capture_gate.message)
    if capture_gate.actions:
        with st.expander("Så förbättrar du observationsunderlaget", expanded=not capture_gate.can_save):
            for action in capture_gate.actions:
                st.write(f"• {action}")
    st.caption(f"Metadata täcker {capture_gate.evidence_coverage} % av kvalitetskontrollen. Poängen beskriver datans kvalitet – inte hur säker prognosen är.")
    
    # v3.28: separata, tidsstämplade bookmakerpunkter. Detta är inte closing line-data.
    from market_timeline import (
        coupon_market_key, make_market_points, market_movement_rows,
        timeline_summary, match_series_rows,
    )
    market_coupon_key = coupon_market_key(matches)
    market_points = []
    if facit_store is not None:
        try:
            market_points = facit_store.load_market_points(market_coupon_key)
        except Exception as exc:
            st.caption(f"Marknadstidslinjen kunde inte läsas: {type(exc).__name__}: {exc}")
    
    st.markdown("### Marknad över tid")
    st.write(
        "Här kan Streckverket spara flera bookmakerbilder för samma kupong. Då ser vi om marknaden faktiskt flyttar sig "
        "mellan mättillfällena. En punkt nära avspark kallas inte closing line om vi inte har verifierat att den verkligen är marknadens slutpris."
    )
    mt_summary = timeline_summary(market_points, coupon_key=market_coupon_key)
    mt1, mt2, mt3 = st.columns(3)
    mt1.metric("Sparade mättillfällen", int(mt_summary["captures"]))
    mt2.metric("Verifierade marknadspunkter", int(mt_summary["verified_points"]))
    mt3.metric("Senaste täckning", f"{int(mt_summary['verified_matches_latest'])}/13")
    
    timeline_pre_match = not any(t.bucket == "POST_KICKOFF" for t in current_timings)
    timeline_live = st.session_state.data_mode != "Demo"
    timeline_has_market = any(bool(getattr(m, "market_available", False)) for m in matches)
    if st.button(
        "🕒 Spara marknadspunkt nu",
        key="save_market_timeline_point",
        disabled=not (facit_store is not None and timeline_pre_match and timeline_live and timeline_has_market),
        help="Sparar en tidsstämplad bookmakerbild för de 13 matcherna. Nästan identiska punkter inom fem minuter dedupliceras.",
    ):
        try:
            incoming = make_market_points(matches, captured_at=capture_now.isoformat())
            saved_count = facit_store.save_market_points(incoming) if facit_store is not None else 0
            if saved_count:
                st.success(f"Marknadspunkten sparades ({saved_count} matchpunkter).")
            else:
                st.info("Ingen ny marknadspunkt sparades. Den senaste mätningen är redan i praktiken identisk.")
            st.rerun()
        except Exception as exc:
            st.error(f"Marknadspunkten kunde inte sparas: {type(exc).__name__}: {exc}")
    if not timeline_live:
        st.caption("Demodata får inte sparas i marknadstidslinjen.")
    elif not timeline_pre_match:
        st.caption("Marknadstidslinjen stoppas när någon känd match redan har startat.")
    elif not timeline_has_market:
        st.caption("Ingen verifierad bookmakerbas finns att spara just nu.")
    
    # v3.30: gemensam tidsaxel för externa observationer. Supporter Pulse är en observerad ton, inte verifierat faktum.
    from signal_timeline import supporter_history_to_signal_points, combined_timeline_rows
    signal_points = []
    if facit_store is not None:
        try:
            _pending_verified = [
                p for p in st.session_state.get("pending_verified_fact_points", [])
                if getattr(p, "coupon_key", None) == market_coupon_key
            ]
            if _pending_verified:
                facit_store.save_signal_points(_pending_verified)
            from supporter_pulse_history import load_pulse_history
            _pulse_for_signal_timeline = load_pulse_history("data/supporter_pulse_history.json")
            _projected = supporter_history_to_signal_points(
                _pulse_for_signal_timeline, coupon_key=market_coupon_key, matches=matches
            )
            facit_store.save_signal_points(_projected)
            signal_points = facit_store.load_signal_points(market_coupon_key)
        except Exception as exc:
            st.caption(f"Signaltidslinjen kunde inte synkas: {type(exc).__name__}: {exc}")
    
    common_timeline = combined_timeline_rows(market_points, signal_points, coupon_key=market_coupon_key)
    if common_timeline:
        with st.expander("Gemensam tidslinje – marknad och externa signaler", expanded=False):
            st.dataframe(pd.DataFrame(common_timeline), use_container_width=True, hide_index=True)
            st.caption(
                "Tidslinjen visar vad Streckverket observerade och när. Verifierade fakta visar också verifieringsnivå; "
                "en direkt leverantörsuppgift är inte samma sak som oberoende bekräftelse. Supporter Pulse är observerad ton med 0 direkt modellpåverkan. "
                "Tidsordning betyder inte att en signal orsakade eller förutsåg en marknadsrörelse."
            )
    
    # v3.33: repeated evidence must be evaluated across the stored history, not just the current coupon.
    if facit_store is not None:
        try:
            from fact_market_timing import fact_market_timing_rows
            from repeated_signal_evidence import repeated_signal_evidence_rows, repeated_signal_summary
            _all_market_points = facit_store.load_market_points(None)
            _all_signal_points = facit_store.load_signal_points(None)
            _all_fact_timing = fact_market_timing_rows(_all_market_points, _all_signal_points, threshold_pp=1.0)
            _repeated_rows = repeated_signal_evidence_rows(
                _all_fact_timing, min_observations=30, min_unique_matches=20
            )
            _repeated_summary = repeated_signal_summary(_repeated_rows)
        except Exception as exc:
            _repeated_rows = []
            _repeated_summary = {}
            st.caption(f"Upprepad signalevidens kunde inte beräknas: {type(exc).__name__}: {exc}")
        # v3.34: compare only safely-before verified facts whose own EvidenceSignal stored a directional vector.
        try:
            from signal_market_response import signal_market_response_rows, directional_evidence_rows, directional_evidence_summary
            _direction_response = signal_market_response_rows(_all_fact_timing)
            _direction_rows = directional_evidence_rows(
                _direction_response, min_observations=30, min_unique_matches=20
            )
            _direction_summary = directional_evidence_summary(_direction_rows)
        except Exception as exc:
            _direction_response = []
            _direction_rows = []
            _direction_summary = {}
            st.caption(f"Riktningsanalys mot marknaden kunde inte beräknas: {type(exc).__name__}: {exc}")
        # v3.35: one conservative overview before the specialist evidence tables.
        try:
            from evidence_dashboard import evidence_dashboard_rows, evidence_dashboard_summary, public_dashboard_rows
            _evidence_dashboard = evidence_dashboard_rows(_repeated_rows, _direction_rows)
            _evidence_dashboard_summary = evidence_dashboard_summary(_evidence_dashboard)
        except Exception as exc:
            _evidence_dashboard = []
            _evidence_dashboard_summary = {}
            st.caption(f"Evidensöversikten kunde inte beräknas: {type(exc).__name__}: {exc}")
    
        if _evidence_dashboard:
            st.markdown("### Evidensöversikt")
            ed1, ed2, ed3, ed4 = st.columns(4)
            ed1.metric("Granska nu", int(_evidence_dashboard_summary.get("review_now", 0)))
            ed2.metric("Granska tidsmönster", int(_evidence_dashboard_summary.get("timing_review", 0)))
            ed3.metric("Datakvalitet att fixa", int(_evidence_dashboard_summary.get("provenance_gaps", 0)))
            ed4.metric("Samla mer data", int(_evidence_dashboard_summary.get("collect_more", 0)))
            _dashboard_df = pd.DataFrame(public_dashboard_rows(_evidence_dashboard))
            _dashboard_cols = [
                "Prioritet", "Status", "Signaltyp", "Liga", "Källa", "Observationer", "Unika matcher",
                "Riktningsobservationer", "Samma riktning %", "Nästa steg"
            ]
            st.dataframe(_dashboard_df[_dashboard_cols], use_container_width=True, hide_index=True)
            st.caption(
                "Prioriteten styrs av datamängd, unika matcher och proveniens – inte av en hög procentsiffra på tunt underlag. "
                "GRANSKA NU betyder bara att segmentet har tillräcklig data för manuell analys. Det är inte bevis på edge och ändrar inga modellvikter."
            )
    
        if _direction_rows:
            with st.expander("Signalriktning jämfört med marknadsrespons", expanded=False):
                dr1, dr2 = st.columns(2)
                dr1.metric("Separata riktningssegment", int(_direction_summary.get("segments", 0)))
                dr2.metric("Tillräckliga för granskning", int(_direction_summary.get("reviewable_segments", 0)))
                st.dataframe(pd.DataFrame(_direction_rows), use_container_width=True, hide_index=True)
                st.warning(
                    "Riktningen hämtas endast från den verifierade EvidenceSignal-vektorn som faktiskt fanns när faktumet användes. "
                    "Äldre observationer utan sådan proveniens räknas inte som riktningsdata. Endast fakta som var säkert verifierade före "
                    "marknadens rörelseintervall används. Samma riktning betyder tidsmässig samstämmighet – inte orsak eller bevisad edge."
                )
    
        if _repeated_rows:
            with st.expander("Upprepad signalevidens över historiken", expanded=False):
                rs1, rs2, rs3 = st.columns(3)
                rs1.metric("Separata segment", int(_repeated_summary.get("segments", 0)))
                rs2.metric("Tillräckliga för granskning", int(_repeated_summary.get("reviewable_segments", 0)))
                rs3.metric("För lite data", int(_repeated_summary.get("insufficient_segments", 0)))
                st.dataframe(pd.DataFrame(_repeated_rows), use_container_width=True, hide_index=True)
                st.warning(
                    "Evidens grupperas separat per signaltyp, liga och källa. Varje segment kräver minst 30 observationer "
                    "och 20 unika matcher innan det ens får status TILLRÄCKLIGT FÖR GRANSKNING. Äldre fakta utan ligaproveniens "
                    "ligger kvar som Okänd liga och blandas inte in i en namngiven liga. Statusen bevisar inte edge och ändrar inga modellvikter."
                )
    
    movement = market_movement_rows(market_points, coupon_key=market_coupon_key)

    # v3.60: compare stored pre-kickoff market points conservatively.  This is
    # deliberately not called closing line unless a future source can prove that.
    try:
        from pre_kickoff_market_quality import quality_rows as pre_kickoff_quality_rows, display_rows as pre_kickoff_display_rows, texttv_562_html
        _models_by_match = {int(m.number): tuple(m.model) for m in matches}
        _late_market_rows = pre_kickoff_quality_rows(
            market_points, coupon_key=market_coupon_key, models=_models_by_match
        )
    except Exception as exc:
        _late_market_rows = []
        st.caption(f"Sen verifierad förmarknad kunde inte beräknas: {type(exc).__name__}: {exc}")
    if _late_market_rows:
        st.markdown("#### 562 · RÖRELSER – SENASTE VERIFIERADE FÖRMARKNAD")
        st.markdown(texttv_562_html(_late_market_rows), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(pre_kickoff_display_rows(_late_market_rows)), use_container_width=True, hide_index=True)
        st.caption(
            "Jämförelsen använder bara faktiskt sparade bookmakerpunkter före avspark. "
            "MYCKET NÄRA betyder högst 60 minuter före avspark, NÄRA 1–3 timmar och TIDIG mer än 3 timmar. "
            "Ingen av dessa etiketter betyder closing line. Om marknaden senare rör sig mot modellen är det diagnostik, inte bevis på positivt EV eller prediktiv edge."
        )

    if movement:
        st.dataframe(pd.DataFrame(movement), use_container_width=True, hide_index=True)
    
        from market_movement_intelligence import movement_rows as intelligence_movement_rows, supporter_timing_rows
        intelligence_rows = intelligence_movement_rows(market_points, coupon_key=market_coupon_key)
        if intelligence_rows:
            st.markdown("#### Marknadsrörelse – enkel klassificering")
            st.dataframe(pd.DataFrame(intelligence_rows), use_container_width=True, hide_index=True)
            st.caption(
                "STABIL = under 1 procentenhets nettoförändring, MÅTTLIG = 1–3 p.e. och KRAFTIG = minst 3 p.e. "
                "Gränserna är deskriptiva och är inte bevis på spelvärde eller prediktiv edge."
            )
    
        try:
            from supporter_pulse_history import load_pulse_history
            pulse_history_for_timing = load_pulse_history("data/supporter_pulse_history.json")
            pulse_timing = supporter_timing_rows(
                market_points, pulse_history_for_timing, coupon_key=market_coupon_key
            )
        except Exception as exc:
            pulse_timing = []
            st.caption(f"Tidskoppling mot Supporter Pulse kunde inte läsas: {type(exc).__name__}: {exc}")
        if pulse_timing:
            with st.expander("Supporter Pulse jämfört med observerad marknadsrörelse"):
                st.dataframe(pd.DataFrame(pulse_timing), use_container_width=True, hide_index=True)
                st.warning(
                    "Det här visar bara tidsordning mellan sparade mätpunkter. Den exakta tidpunkten för marknadens rörelse är okänd mellan två snapshots, "
                    "och tidsordning bevisar varken orsak eller prediktiv nytta."
                )
    
        try:
            from fact_market_timing import fact_market_timing_rows, timing_evidence_summary
            fact_timing = fact_market_timing_rows(
                market_points, signal_points, coupon_key=market_coupon_key, threshold_pp=1.0
            )
            fact_timing_summary = timing_evidence_summary(fact_timing, min_observations=30)
        except Exception as exc:
            fact_timing = []
            fact_timing_summary = {}
            st.caption(f"Tidsanalys för verifierade fakta kunde inte beräknas: {type(exc).__name__}: {exc}")
        if fact_timing:
            with st.expander("Verifierade fakta jämfört med marknadsrörelse", expanded=False):
                fc1, fc2, fc3, fc4 = st.columns(4)
                fc1.metric("Observationer", int(fact_timing_summary.get("observations", 0)))
                fc2.metric("Säkert före", int(fact_timing_summary.get("definitely_before", 0)))
                fc3.metric("Osäker ordning", int(fact_timing_summary.get("ambiguous", 0)))
                fc4.metric("Efter", int(fact_timing_summary.get("after", 0)))
                st.caption(f"Evidensstatus: {fact_timing_summary.get('status', 'FÖR LITE DATA')} · Minst 30 observationer krävs innan mönstret ens får beskrivas som tillräckligt för granskning.")
                st.dataframe(pd.DataFrame(fact_timing), use_container_width=True, hide_index=True)
                st.warning(
                    "Marknadsrörelsen kan bara placeras inom intervallet mellan två sparade bookmakerpunkter. "
                    "SÄKERT FÖRE betyder att faktumet var verifierat innan intervallet började. INOM OSÄKERT RÖRELSEINTERVALL betyder att ordningen inte går att avgöra. "
                    "Inte ens 30+ observationer bevisar orsak, spelvärde eller prediktiv edge."
                )
                try:
                    from signal_market_response import signal_market_response_rows
                    _current_direction = signal_market_response_rows(fact_timing)
                except Exception:
                    _current_direction = []
                if _current_direction:
                    st.markdown("##### Riktning på verifierad signal vs marknaden")
                    _direction_cols = [
                        'Nr','Match','Faktum','Förväntad riktning','Marknadsrörelse','Marknadsrespons',
                        'Riktningssamstämmighet','Riktningsdata användbar'
                    ]
                    st.dataframe(pd.DataFrame(_current_direction)[_direction_cols], use_container_width=True, hide_index=True)
                    st.caption("RIKTNING OKÄND betyder att äldre data saknar sparad riktningsproveniens. Streckverket gissar då inte signalens riktning från ord som skada eller startelva.")
        selectable = [m for m in matches if any(r["Nr"] == m.number and r["Punkter"] >= 2 for r in movement)]
        if selectable:
            chosen_match = st.selectbox(
                "Visa marknadsrörelse för match",
                selectable,
                format_func=lambda m: f"{m.number}. {m.home} – {m.away}",
                key="market_timeline_match",
            )
            series_rows = match_series_rows(market_points, market_coupon_key, chosen_match.number)
            if len(series_rows) >= 2:
                chart = pd.DataFrame(series_rows).set_index("Tid")
                st.line_chart(chart[["1", "X", "2"]])
                st.caption("Y-axeln visar bookmakerbasens marginalrensade sannolikhet i procent. Rörelsen är deskriptiv och bevisar inte värde eller prediktiv edge.")
    else:
        st.info("Ingen marknadsrörelse finns ännu. Spara minst två mättillfällen för samma kupong för att börja bygga tidslinjen.")
    
    csave1, csave2 = st.columns([1,1])
    with csave1:
        is_live = st.session_state.data_mode != "Demo"
        can_save = is_live and capture_gate.can_save
        if st.button(
            "📌 Spara prognosen före spelstopp",
            disabled=not can_save,
            help="Sparar exakt vad modellen och systemet säger just nu. Kräver en riktig pre-match-kupong med verifierad bookmakerbas för alla 13 matcher.",
        ):
            coupon_id = capture_now.strftime("%Y%m%dT%H%M%SZ")
            from factor_learning import factor_map_from_cards
            factor_snapshots = {}
            oc_result = st.session_state.get("one_click_result")
            if oc_result and len(getattr(oc_result, "cards", [])) == 13:
                factor_snapshots = factor_map_from_cards(oc_result.cards)
            from swap_backtest import snapshot_reallocation_proposals
            from counterfactual_system_lab import snapshot_counterfactual_systems
            swap_proposals = snapshot_reallocation_proposals(matches, system, locks=locks, limit=5)
            counterfactual_systems = snapshot_counterfactual_systems(matches, system, budget=int(budget), locks=locks)
            from predictive_experiment import build_shadow_predictions
            shadow_predictions = build_shadow_predictions(
                matches, st.session_state.facit_coupons,
                source_model_version=__import__("release_info").APP_VERSION,
            )
            snap = make_coupon_snapshot(
                coupon_id,
                matches,
                system["selections"],
                source=st.session_state.data_mode,
                strategy=strategy,
                budget=int(budget),
                rows=int(system["rows"]),
                model_coverage=float(system["coverage"]),
                factor_snapshots=factor_snapshots,
                captured_at=capture_now.isoformat(),
                model_version=__import__("release_info").APP_VERSION,
                swap_proposals=swap_proposals,
                counterfactual_systems=counterfactual_systems,
                market_timeline_key=market_coupon_key,
                shadow_predictions=shadow_predictions,
            )
            st.session_state.facit_coupons.append(snap)
            try:
                _save_to_history(snap)
                if facit_store is not None:
                    facit_store.save_market_points(make_market_points(matches, captured_at=capture_now.isoformat()))
                if facit_store is not None and facit_store.persistent_cloud:
                    st.success("Prognosen är sparad i molnhistoriken.")
                else:
                    st.success("Prognosen är sparad. Ladda gärna ner facitfilen som extra säkerhetskopia.")
            except Exception as exc:
                st.warning(f"Prognosen finns i sessionen men databassparningen misslyckades: {type(exc).__name__}: {exc}")
        if not is_live:
            st.caption("Demoläget kan inte sparas som riktigt facit. Hämta en riktig kupong först.")
        elif not capture_gate.can_save:
            st.caption("Sparningen är spärrad tills observationsunderlaget uppfyller minimikraven ovan.")
    
    with csave2:
        uploaded_facit = st.file_uploader("Återställ tidigare facitfil", type=["json"], key="facit_upload")
        if uploaded_facit is not None and st.button("Importera facitfil"):
            try:
                restored = loads_facit(uploaded_facit.getvalue().decode("utf-8"))
                st.session_state.facit_coupons = restored
                if facit_store is not None:
                    facit_store.replace_all(restored)
                st.success(f"Importerade {len(restored)} sparade kuponger" + (" till databasen." if facit_store is not None else "."))
                st.rerun()
            except Exception as exc:
                st.error(f"Facitfilen kunde inte läsas: {exc}")
    
    coupons = list(st.session_state.facit_coupons)
    if coupons:
        st.download_button(
            "⬇️ Ladda ner facit som säkerhetskopia",
            data=dumps_facit(coupons),
            file_name="streckverket-facit.json",
            mime="application/json",
            help="Streamlit Community Cloud är inte en permanent databas. Spara filen om du vill vara säker på att historiken finns kvar.",
        )
    else:
        st.warning("Det finns inget riktigt facit sparat ännu. Första steget är att spara en prognos före spelstopp.")
    
    if coupons:
        latest = coupons[-1]
        st.markdown("### Senast sparade kupongen")
        st.caption(
            f"Sparad {latest.captured_at} · källa {latest.source} · strategi {latest.strategy} · "
            f"{latest.rows} rader · modellens uppskattade täckning {100*latest.model_coverage:.2f} %."
        )
        st.write(
            "När matcherna är färdigspelade kan Streckverket försöka hämta slutresultaten automatiskt. "
            "Du kan alltid kontrollera eller fylla i 1/X/2 manuellt under knappen."
        )
    
        from auto_results import fetch_coupon_results
        auto_key = st.text_input(
            "API-Football-nyckel för automatisk facitinhämtning",
            type="password", key="facit_api_football",
            help="Nyckeln används bara när du trycker på knappen. Resultat registreras endast när lagmatchningen är tillräckligt säker och matchen är slutrapporterad.",
        )
        if st.button("🔄 Hämta färdiga matchresultat automatiskt", disabled=not auto_key.strip()):
            try:
                found, details = fetch_coupon_results(latest, auto_key.strip())
                if found:
                    updated = with_results(latest, found)
                    st.session_state.facit_coupons[-1] = updated
                    try:
                        _save_to_history(updated)
                    except Exception as exc:
                        st.warning(f"Resultaten finns i sessionen men databassparningen misslyckades: {type(exc).__name__}: {exc}")
                    st.success(f"Hittade och sparade {len(found)} säkert matchade slutresultat. Övriga matcher lämnades orörda.")
                else:
                    st.info("Inga nya säkert matchade slutresultat hittades. Inget facit ändrades.")
                with st.expander("Visa kontroll av automatisk resultatmatchning", expanded=False):
                    for d in details:
                        score = "" if d.home_score is None else f" · {d.home_score}–{d.away_score}"
                        st.write(f"**Match {d.match_number}:** {d.status}{score} · {d.message}")
                if found:
                    st.rerun()
            except Exception as exc:
                st.error(f"Resultaten kunde inte hämtas: {type(exc).__name__}: {exc}")
    
        st.caption("Säkerhetsregel: Streckverket gissar aldrig ett resultat. Osäker lagmatchning, saknat datum eller en match som inte är slutrapporterad lämnas för manuell kontroll.")
    
        result_values = {}
        rcols = st.columns(2)
        for idx, fm in enumerate(latest.matches):
            options = ["Ej klar", "1", "X", "2"]
            current = fm.result if fm.result in ("1","X","2") else "Ej klar"
            with rcols[idx % 2]:
                val = st.selectbox(
                    f"{fm.match_number}. {fm.home} – {fm.away}",
                    options,
                    index=options.index(current),
                    key=f"facit_result_{latest.coupon_id}_{fm.match_number}",
                )
                if val != "Ej klar":
                    result_values[fm.match_number] = val
    
        if st.button("✅ Spara matchresultaten"):
            updated = with_results(latest, result_values)
            st.session_state.facit_coupons[-1] = updated
            try:
                _save_to_history(updated)
                st.success("Resultaten är sparade i facitet" + (" och databasen." if facit_store is not None else "."))
            except Exception as exc:
                st.warning(f"Resultaten finns i sessionen men databassparningen misslyckades: {type(exc).__name__}: {exc}")
            st.rerun()
    
        latest_eval = evaluate_coupon(st.session_state.facit_coupons[-1])
        e1,e2,e3,e4 = st.columns(4)
        e1.metric("Färdiga matcher", f"{latest_eval['completed']}/13")
        e2.metric("Systemet täckte", f"{latest_eval['system_hits']}/{latest_eval['completed'] or 0}")
        e3.metric("Modellens förstaval rätt", f"{latest_eval['model_pick_hits']}/{latest_eval['completed'] or 0}")
        e4.metric("Marknadens förstaval rätt", f"{latest_eval['market_pick_hits']}/{latest_eval['market_completed'] or 0}")
        st.write(latest_eval["plain_summary"])
    
        st.markdown("### Vad har modellen lärt sig hittills?")
        perf = aggregate_performance(st.session_state.facit_coupons)
        p1,p2,p3,p4 = st.columns(4)
        p1.metric("Verifierade matcher", perf["matches"], help="Färdigspelade matcher där en riktig bookmakerbas fanns sparad före matchen.")
        p2.metric(
            "Streckverket rätt på förstaval",
            "–" if perf["model_pick_accuracy"] is None else f"{100*perf['model_pick_accuracy']:.1f} %",
            help="Hur ofta det utfall som modellen gav högst sannolikhet faktiskt inträffade. Det mäter inte systemets garderingar.",
        )
        p3.metric(
            "Marknaden rätt på förstaval",
            "–" if perf["market_pick_accuracy"] is None else f"{100*perf['market_pick_accuracy']:.1f} %",
            help="Samma jämförelse, men med bookmakeroddsens grundsannolikheter.",
        )
        p4.metric("Kuponger där systemet täckte 13", perf["system_13_count"])
        if perf.get("excluded_missing_market", 0):
            st.warning(
                f"{perf['excluded_missing_market']} färdigspelade matcher räknas inte i modellvalideringen eftersom en verifierad bookmakerbas saknas eller inte kan styrkas i den sparade historiken."
            )
        st.write(f"**Streckverkets försiktiga slutsats:** {perf['lesson']}")

        # v3.74: diagnose where a prospective coupon lost the possibility of 13 correct.
        from thirteen_right_performance import performance_summary as thirteen_performance_summary, coupon_rows as thirteen_coupon_rows, miss_rows as thirteen_miss_rows
        thirteen_perf = thirteen_performance_summary(st.session_state.facit_coupons)
        st.markdown("### 13-Rätt Performance Lab")
        st.write(
            "Här mäter Streckverket varför en färdig kupong inte täckte alla 13 utfall. "
            "Labbet använder bara system och sannolikheter som faktiskt sparades före matcherna; äldre luckor fylls inte i i efterhand."
        )
        t1,t2,t3,t4 = st.columns(4)
        t1.metric("Kompletta kuponger", thirteen_perf["complete_coupons"])
        t2.metric("13 rätt fanns i systemet", thirteen_perf["thirteen_correct"])
        t3.metric(
            "Snitt täckta matcher",
            "–" if thirteen_perf["mean_system_hits"] is None else f"{thirteen_perf['mean_system_hits']:.2f}/13",
        )
        t4.metric("Systemmissar totalt", thirteen_perf["system_misses"])
        b1,b2,b3 = st.columns(3)
        b1.metric("Spikmissar", thirteen_perf["missed_spikes"], help="Matcher där systemet valde ett enda tecken och utfallet blev ett annat.")
        b2.metric("Halvgarderingsmissar", thirteen_perf["missed_halves"], help="Matcher där systemet valde två tecken men utfallet blev det tredje.")
        b3.metric(
            "Rätt modellförstaval men systemmiss",
            thirteen_perf["allocation_misses"],
            help="Modellens högsta sannolikhet var det verkliga utfallet, men systemkonstruktionen lämnade ändå utfallet utanför. Detta pekar på system-/budgetallokering snarare än ett fel förstaval i prognosen.",
        )
        st.info(f"Utvecklingsprioritet: **{thirteen_perf['priority']}**")
        st.write(thirteen_perf["lesson"])
        if thirteen_perf["complete_coupons"]:
            expected = thirteen_perf["expected_13_count_from_frozen_model"]
            actual = thirteen_perf["thirteen_correct"]
            st.caption(
                f"Fryst modell: summan av systemens beräknade täckning motsvarar {expected:.2f} förväntade 13-täckningar över historiken; faktiskt utfall är {actual}. "
                "Detta är en kalibreringsdiagnostik under modellens antaganden, inte bevis på framtida träffsäkerhet eller oberoende mellan matcher."
            )
        if not thirteen_perf["review_ready"]:
            st.warning(
                f"Minst {thirteen_perf['min_review_coupons']} kompletta prospektivt sparade kuponger krävs innan labbet får rekommendera vilken motor som bör ändras. "
                "Fram till dess visas bara observerade missmönster."
            )
        _thirteen_coupon_rows = thirteen_coupon_rows(st.session_state.facit_coupons)
        _thirteen_miss_rows = thirteen_miss_rows(st.session_state.facit_coupons)
        if _thirteen_coupon_rows:
            with st.expander("Visa kupong för kupong", expanded=False):
                st.dataframe(pd.DataFrame(_thirteen_coupon_rows), use_container_width=True, hide_index=True)
        if _thirteen_miss_rows:
            with st.expander("Visa exakt vilka matcher som stoppade 13 rätt", expanded=False):
                st.dataframe(pd.DataFrame(_thirteen_miss_rows), use_container_width=True, hide_index=True)
        st.caption(
            "Labbet ändrar inga modellvikter eller system automatiskt. Målet är att skilja prognosfel från system-/budgetfel innan nästa hypotes byggs och testas prospektivt."
        )

        # v3.83: audit frozen same-budget alternatives without hindsight reconstruction.
        from system_p13_audit import system_p13_summary, audit_rows as system_p13_audit_rows
        _p13_audit = system_p13_summary(st.session_state.facit_coupons)
        st.markdown("### System P(13) Audit")
        st.write(
            "Granskar om ett systemalternativ som faktiskt frystes före match hade högre modellbaserad sannolikhet att täcka alla 13 utfall inom samma budgetram. "
            "Äldre kuponger utan frysta alternativ rekonstrueras inte i efterhand."
        )
        pa1,pa2,pa3,pa4 = st.columns(4)
        pa1.metric("Granskningsbara kuponger", _p13_audit["auditable_coupons"])
        pa2.metric("Med ≥1 % P(13)-headroom", _p13_audit["coupons_with_material_headroom"])
        pa3.metric(
            "Snitt P(13)-skillnad",
            "–" if _p13_audit["mean_p13_delta_pp"] is None else f"{_p13_audit['mean_p13_delta_pp']:+.3f} pp",
        )
        pa4.metric("Sekundärt: räddade 13", _p13_audit["counterfactual_13_rescues"])
        st.info(f"Status: **{_p13_audit['status']}**")
        st.write(_p13_audit["lesson"])
        if not _p13_audit["review_ready"]:
            st.warning(
                f"Minst {_p13_audit['min_review_coupons']} prospektivt frysta kuponger krävs innan återkommande system-/budgetbrist får pekas ut. "
                "Resultat på mindre underlag är endast diagnostik."
            )
        if _p13_audit["legacy_without_frozen_variants"]:
            st.caption(
                f"{_p13_audit['legacy_without_frozen_variants']} kuponger saknar frysta systemalternativ och exkluderas. "
                "Streckverket fyller inte i gamla system i efterhand eftersom tidigare låsningar/proveniens då kan saknas."
            )
        _p13_rows = system_p13_audit_rows(st.session_state.facit_coupons)
        if _p13_rows:
            with st.expander("Visa P(13)-audit kupong för kupong", expanded=False):
                st.dataframe(pd.DataFrame(_p13_rows), use_container_width=True, hide_index=True, column_config={
                    "Original P(13)": st.column_config.NumberColumn(format="%.4f"),
                    "Bästa frysta P(13)": st.column_config.NumberColumn(format="%.4f"),
                    "P(13)-skillnad pp": st.column_config.NumberColumn(format="%+.3f"),
                    "Relativ förbättring": st.column_config.NumberColumn(format="%+.1%%"),
                })
        st.caption(
            "Bästa alternativ väljs enbart efter den frysta modellens P(13), aldrig efter facit. 'Räddade 13' är därför bara en efterföljande observation – inte ett optimeringskriterium eller bevis på edge."
        )

        # v3.84: prospective spike-failure diagnostics before any spike-threshold change.
        from spike_failure_lab import spike_failure_summary, spike_rows as spike_failure_rows
        _spike = spike_failure_summary(st.session_state.facit_coupons)
        st.markdown("### Spike Failure Lab")
        st.write(
            "Granskar de spikar som faktiskt frystes före match. Labbet jämför faktisk träff med sannolikheten Streckverket gav just det spikade tecknet och, när den finns, bookmakerankarets sannolikhet för samma tecken."
        )
        sf1,sf2,sf3,sf4 = st.columns(4)
        sf1.metric("Prospektiva spikar", _spike["spikes"])
        sf2.metric("Spikträff", "–" if _spike["hit_rate"] is None else f"{100*_spike['hit_rate']:.1f} %")
        sf3.metric("Snitt modell p(spik)", "–" if _spike["mean_model_probability"] is None else f"{100*_spike['mean_model_probability']:.1f} %")
        sf4.metric("Kalibreringsgap", "–" if _spike["calibration_gap"] is None else f"{100*_spike['calibration_gap']:+.1f} pp")
        st.info(f"Status: **{_spike['status']}**")
        st.write(_spike["lesson"])
        if not _spike["review_ready"]:
            st.warning(
                f"Minst {_spike['min_review_spikes']} spikar över {_spike['min_review_coupons']} kuponger krävs innan labbet får peka ut ett återkommande spikproblem. "
                "En enskild favorit kan förlora utan att spiken var felbeslutad."
            )
        if _spike["market_comparable_spikes"]:
            st.caption(
                "På spikar med verifierat bookmakerankare: "
                f"Streckverket binär Brier {(_spike['model_binary_brier'] or 0):.4f}, marknaden {(_spike['market_binary_brier'] or 0):.4f}. "
                "Jämförelsen gäller exakt samma spiktecken och matcher."
            )
        if _spike["bands"]:
            with st.expander("Spikträff per fryst sannolikhetsintervall", expanded=True):
                st.dataframe(pd.DataFrame(_spike["bands"]), use_container_width=True, hide_index=True, column_config={
                    "Snitt modell p": st.column_config.NumberColumn(format="%.1f%%"),
                    "Faktisk träff": st.column_config.NumberColumn(format="%.1f%%"),
                    "Kalibreringsgap": st.column_config.NumberColumn(format="%+.1f%%"),
                    "Snitt marknad p": st.column_config.NumberColumn(format="%.1f%%"),
                })
                st.caption(
                    "Ett intervall måste innehålla minst 20 spikar från minst 5 olika kuponger innan det får klassas som moget. "
                    "Minst ±5 procentenheters kalibreringsgap markeras för granskning, men skapar ingen automatisk spiktröskel."
                )
        _spike_rows = spike_failure_rows(st.session_state.facit_coupons)
        if _spike_rows:
            with st.expander("Visa spik för spik", expanded=False):
                st.dataframe(pd.DataFrame(_spike_rows), use_container_width=True, hide_index=True, column_config={
                    "Modell p(spik)": st.column_config.NumberColumn(format="%.1f%%"),
                    "Marknad p(spik)": st.column_config.NumberColumn(format="%.1f%%"),
                })
        st.caption(
            "Labbet använder inte facit för att välja vilka matcher som borde ha spikats. Det utvärderar bara redan frysta spikar efteråt och ändrar varken model_engine.py, strategy_engine.py eller någon spikregel automatiskt."
        )

        # v3.85: isolate guard placement from stake size using exact same-row frozen alternatives.
        from guard_allocation_lab import guard_allocation_summary, guard_allocation_rows
        _guard = guard_allocation_summary(st.session_state.facit_coupons)
        st.markdown("### Guard Allocation Lab")
        st.write(
            "Granskar om samma antal rader återkommande hade kunnat ge högre modellbaserad P(13) genom att flytta garderingar mellan matcher. "
            "Endast alternativ som faktiskt frystes före match och har exakt samma radantal som originalsystemet får jämföras."
        )
        ga1,ga2,ga3,ga4 = st.columns(4)
        ga1.metric("Samma-rad-kuponger", _guard["auditable_coupons"])
        ga2.metric("Med materiell garderingflytt", _guard["coupons_with_material_relocation"])
        ga3.metric(
            "Snitt P(13)-skillnad",
            "–" if _guard["mean_p13_delta_pp"] is None else f"{_guard['mean_p13_delta_pp']:+.3f} pp",
        )
        ga4.metric(
            "Andel materiell flytt",
            "–" if _guard["material_relocation_share"] is None else f"{100*_guard['material_relocation_share']:.1f} %",
        )
        st.info(f"Status: **{_guard['status']}**")
        st.write(_guard["lesson"])
        if not _guard["review_ready"]:
            st.warning(
                f"Minst {_guard['min_review_coupons']} prospektiva kuponger med ett fryst alternativ på exakt samma radantal krävs innan garderingarnas placering får pekas ut som ett återkommande problem."
            )
        _guard_rows = guard_allocation_rows(st.session_state.facit_coupons)
        if _guard_rows:
            with st.expander("Visa garderingallokering kupong för kupong", expanded=False):
                st.dataframe(pd.DataFrame(_guard_rows), use_container_width=True, hide_index=True, column_config={
                    "Original P(13)": st.column_config.NumberColumn(format="%.4f"),
                    "Alternativ P(13)": st.column_config.NumberColumn(format="%.4f"),
                    "P(13)-skillnad pp": st.column_config.NumberColumn(format="%+.3f"),
                    "Relativ förbättring": st.column_config.NumberColumn(format="%+.1%%"),
                })
        st.caption(
            "Facit väljer aldrig alternativet. Exakt samma radantal krävs för att ett större och dyrare system inte ska kunna se ut som bättre garderingallokering. Ingen automatisk strategiändring görs."
        )

        # v3.86: audit entire same-row system structure without hindsight optimization.
        from counterfactual_13_optimizer_audit import optimizer_audit_summary, optimizer_audit_rows
        _opt13 = optimizer_audit_summary(st.session_state.facit_coupons)
        st.markdown("### Counterfactual 13-Rätt Optimizer Audit")
        st.write("Jämför originalsystemet med redan före-match frysta alternativ som har exakt samma radantal. Bästa alternativ väljs endast efter fryst modell-P(13), aldrig efter facit.")
        co1,co2,co3,co4 = st.columns(4)
        co1.metric("Granskningsbara kuponger", _opt13["auditable_coupons"])
        co2.metric("Med materiellt headroom", _opt13["coupons_with_material_headroom"])
        co3.metric("Strukturella förbättringar", _opt13["material_structural_changes"])
        co4.metric("Snitt P(13)-skillnad", "–" if _opt13["mean_p13_delta_pp"] is None else f"{_opt13['mean_p13_delta_pp']:+.3f} pp")
        st.info(f"Status: **{_opt13['status']}**")
        st.write(_opt13["lesson"])
        if not _opt13["review_ready"]:
            st.warning(f"Minst {_opt13['min_review_coupons']} prospektivt granskningsbara kuponger krävs innan systemstrukturen får pekas ut som ett återkommande problem.")
        _opt_rows = optimizer_audit_rows(st.session_state.facit_coupons)
        if _opt_rows:
            with st.expander("Visa optimizer-audit kupong för kupong", expanded=False):
                st.dataframe(pd.DataFrame(_opt_rows), use_container_width=True, hide_index=True)
        st.caption("Samma radantal krävs. Resultat används endast sekundärt efter att alternativen varit frysta; ingen strategi eller motor ändras automatiskt.")

        # v3.87: hierarchical attribution across overlapping system diagnostics.
        from system_decision_attribution import decision_attribution_summary
        _attrib = decision_attribution_summary(st.session_state.facit_coupons)
        st.markdown("### System Decision Attribution")
        st.write(
            "Slår ihop v3.83–v3.86 utan att dubbelräkna överlappande P(13)-effekter. "
            "Garderingar och hela systemstrukturen jämförs hierarkiskt; spikdiagnostik hålls separat eftersom kalibreringsmått inte kan summeras med P(13)-headroom."
        )
        at1,at2,at3,at4 = st.columns(4)
        at1.metric("Bred systemaudit", _attrib["broad_status"])
        at2.metric("Gardering", _attrib["guard_status"])
        at3.metric("Systemstruktur", _attrib["structure_status"])
        at4.metric("Spik", _attrib["spike_status"])
        st.info(f"Nästa evidensbaserade prioritet: **{_attrib['priority']}**")
        st.write(f"**Attribution:** {_attrib['attribution']}")
        st.write(_attrib["rationale"])
        if _attrib["guard_share_of_structure_headroom"] is not None:
            st.caption(
                f"Garderinglabbet motsvarar cirka {100*_attrib['guard_share_of_structure_headroom']:.1f} % av den genomsnittliga direkta samma-rad-P(13)-signal som hela struktur-auditen visar. "
                "Det är en diagnostisk relation mellan överlappande auditer, inte en kausal decomposition."
            )
        if not _attrib["direct_system_review_ready"] or not _attrib["spike_review_ready"]:
            st.warning("Alla delområden har ännu inte moget prospektivt underlag. Attributionen får därför inte användas som automatisk strategi- eller modelländring.")
        st.caption("P(13)-effekterna summeras aldrig mellan de överlappande labben. Facit används inte för att välja systemalternativ, och ingen motor ändras automatiskt.")

        # v3.75: calibration diagnostics before any spike threshold or model-weight experiment.
        from probability_calibration import calibration_summary as probability_calibration_summary
        cal = probability_calibration_summary(st.session_state.facit_coupons)
        st.markdown("### Probability Calibration & Spike Discipline Lab")
        st.write(
            "Jämför frysta Streckverket-sannolikheter med bookmakerankaret och faktiskt utfall. "
            "Fokus är om höga sannolikheter beter sig som de säger – särskilt i matcher som systemet faktiskt spikade."
        )
        ca,cb,cc,cd = st.columns(4)
        ca.metric("Kompletta kuponger", cal["complete_coupons"])
        cb.metric("Spikmatcher", cal["spike_matches"])
        cc.metric("Modell Brier", "–" if cal["model"]["brier"] is None else f"{cal['model']['brier']:.4f}")
        cd.metric("Marknad Brier", "–" if cal["market"]["brier"] is None else f"{cal['market']['brier']:.4f}")
        st.info(f"Status: **{cal['status']}**")
        st.write(cal["lesson"])
        if not cal["review_ready"]:
            st.warning(
                f"Minst {cal['min_review_coupons']} kompletta prospektiva kuponger krävs innan kalibreringsmönster får användas som grund för ett nytt prediktivt experiment. "
                "Ett litet sample får inte skapa en regel som exempelvis 'spika aldrig under 65 %'."
            )
        if cal["spike_bins"]:
            with st.expander("Spikarnas kalibrering per sannolikhetsintervall", expanded=True):
                st.dataframe(pd.DataFrame(cal["spike_bins"]), use_container_width=True, hide_index=True,
                    column_config={"Snittprognos": st.column_config.NumberColumn(format="%.1f%%"), "Faktisk träff": st.column_config.NumberColumn(format="%.1f%%"), "Kalibreringsgap": st.column_config.NumberColumn(format="%+.1f%%")})
                st.caption("Gap = faktisk träff minus fryst sannolikhet. Positivt gap betyder att utfallet inträffade oftare än prognosen i just detta historiska intervall.")
        with st.expander("Modell mot marknad – alla förstaval 50 % +", expanded=False):
            left,right=st.columns(2)
            with left:
                st.write("**Streckverket**")
                if cal["model_bins"]: st.dataframe(pd.DataFrame(cal["model_bins"]), use_container_width=True, hide_index=True)
                else: st.caption("Inga observationer i intervallen ännu.")
            with right:
                st.write("**Bookmakerankare**")
                if cal["market_bins"]: st.dataframe(pd.DataFrame(cal["market_bins"]), use_container_width=True, hide_index=True)
                else: st.caption("Inga verifierade marknadsobservationer i intervallen ännu.")
        if cal["model_outcome_bins"]:
            with st.expander("Kalibrering separat för 1 / X / 2", expanded=False):
                st.dataframe(pd.DataFrame(cal["model_outcome_bins"]), use_container_width=True, hide_index=True)
        st.caption(
            "Brier/log loss mäts på alla tre utfallssannolikheter. Intervalltabellerna är diagnostik, inte bevisad edge. "
            "Saknad bookmakerdata exkluderas och fylls aldrig i retroaktivt. Ingen modell- eller strategimotor ändras i v3.75."
        )


        # v3.76: paired model-vs-market validation and leave-one-signal-out diagnostics.
        from model_market_validation import model_market_summary
        from signal_ablation import signal_ablation_summary
        mm = model_market_summary(st.session_state.facit_coupons)
        st.markdown("### Model vs Market & Signal Ablation Lab")
        st.write(
            "Här jämförs Streckverket och bookmakerankaret på exakt samma färdiga, prospektivt frysta matcher. "
            "Positiv Brier-/log-loss-vinst betyder att Streckverket var bättre i just detta sample – inte att en framtida edge är bevisad."
        )
        ma, mb, mc, md = st.columns(4)
        ma.metric("Parade matcher", mm["matches"])
        mb.metric("Kuponger", mm["eligible_coupons"])
        mc.metric("Brier-vinst mot marknad", "–" if mm["brier_gain"] is None else f"{mm['brier_gain']:+.4f}")
        md.metric("Log-loss-vinst", "–" if mm["log_loss_gain"] is None else f"{mm['log_loss_gain']:+.4f}")
        st.info(f"Status: **{mm['status']}**")
        st.write(mm["lesson"])
        if not mm["review_ready"]:
            st.warning(
                f"För mogen modell-vs-marknad-granskning krävs minst {mm['min_coupons']} kuponger och {mm['min_matches']} parade matcher. "
                "Ingen vikt eller prognosregel ändras automatiskt före det."
            )
        if mm["divergence_rows"]:
            with st.expander("När modellen avviker mer från marknaden", expanded=False):
                ddf = pd.DataFrame(mm["divergence_rows"])
                st.dataframe(ddf, use_container_width=True, hide_index=True)
                st.caption(
                    "Avvikelsen mäts som total sannolikhetsförflyttning mellan fryst modell och marknadsankare. "
                    "Tabellen används för att se om större modelljusteringar faktiskt blir bättre eller sämre – inte för att optimera en ny tröskel i efterhand."
                )

        abl = signal_ablation_summary(st.session_state.facit_coupons)
        st.markdown("#### Signalablation – vad händer om en verifierad signal tas bort?")
        st.write(abl["lesson"])
        if abl["rows"]:
            adf = pd.DataFrame([{
                "Signal": r["name"],
                "Observationer": r["observations"],
                "Kuponger": r["coupons"],
                "Brier-bidrag": r["brier_contribution"],
                "Log-loss-bidrag": r["log_loss_contribution"],
                "Hjälpfrekvens": r["help_rate"],
                "Modell vs marknad (Brier)": r["model_vs_market_brier_gain"],
                "Bedömning": r["verdict"],
            } for r in abl["rows"]])
            st.dataframe(adf, use_container_width=True, hide_index=True)
        st.caption(
            "Leave-one-signal-out använder endast kontrafaktiska snapshots som sparades före facit. Signaler kan samverka, så resultatet är marginaldiagnostik och inte ett kausalitetsbevis. "
            "v3.76 ändrar varken model_engine.py eller strategy_engine.py."
        )

        # v3.77: conservative gate before any predictive experiment.
        from market_anchor_decision import market_anchor_decision
        mad = market_anchor_decision(st.session_state.facit_coupons)
        st.markdown("### Market Anchor Decision Lab")
        st.write(
            "Detta är beslutsgrinden mellan diagnostik och ett eventuellt framtida prediktivt experiment. "
            "Den ändrar aldrig modellen automatiskt."
        )
        st.info(f"Beslut: **{mad['status']}**")
        st.write(mad["action"])
        if mad["candidate_experiment"]:
            st.success(f"Tillåten experimentkandidat: **{mad['candidate_experiment']}**")
        for warning in mad["warnings"]:
            st.warning(warning)
        req = mad["requirements"]
        st.caption(
            f"Fasta grindar: minst {req['min_coupons']} kuponger / {req['min_matches']} parade matcher; "
            f"minst {req['min_signal_observations']} signalobservationer över {req['min_signal_coupons']} kuponger; "
            f"minst {req['min_divergence_bucket_matches']} matcher i ett avvikelsesegment. "
            "Blandad evidens = ändra inget. v3.77 ändrar inte model_engine.py eller strategy_engine.py."
        )

        # v3.78: prospective shadow-mode candidate evaluation.
        from predictive_experiment import eligible_shadow_spec, shadow_experiment_summary
        shadow_spec = eligible_shadow_spec(st.session_state.facit_coupons)
        shadow = shadow_experiment_summary(st.session_state.facit_coupons)
        st.markdown("### Predictive Experiment Framework · Shadow mode")
        if shadow_spec:
            st.success(f"Ny prospektiv snapshot kommer även frysa kandidaten: **{shadow_spec['label']}**.")
            st.caption("Kandidaten påverkar inte systemtecken, budget, readiness eller produktionsprognosen.")
        else:
            st.info("Ingen shadow-kandidat aktiveras ännu. v3.77-grinden måste först öppna för ett specifikt experiment.")
        se1,se2,se3 = st.columns(3)
        se1.metric("Färdiga shadow-matcher", shadow["completed_matches"])
        se2.metric("Shadow-kuponger", shadow["completed_coupons"])
        se3.metric("Väntar på facit", shadow["pending_matches"])
        st.info(f"Shadow-status: **{shadow['status']}**")
        st.write(shadow["lesson"])
        if shadow["candidate_brier"] is not None:
            with st.expander("Kandidat vs produktion vs marknad", expanded=False):
                sdf = pd.DataFrame([
                    {"Prognos": "Shadow-kandidat", "Brier": shadow["candidate_brier"], "Log loss": shadow["candidate_log_loss"]},
                    {"Prognos": "Produktion", "Brier": shadow["baseline_brier"], "Log loss": shadow["baseline_log_loss"]},
                    {"Prognos": "Bookmakerankare", "Brier": shadow["market_brier"], "Log loss": shadow["market_log_loss"]},
                ])
                st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.caption(
            f"Bedömningsgrind: minst {shadow['min_matches']} färdiga shadow-matcher över {shadow['min_coupons']} kuponger. "
            "Gamla kuponger backfillas aldrig. Kandidaten kan aldrig automatiskt promoveras till produktion. v3.78 ändrar inte model_engine.py eller strategy_engine.py."
        )

        # v3.79: governance and promotion gate for shadow candidates.
        from shadow_governance import shadow_governance
        gov = shadow_governance(st.session_state.facit_coupons)
        st.markdown("### Shadow Governance · Promotion Gate")
        g1,g2,g3 = st.columns(3)
        g1.metric("Bedömda matcher", gov["completed_matches"])
        g2.metric("Bedömda kuponger", gov["completed_coupons"])
        g3.metric("Kupongbredd", "–" if gov["coupon_win_rate"] is None else f"{gov['coupon_win_rate']*100:.0f}%")
        st.info(f"Governance-beslut: **{gov['decision']}**")
        st.write(gov["action"])
        if gov["relative_brier_gain"] is not None:
            with st.expander("Governance-diagnostik", expanded=False):
                st.write({
                    "Relativ Brier-förbättring": f"{gov['relative_brier_gain']*100:.2f}%",
                    "Relativ log-loss-förbättring": f"{gov['relative_log_loss_gain']*100:.2f}%",
                    "Kuponger där kandidaten vinner på båda måtten": f"{gov['coupon_win_rate']*100:.1f}%",
                    "Största kupongens andel av absolut Brier-effekt": f"{gov['largest_coupon_gain_share']*100:.1f}%",
                })
        greq = gov["requirements"]
        st.caption(
            f"Promotion kräver minst {greq['promotion_matches']} matcher över {greq['promotion_coupons']} kuponger, "
            f"minst {greq['min_relative_brier_gain']*100:.1f}% relativ förbättring på både Brier och log loss, "
            f"vinst på båda måtten i minst {greq['min_coupon_win_rate']*100:.0f}% av kupongerna och högst "
            f"{greq['max_single_coupon_gain_share']*100:.0f}% koncentration till en enskild kupong. Ingen automatisk promotion. "
            "v3.79 ändrar inte model_engine.py eller strategy_engine.py."
        )

        # v3.80: explicit experiment registry and lifecycle.
        from experiment_registry import experiment_lifecycle, experiment_registry_rows
        lifecycle = experiment_lifecycle(st.session_state.facit_coupons)
        st.markdown("### Experiment Lifecycle · Candidate Registry")
        st.info(f"Livscykelstatus: **{lifecycle['status']}**")
        st.write(lifecycle['reason'])
        st.dataframe(pd.DataFrame(experiment_registry_rows(st.session_state.facit_coupons)), use_container_width=True, hide_index=True)
        st.caption(
            "Registret är explicit och kandidaternas parametrar är förhandsregistrerade. Ett förkastat experiment eller ett experiment som nått manuell review-grind får inga nya snapshots. "
            "Ingen status här kan automatiskt ändra produktionsmodellen. v3.80 ändrar inte model_engine.py eller strategy_engine.py."
        )

        # v3.81: fixed prospective cohort robustness diagnostics.
        from experiment_cohorts import cohort_robustness
        cohorts = cohort_robustness(st.session_state.facit_coupons)
        st.markdown("### Shadow Robusthet · Kohorter")
        st.info(f"Robusthetsstatus: **{cohorts['status']}**")
        if cohorts["rows"]:
            with st.expander("Visa fasta robusthetssegment", expanded=False):
                cdf = pd.DataFrame(cohorts["rows"])
                st.dataframe(cdf, use_container_width=True, hide_index=True)
        req = cohorts["requirements"]
        st.caption(
            f"Varje segment kräver minst {req['min_matches']} matcher över {req['min_coupons']} kuponger. "
            "Segmenten är fasta och bygger bara på frysta pre-match-data. Diagnostiken ändrar aldrig produktion eller kandidatparametrar. "
            "v3.81 ändrar inte model_engine.py eller strategy_engine.py."
        )

        from swap_backtest import swap_backtest_results, swap_backtest_summary
        swap_summary = swap_backtest_summary(st.session_state.facit_coupons)
        st.markdown("### Omfördelningsfacit – prospektivt test")
        st.write(
            "Från och med v3.52 sparar Streckverket de faktiska förslag som sida 558 visade före spelstopp. "
            "När facit finns jämförs det primära förslaget med originalsystemet med exakt samma radantal."
        )
        s1,s2,s3,s4 = st.columns(4)
        s1.metric("Kuponger med sparat förslag", swap_summary["prospective_coupons"])
        s2.metric("Primära förslag med facit", swap_summary["completed_primary"])
        s3.metric("Bättre / lika / sämre", f"{swap_summary['better']} / {swap_summary['same']} / {swap_summary['worse']}")
        s4.metric("Räddade / tappade 13", f"{swap_summary['rescued_13']} / {swap_summary['lost_13']}")
        st.info(f"Status: **{swap_summary['status']}**")
        if swap_summary["legacy_without_proposal"]:
            st.caption(
                f"{swap_summary['legacy_without_proposal']} äldre kuponger saknar sparad swap-proveniens. "
                "De räknas inte in genom efterhandsrekonstruktion, eftersom gamla snapshots inte sparade låsningar eller vilket förslag som faktiskt visades."
            )
        if swap_summary["pending_primary"]:
            st.caption(f"{swap_summary['pending_primary']} primära förslag väntar fortfarande på komplett facit.")
        completed_swaps = [r for r in swap_backtest_results(st.session_state.facit_coupons, primary_only=True) if r.completed and r.hit_delta is not None]
        if completed_swaps:
            with st.expander("Visa genomförda primära swap-backtest", expanded=False):
                st.dataframe(pd.DataFrame([{
                    "Kupong": r.coupon_id,
                    "Flytt": f"M{r.donor_match_number} → M{r.recipient_match_number}",
                    "Originalträffar": r.original_hits,
                    "Efter swap": r.swapped_hits,
                    "Skillnad": r.hit_delta,
                    "Utfall": r.verdict,
                    "Förväntad täckningsökning före match": f"{r.predicted_delta_coverage_pp:+.3f} pp",
                } for r in completed_swaps]), use_container_width=True, hide_index=True)
        st.caption(
            "Detta är ett prospektivt systemtest, inte ROI- eller vinstbevis. Färre än 20 färdiga primära förslag ger alltid status FÖR LITE PROSPEKTIV HISTORIK."
        )
    
        quality = observation_quality_summary(st.session_state.facit_coupons)
        st.markdown("### Kontrafaktiskt systemlabb")
        from counterfactual_system_lab import counterfactual_summary
        cf = counterfactual_summary(st.session_state.facit_coupons)
        st.caption("Prospektivt experiment: systemen fryses före spelstopp. Äldre kuponger rekonstrueras inte. Jämförelsen gäller systemtäckning, inte ROI eller bevisad edge.")
        cfa, cfb = st.columns(2)
        cfa.metric("Kuponger med frysta alternativ", cf["prospective_coupons"])
        cfb.metric("Äldre utan alternativ", cf["legacy_without_variants"])
        if cf["variants"]:
            _cf_rows=[]
            for r in cf["variants"]:
                _cf_rows.append({"System":r["label"],"Kuponger":r["coupons"],"Snitt täckta matcher":round(r["mean_hits"],2),"13-rätt täckt":r["thirteen_correct"],"Snittrader":round(r["mean_rows"],1),"Status":r["status"]})
            st.dataframe(pd.DataFrame(_cf_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Inga färdigspelade prospektiva systemalternativ finns ännu.")

        st.markdown("### Strategiliggan – bara rättvisa möten")
        from strategy_league_table import strategy_league
        league = strategy_league(st.session_state.facit_coupons, min_shared=20)
        st.caption(
            "Två strategier jämförs bara på kuponger där båda systemen frystes före spelstopp. "
            "Minst 20 gemensamma färdigspelade kuponger krävs innan ett par får ett ligaresultat. "
            "Ligapoäng beskriver historisk systemtäckning – inte ROI, utdelning eller bevisad edge."
        )
        l1,l2 = st.columns(2)
        l1.metric("Granskningsbara möten", f"{league['qualified_matchups']}/{league['total_matchups']}")
        l2.metric("Minsta gemensamma historik", league['min_shared_coupons'])
        reviewable_rows = [r for r in league['league'] if r['matchups'] > 0]
        if reviewable_rows:
            st.dataframe(pd.DataFrame([{
                "Strategi": r["strategy"], "Möten": r["matchups"], "V": r["wins"],
                "O": r["draws"], "F": r["losses"], "Poäng": r["points"], "Status": r["status"]
            } for r in reviewable_rows]), use_container_width=True, hide_index=True)
        else:
            st.info("Ingen strategipar har ännu 20 gemensamma färdigspelade prospektiva kuponger.")
        if league['matchups']:
            with st.expander("Visa parvisa strategimöten", expanded=False):
                st.dataframe(pd.DataFrame([{
                    "Möte": f"{m.strategy_a} – {m.strategy_b}",
                    "Gemensamma kuponger": m.shared_coupons,
                    "V/O/F ur A-perspektiv": f"{m.wins_a}/{m.draws}/{m.wins_b}",
                    "Snitt träff A/B": f"{m.mean_hits_a:.2f} / {m.mean_hits_b:.2f}",
                    "13 täckt A/B": f"{m.thirteen_a} / {m.thirteen_b}",
                    "Snittrader A/B": f"{m.mean_rows_a:.1f} / {m.mean_rows_b:.1f}",
                    "Resultat": m.matchup_result, "Status": m.status,
                } for m in league['matchups']]), use_container_width=True, hide_index=True)
        st.caption(
            "Identiska system kan bära flera strategialias från v3.54. Då räknas samma utfall som ett verkligt oavgjort möte. "
            "Äldre saknade alias rekonstrueras bara när den faktiskt använda strategin finns explicit sparad i kupongen."
        )

        st.markdown("### Strategirobusthet – fungerar mönstret i olika kupongmiljöer?")
        from strategy_robustness import strategy_robustness
        robustness = strategy_robustness(st.session_state.facit_coupons, min_shared=20)
        st.caption(
            "Kupongmiljöerna bestäms av frysta förhandsdata, inte av resultatet: favoritbild, publikträngsel och "
            "modell–bookmaker-avvikelse. Minst 20 gemensamma färdigspelade kuponger krävs inom varje segment. "
            "Dessutom krävs minst två olika miljöer inom samma dimension innan robusthet ens kan granskas."
        )
        r1,r2,r3 = st.columns(3)
        r1.metric("Segmentmöten med nog historik", robustness["qualified_matchups"])
        r2.metric("Minst gemensamma kuponger/segment", robustness["min_shared_per_segment"])
        r3.metric("Automatisk strategiändring", "NEJ")
        if robustness["strategies"]:
            st.dataframe(pd.DataFrame([{
                "Strategi": r["strategy"],
                "Granskade segment": r["qualified_segments"],
                "Kontrasterande dimensioner": r["contrasting_dimensions"],
                "V/O/F": f"{r['wins']}/{r['draws']}/{r['losses']}",
                "Status": r["status"],
            } for r in robustness["strategies"]]), use_container_width=True, hide_index=True)
        else:
            st.info("För lite prospektiv historik för segmenterad strategijämförelse ännu.")
        if robustness["matchups"]:
            with st.expander("Visa strategimöten per kupongmiljö", expanded=False):
                st.dataframe(pd.DataFrame([{
                    "Dimension": m.dimension, "Miljö": m.segment,
                    "Möte": f"{m.strategy_a} – {m.strategy_b}",
                    "Gemensamma kuponger": m.shared_coupons,
                    "V/O/F ur A-perspektiv": f"{m.wins_a}/{m.draws}/{m.wins_b}",
                    "Snitt träff A/B": f"{m.mean_hits_a:.2f} / {m.mean_hits_b:.2f}",
                    "Resultat": m.matchup_result, "Status": m.status,
                } for m in robustness["matchups"]]), use_container_width=True, hide_index=True)
        with st.expander("Så definieras kupongmiljöerna", expanded=False):
            st.write("**Favoritdominerad:** minst 7 av 13 matcher har publikfavorit på minst 60 %.")
            st.write("**Öppen:** högst 3 av 13 matcher har publikfavorit på minst 60 %. Mellanläget kallas balanserad.")
            st.write("**Publikträngsel:** bygger på snittet av 1 minus normaliserad entropi i streckfördelningen. Hög ≥ 0,28, låg ≤ 0,16.")
            st.write("**Modell–marknad-gap:** snittlig total-variation mellan modellens och bookmakerbasens 1/X/2-sannolikheter. Hög ≥ 0,08, låg ≤ 0,04.")
            st.caption("Trösklarna är fasta i förväg och optimeras inte efter facit. Segmentresultat får inte automatiskt ändra strategin. Ingen ROI eller edge påstås.")
        
        st.markdown("### Multipeltest-vakt – hur mycket kan vara slump?")
        from strategy_confidence import strategy_confidence
        confidence = strategy_confidence(st.session_state.facit_coupons, min_shared=30)
        st.caption(
            "När många strategier och kupongmiljöer testas ökar risken för falska fynd. Här används ett exakt parat "
            "teckentest på kupongnivå och Holm-korrigering över hela den aktuella testfamiljen. Minst 30 gemensamma "
            "färdigspelade kuponger krävs per segmenttest. Detta är ett diagnostiskt skydd, inte formellt bevis på edge."
        )
        c1,c2,c3 = st.columns(3)
        c1.metric("Test i familjen", confidence["family_size"])
        c2.metric("Kvar efter Holm", confidence["significant_after_holm"])
        c3.metric("Automatisk strategiändring", "NEJ")
        st.info(f"**{confidence['status']}**")
        if confidence["tests"]:
            st.dataframe(pd.DataFrame([{
                "Dimension": t.dimension,
                "Miljö": t.segment,
                "Möte": f"{t.strategy_a} – {t.strategy_b}",
                "Gemensamma kuponger": t.shared_coupons,
                "Avgörande kuponger": t.decisive_coupons,
                "V/F ur A-perspektiv": f"{t.wins_a}/{t.wins_b}",
                "Snitt träffskillnad A–B": round(t.mean_hit_delta_a_minus_b, 3),
                "Rått p": "–" if t.raw_p is None else round(t.raw_p, 4),
                "Holm p": "–" if t.holm_p is None else round(t.holm_p, 4),
                "Riktning": t.direction,
                "Status": t.status,
            } for t in confidence["tests"]]), use_container_width=True, hide_index=True)
        else:
            st.info("Ännu finns inga segment med minst 30 gemensamma färdigspelade prospektiva kuponger.")
        st.caption(
            "Oavgjorda kuponger räknas i historiken men ger ingen riktning i teckentestet. Holm-korrigeringen begränsar "
            "familjevis felrisk när många segment granskas samtidigt. Positiv signal här får fortfarande inte tolkas som ROI, "
            "kausalitet eller bevisad spel-edge."
        )

        st.markdown("### Walk-forward – klarar strategivalet senare kuponger?")
        from strategy_walk_forward import walk_forward_validation
        walk = walk_forward_validation(
            st.session_state.facit_coupons, min_train=30, test_block=10, min_oos=20
        )
        st.caption(
            "Äldre gemensamma kuponger används först för att välja historiskt starkare strategi. Valet fryses sedan och "
            "testas på nästa 10 senare kuponger. Därefter får träningshistoriken växa och nästa block testas. "
            "Kuponger utan läsbar sparad tidsstämpel exkluderas – ordningen gissas aldrig från kupong-ID."
        )
        w1,w2,w3,w4 = st.columns(4)
        w1.metric("Kronologiska kuponger", walk["chronological_coupons"])
        w2.metric("Granskningsbara par", walk["reviewable_pairs"])
        w3.metric("Signaler efter Holm", walk["signals_after_holm"])
        w4.metric("Automatisk strategiändring", "NEJ")
        st.info(f"**{walk['status']}**")
        if walk["excluded_without_valid_chronology"]:
            st.caption(
                f"{walk['excluded_without_valid_chronology']} kuponger kan inte användas i walk-forward eftersom säker kronologi saknas."
            )
        if walk["pairs"]:
            st.dataframe(pd.DataFrame([{
                "Möte": f"{p.strategy_a} – {p.strategy_b}",
                "Gemensamma kronologiska": p.shared_chronological_coupons,
                "Fold": p.folds,
                "Beslutade fold": p.decided_folds,
                "Senare testkuponger": p.oos_coupons,
                "V/O/F för valt system": f"{p.oos_wins_selected}/{p.oos_draws}/{p.oos_losses_selected}",
                "Snitt träffskillnad": "–" if p.mean_oos_hit_delta_selected_minus_other is None else round(p.mean_oos_hit_delta_selected_minus_other, 3),
                "Val A/B i fold": f"{p.selection_a_folds}/{p.selection_b_folds}",
                "Rått p": "–" if p.raw_p is None else round(p.raw_p, 4),
                "Holm p": "–" if p.holm_p is None else round(p.holm_p, 4),
                "Status": p.status,
            } for p in walk["pairs"]]), use_container_width=True, hide_index=True)
        else:
            st.info("Ännu finns inte tillräckligt många kronologiska prospektiva systemalternativ för ett walk-forward-test.")
        if walk["folds"]:
            with st.expander("Visa walk-forward-fold", expanded=False):
                st.dataframe(pd.DataFrame([{
                    "Möte": f"{f.strategy_a} – {f.strategy_b}",
                    "Äldre träningskuponger": f.train_coupons,
                    "Senare testkuponger": f.test_coupons,
                    "Vald från äldre historik": f.selected_strategy,
                    "V/O/F i senare block": f"{f.test_wins_selected}/{f.test_draws}/{f.test_losses_selected}",
                    "Snittskillnad i senare block": "–" if f.test_mean_hit_delta_selected_minus_other is None else round(f.test_mean_hit_delta_selected_minus_other, 3),
                    "Sista träning": f.train_end_coupon_id,
                    "Första test": f.test_start_coupon_id,
                    "Sista test": f.test_end_coupon_id,
                } for f in walk["folds"]]), use_container_width=True, hide_index=True)
        st.caption(
            "Detta är tidsordnad prospektiv diagnostik, inte ett formellt out-of-sample-bevis. Träningsregeln kan uppdateras "
            "mellan blocken och fotbollskuponger är inte garanterat oberoende. En positiv signal får därför inte tolkas som ROI eller bevisad edge."
        )

        st.markdown("### Marknadsoenighet – när hjälper eller stjälper modellavvikelsen?")
        from market_disagreement_validation import market_disagreement_validation
        disagreement = market_disagreement_validation(
            st.session_state.facit_coupons, min_matches=100, min_coupons=20
        )
        st.caption(
            "Den här analysen använder bara prospektiva snapshots från v3.58 eller senare där bookmaker-spridning faktiskt sparades före facit. "
            "Äldre kuponger fylls inte i i efterhand. Varje marknadsmiljö kräver minst 100 färdigspelade matcher från minst 20 separata kuponger innan den blir granskningsbar."
        )
        md1,md2,md3,md4 = st.columns(4)
        md1.metric("Prospektiva matcher", disagreement["prospective_matches"])
        md2.metric("Prospektiva kuponger", disagreement["prospective_coupons"])
        md3.metric("Granskningsbara miljöer", f"{disagreement['reviewable_segments']}/3")
        md4.metric("Automatisk modellvikt", "NEJ")
        if disagreement["segments"]:
            st.dataframe(pd.DataFrame([{
                "Marknadsmiljö": x.segment,
                "Matcher": x.matches,
                "Kuponger": x.coupons,
                "Modell träff %": "–" if x.model_pick_accuracy is None else round(100*x.model_pick_accuracy, 1),
                "Marknad träff %": "–" if x.market_pick_accuracy is None else round(100*x.market_pick_accuracy, 1),
                "Brier-fördel modell": "–" if x.brier_gain is None else round(x.brier_gain, 4),
                "Log loss-fördel modell": "–" if x.logloss_gain is None else round(x.logloss_gain, 4),
                "Snitt modell–marknad-gap": "–" if x.mean_model_market_gap is None else f"{100*x.mean_model_market_gap:.1f} %",
                "Status": x.status,
            } for x in disagreement["segments"]]), use_container_width=True, hide_index=True)
        if disagreement["contrast_status"] == "KONTRAST GRANSKNINGSBAR":
            delta = disagreement["high_vs_disagree_brier_gain_delta"]
            st.info(
                "HÖG samstämmighet och OENIG marknad har nu båda tillräcklig historik för en direkt diagnostisk kontrast. "
                + ("Skillnaden i modellens Brier-fördel (OENIG minus HÖG) är " + f"{delta:+.4f}." if delta is not None else "")
            )
        else:
            st.info("Ännu finns inte tillräcklig prospektiv historik i både HÖG och OENIG marknad för en seriös kontrast.")
        if disagreement["excluded_legacy_coupons"]:
            st.caption(
                f"{disagreement['excluded_legacy_coupons']} äldre kuponger exkluderas eftersom marknadsoenighet inte sparades prospektivt före v3.58. "
                "Streckverket rekonstruerar inte den informationen i efterhand."
            )
        if disagreement["excluded_without_diagnostics"]:
            st.caption(
                f"{disagreement['excluded_without_diagnostics']} färdigspelade matcher från nyare kuponger saknar tillräcklig bookmaker-spridningsdata och exkluderas."
            )
        with st.expander("Explorativt: modellgap × marknadsmiljö", expanded=False):
            st.write(
                "Här delas modell–marknad-gap i fasta förhandsgränser: lågt ≤4 %, normalt 4–8 %, högt ≥8 %. "
                "Cellerna är explorativa och kräver samma 100 matcher + 20 kuponger för att bli granskningsbara. Resultatet används inte för modellvikt."
            )
            st.dataframe(pd.DataFrame([{
                "Marknadsmiljö": g.market_context,
                "Modellgap": g.gap_bucket,
                "Matcher": g.matches,
                "Kuponger": g.coupons,
                "Brier-fördel modell": "–" if g.brier_gain is None else round(g.brier_gain, 4),
                "Status": g.status,
            } for g in disagreement["gap_context"]]), use_container_width=True, hide_index=True)
        st.caption(
            "Positiv Brier-fördel betyder bara att modellens sparade sannolikheter historiskt varit bättre än marknadens i just gruppen. "
            "Analysen bevisar inte ROI, edge eller kausalitet och får inte ändra prognosen automatiskt."
        )

        st.markdown("### Sen marknad efter fryst prognos")
        try:
            from late_market_benchmark import late_market_benchmark, observation_rows as late_market_observation_rows
            _all_market_points = facit_store.load_market_points() if facit_store is not None else []
            _late_bench = late_market_benchmark(
                st.session_state.facit_coupons, _all_market_points, min_matches=100, min_coupons=20
            )
        except Exception as exc:
            _late_bench = None
            st.caption(f"Historisk senmarknadsbenchmark kunde inte beräknas: {type(exc).__name__}: {exc}")
        if _late_bench is not None:
            st.caption(
                "Från v3.61 sparas en explicit länk mellan prognossnapshot och dess marknadstidslinje. Endast sådana prospektiva snapshots används. "
                "Äldre kuponger bakåtkompletteras inte. En senare punkt måste vara faktiskt sparad efter prognosen och före avspark; snapshot-punkten i sig räknas inte."
            )
            lm1,lm2,lm3,lm4 = st.columns(4)
            lm1.metric("Senare marknadspunkter", _late_bench["prospective_matches"])
            lm2.metric("Kuponger", _late_bench["prospective_coupons"])
            _toward_rate = _late_bench["toward_rate"]
            lm3.metric("Rörde sig mot modellen", "–" if _toward_rate is None else f"{100*_toward_rate:.1f} %")
            lm4.metric("Automatisk modellvikt", "NEJ")
            st.dataframe(pd.DataFrame([{
                "Startgap": seg.gap_bucket,
                "Matcher": seg.matches,
                "Kuponger": seg.coupons,
                "Mot/från/neutral": f"{seg.toward}/{seg.away}/{seg.neutral}",
                "Mot modellen %": "–" if seg.toward_rate is None else round(100*seg.toward_rate, 1),
                "Snitt gapförändring pp": "–" if seg.mean_alignment_change_pp is None else round(seg.mean_alignment_change_pp, 2),
                "Snitt största marknadsrörelse pp": "–" if seg.mean_abs_market_move_pp is None else round(seg.mean_abs_market_move_pp, 2),
                "Status": seg.status,
            } for seg in _late_bench["segments"]]), use_container_width=True, hide_index=True)
            if _late_bench["excluded_legacy_coupons"]:
                st.caption(
                    f"{_late_bench['excluded_legacy_coupons']} äldre kuponger saknar den explicita tidslinjelänken och exkluderas. "
                    "Streckverket gissar inte vilken historisk marknadstidslinje de hörde till."
                )
            if _late_bench["excluded_no_later_point"]:
                st.caption(
                    f"{_late_bench['excluded_no_later_point']} match-snapshots saknar en faktiskt senare verifierad marknadspunkt före avspark och ger därför ingen observation."
                )
            with st.expander("Visa prospektiva observationer", expanded=False):
                _obs = list(_late_bench["observations"])
                if _obs:
                    st.dataframe(pd.DataFrame(late_market_observation_rows(_obs)), use_container_width=True, hide_index=True)
                else:
                    st.info("Ännu finns inga prospektiva snapshot → senare marknad-observationer. Fortsätt spara marknadspunkter efter prognossnapshot och före avspark.")
            st.caption(
                "Att en senare bookmakerbild rör sig mot Streckverkets tidigare modell är marknadsdiagnostik – inte facit, ROI eller bevisad edge. "
                "Varje gapgrupp kräver minst 100 matcher från minst 20 kuponger innan den markeras GRANSKNINGSBAR."
            )

        st.markdown("### Hur bra är själva historikunderlaget?")
        st.write(
            "Detta mäter **datakvaliteten när prognosen sparades**, inte hur bra tipset var. "
            "Poängen bygger bara på metadata som faktiskt finns: marknadsproveniens, oddsens färskhet, antal bookmakers, "
            "matchningssäkerhet, tid till avspark och streckens färskhet."
        )
        q1,q2,q3,q4 = st.columns(4)
        q1.metric("Snittkvalitet", "–" if quality["average_score"] is None else f"{quality['average_score']:.0f}/100")
        q2.metric("Hög kvalitet", quality["high"])
        q3.metric("Medel", quality["medium"])
        q4.metric("Låg/mycket låg", int(quality["low"])+int(quality["very_low"]))
        st.caption("Äldre observationer kan få låg poäng därför att metadata inte sparades då. Streckverket gissar inte bakåt i tiden för att fylla luckorna.")
    
        from snapshot_timing import summarize_snapshot_timing
        timing = summarize_snapshot_timing(st.session_state.facit_coupons)
        st.markdown("### När sparades prognoserna?")
        st.write(
            "Tidpunkten spelar roll. En prognos sparad långt före avspark ska inte blandas ihop med en prognos sparad nära avspark. "
            "Streckverket kallar inte nära-avspark-data för closing line om ett faktiskt verifierat closing-odds saknas."
        )
        t1,t2,t3,t4 = st.columns(4)
        t1.metric("Känd timing", f"{timing['known']}/{timing['count']}")
        t2.metric("Inom 1 h", timing["within_1h"])
        t3.metric("Inom 3 h", timing["within_3h"])
        t4.metric("Efter avspark", timing["post_kickoff"])
        if timing["unknown"]:
            st.caption(f"{timing['unknown']} observationer saknar tillräcklig tidsmetadata. De räknas inte som nära-avspark-observationer.")
    
        from validation_reality import assess_validation_reality
        reality = assess_validation_reality(st.session_state.facit_coupons, min_matches=100, min_coupons=20)
        st.markdown("### Produktens verklighetskontroll")
        st.write(
            "Innan historiken tolkas frågar Streckverket om underlaget faktiskt är tillräckligt oberoende och spårbart. "
            "Hundra matcher från några få kuponger är inte samma sak som hundra oberoende försök."
        )
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Verifierade matcher", reality.eligible_matches)
        r2.metric("Separata kuponger", reality.eligible_coupons)
        r3.metric("Högre datakvalitet", reality.high_quality_matches)
        r4.metric("Känd modellversion", f"{reality.known_version_coupons}/{reality.eligible_coupons}")
        st.info(f"**{reality.status}** · {reality.biggest_gap}")
        if reality.unknown_version_coupons:
            st.caption(
                "Äldre snapshots utan modellversion får ligga kvar i historiken, men Streckverket gissar inte vilken modellgeneration som skapade dem. "
                "Nya snapshots versionsmärks automatiskt från v3.43."
            )
        st.caption("Verklighetskontrollen kan aldrig sätta Edge=bevisad. Den avgör bara om historiken är mogen nog att granskas seriöst.")

        from model_version_benchmark import model_version_benchmarks, public_version_rows
        version_rows = model_version_benchmarks(st.session_state.facit_coupons, min_sample=100, min_coupons=20)
        st.markdown("### Modellversioner – jämför inte äpplen med päron")
        st.write(
            "När Streckverkets modell ändras ska den nya modellen följas som en egen generation. "
            "En version med få kuponger får visas, men får inte rankas som bättre eller sämre än en annan version."
        )
        if version_rows:
            st.dataframe(pd.DataFrame(public_version_rows(version_rows)), use_container_width=True, hide_index=True)
            comparable_versions = sum(1 for row in version_rows if row.comparable)
            if comparable_versions < 2:
                st.info(
                    "Det finns ännu inte minst två modellversioner med tillräckligt oberoende historik för en seriös versionsjämförelse. "
                    "Fortsätt samla facit per version i stället för att dra slutsatser tidigt."
                )
            else:
                st.warning(
                    "Jämförbara versioner betyder bara att datamängden räcker för granskning. Skillnaderna kan fortfarande bero på kupongmix, liga, timing och marknadsläge – inte bara på modellen."
                )

            from model_change_registry import change_rows_for_versions
            st.markdown("### Vad ändrades mellan versionerna?")
            st.write(
                "Versionsresultat blir användbara först när vi vet vad som faktiskt ändrades. "
                "Registret är explicit: saknas en dokumenterad ändringspost visas den som okänd i stället för att Streckverket gissar."
            )
            change_rows = change_rows_for_versions([row.version for row in version_rows])
            st.dataframe(pd.DataFrame(change_rows), use_container_width=True, hide_index=True)
            st.caption(
                "'Ändrade prognosen? NEJ' betyder att releasen bara ändrade metod, validering eller spårbarhet. "
                "Det gör att sådana releaser inte felaktigt tolkas som nya prognosmodeller."
            )

        from verification_engine import benchmark_against_market
        bench = benchmark_against_market(st.session_state.facit_coupons, min_sample=100)
        quality_bench = benchmark_against_market(st.session_state.facit_coupons, min_sample=100, min_quality_score=60)
        near_kickoff_bench = benchmark_against_market(st.session_state.facit_coupons, min_sample=100, max_hours_before_kickoff=3)
        st.markdown("### Verifiering mot bookmaker-marknaden")
        st.write(
            "Det här är Streckverkets viktigaste kontrollfråga: **har våra egna justeringar faktiskt varit bättre än att bara följa marknadens sannolikheter?** "
            "Jämförelsen använder bara färdigspelade matcher med en användbar marknadsbas och ändrar aldrig modellen automatiskt."
        )
        st.info(f"**{bench.verdict}** · {bench.plain_summary}")
        v1,v2,v3,v4 = st.columns(4)
        v1.metric("Verifierade matcher", bench.matches)
        v2.metric("Kuponger", bench.coupons)
        v3.metric("Brier-fördel mot marknaden", "–" if bench.brier_gain is None else f"{bench.brier_gain:+.4f}", help="Positivt betyder att Streckverkets sannolikheter varit bättre. Brier mäter hela sannolikhetsfördelningen, inte bara vinnartipset.")
        v4.metric("Senaste 30 %", "–" if bench.recent_brier_gain is None else f"{bench.recent_brier_gain:+.4f}", help="En enkel kontroll av om resultatet även syns i den nyare delen av historiken.")
        if bench.ci_low is not None:
            st.caption(
                f"Diagnostiskt 95 %-intervall för den genomsnittliga Brier-fördelen: {bench.ci_low:+.4f} till {bench.ci_high:+.4f}. "
                "Detta är inte ett formellt bevis på spel-edge eftersom fotbollsmatcher och kuponger inte kan antas vara perfekt oberoende."
            )
        if quality_bench.matches:
            st.caption(
                f"Kvalitetskontroll: {quality_bench.matches} av de verifierade matcherna har observationskvalitet minst 60/100. "
                + ("Brier-fördelen i den gruppen är " + f"{quality_bench.brier_gain:+.4f}." if quality_bench.brier_gain is not None else "")
                + " Detta är diagnostik, inte ett nytt edge-påstående."
            )
        if near_kickoff_bench.matches:
            st.caption(
                f"Tidskontroll: {near_kickoff_bench.matches} verifierade matcher sparades högst 3 timmar före avspark. "
                + ("Brier-fördelen i den gruppen är " + f"{near_kickoff_bench.brier_gain:+.4f}." if near_kickoff_bench.brier_gain is not None else "")
                + " Detta är en nära-avspark-jämförelse, inte verifierad closing-line-data och inte ett nytt edge-påstående."
            )
        if bench.matches and (bench.matches < 100 or not bench.coupon_diversity_ok):
            st.warning(f"Streckverket kräver minst 100 verifierade matcher och {bench.min_coupons_required} separata kuponger innan ett positivt mönster får lyftas. Matcher på samma kupong är inte helt oberoende bevis.")
    
        if perf["model_brier"] is not None:
            st.markdown("#### Är sannolikheterna bra – inte bara vinnartipset?")
            st.write(
                "Vi använder två standardmått. **Lägre är bättre.** De belönar en modell som ger rimliga sannolikheter och straffar den när den är överdrivet säker och har fel."
            )
            b1,b2,b3,b4 = st.columns(4)
            b1.metric("Streckverket · Brier", f"{perf['model_brier']:.3f}")
            b2.metric("Marknaden · Brier", f"{perf['market_brier']:.3f}")
            b3.metric("Streckverket · Log loss", f"{perf['model_log_loss']:.3f}")
            b4.metric("Marknaden · Log loss", f"{perf['market_log_loss']:.3f}")
    
        from learning_diagnostics import diagnostic_segments, recommended_action, strongest_lessons
    
        st.markdown("### Vad fungerar egentligen?")
        st.write(
            "Här delar Streckverket upp historiken i olika **typer av situationer**. Vi frågar till exempel: "
            "blir modellen faktiskt bättre när den går emot folkets favorit, eller när den ändrar marknadens grundbedömning mycket?"
        )
        st.caption(
            "Positiv förbättring betyder att Streckverkets sannolikheter historiskt har varit bättre än marknadsbasen. "
            "Det är inte samma sak som att just det spelet vinner nästa gång."
        )
        diag_rows = diagnostic_segments(st.session_state.facit_coupons, min_sample=30)
        lessons = strongest_lessons(diag_rows)
        st.info(lessons["summary"])
        if diag_rows:
            diag_df = pd.DataFrame([
                {
                    "Situation": r.segment,
                    "Matcher": r.matches,
                    "Streckverket": f"{r.model_brier:.3f}",
                    "Marknaden": f"{r.market_brier:.3f}",
                    "Förbättring": f"{100*r.improvement:+.1f} p.e.",
                    "Bedömning": r.verdict,
                }
                for r in diag_rows
            ])
            st.dataframe(diag_df, use_container_width=True, hide_index=True)
            st.write(f"**Nästa modellåtgärd:** {recommended_action(diag_rows)}")
            st.caption(
                "Streckverket ändrar aldrig modellvikter automatiskt bara för att en historisk grupp ser bra eller dålig ut. "
                "Först krävs tillräckligt många matcher och därefter kontroll på ny data som inte användes när slutsatsen drogs."
            )
    
        from factor_learning import factor_lesson, factor_scorecard, proposed_weight_actions
    
        st.markdown("### Vilka analysfaktorer hjälper faktiskt?")
        st.write(
            "När en prognos sparas efter en riktig multi-source-analys sparar Streckverket också ett **före/utan-faktorn-facit**. "
            "Efter matchen kan vi därför fråga: blev sannolikheterna bättre eller sämre av exempelvis hemmaform, skador eller lagstyrka?"
        )
        factor_rows = factor_scorecard(st.session_state.facit_coupons, min_sample=30)
        if factor_rows:
            st.info(factor_lesson(factor_rows))
            factor_df = pd.DataFrame([
                {
                    "Faktor": r["name"],
                    "Matcher": r["matches"],
                    "Hjälpte": f"{100*r['help_rate']:.0f} %",
                    "Brier-förbättring": f"{r['mean_brier_gain']:+.4f}",
                    "Genomsnittlig modellflytt": f"{100*r['mean_shift']:.2f} p.e.",
                    "Oberoende källnamn": r["sources"],
                    "Bedömning": r["verdict"],
                }
                for r in factor_rows
            ])
            st.dataframe(factor_df, use_container_width=True, hide_index=True)
            st.caption(
                "Positiv Brier-förbättring betyder att modellen historiskt blev bättre när faktorn fanns med än i den sparade motberäkningen utan just den faktorn. "
                "Det bevisar inte att faktorn ensam orsakade förbättringen; faktorer kan samverka."
            )
            actions = proposed_weight_actions(factor_rows, min_sample=100)
            if actions:
                with st.expander("Granskningsförslag för modellvikter – ändras aldrig automatiskt", expanded=False):
                    for row in actions:
                        st.write(f"**{row['name']}** · {row['matches']} matcher · {row['action']}")
                    st.warning(
                        "Ett förslag här är bara en hypotes. Innan en vikt ändras ska den testas på ny data som inte användes för att skapa förslaget."
                    )
        else:
            st.info(
                "Ännu finns inget faktorfacit. För att bygga det behöver du först köra en riktig multi-source-analys och sedan spara prognosen före spelstopp. "
                "Gamla facitfiler fungerar fortfarande, men de innehåller inte historiska faktorbidrag."
            )
    
        cal = calibration_rows(st.session_state.facit_coupons)
        if cal:
            with st.expander("Avancerat: träffar 60 % verkligen ungefär 60 % av gångerna?", expanded=False):
                st.write(
                    "Detta kallas kalibrering. Om Streckverket ofta säger 60 % ska sådana utfall på lång sikt inträffa ungefär 60 % av gångerna. "
                    "Små datamängder kan svänga kraftigt, så vi drar inga stora slutsatser tidigt."
                )
                cal_df = pd.DataFrame(cal)
                cal_df["Modellens snitt"] = cal_df["modell_snitt"].map(lambda x: f"{100*x:.1f} %")
                cal_df["Verkligt utfall"] = cal_df["utfall_snitt"].map(lambda x: f"{100*x:.1f} %")
                cal_df["Skillnad"] = cal_df["kalibreringsfel"].map(lambda x: f"{100*x:.1f} p.e.")
                st.dataframe(
                    cal_df[["intervall","antal","Modellens snitt","Verkligt utfall","Skillnad"]].rename(columns={"intervall":"Prognosintervall","antal":"Observationer"}),
                    use_container_width=True,
                    hide_index=True,
                )
    
    st.caption(
        "v3.3 bygger vidare på lagringsmotorn: lokal SQLite fungerar direkt och PostgreSQL/Neon aktiveras när STRECKVERKET_DATABASE_URL finns i Streamlit Secrets. "
        "Appen påstår aldrig att lokal Streamlit-disk är permanent. JSON-exporten finns kvar som portabel säkerhetskopia."
    )
    
    
