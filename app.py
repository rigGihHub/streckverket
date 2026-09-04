from pool_value import system_pool_value, top_coupon_cleaners
from ui_navigation import ALL_TABS, beginner_flow, hidden_tabs_css
from analysis_entry import SOURCE_SECRET_KEYS, source_availability, source_status_text
from analysis_controller import build_one_click_config, execute_one_click
from coupon_state import commit_analysis_state, ensure_coupon_state, set_coupon_state
import pandas as pd
import streamlit as st

from core import (
    SIGNS, classify_match, optimize_system,
    spike_score, value_index, best_upgrades
)
from demo_data import get_demo_matches
from evidence import DEFAULT_CATEGORY_WEIGHTS
from team_matching import TeamCandidate, match_coupon_teams
from enrichment import fetch_football_data_teams, fetch_team_finished_matches, summarize_team_form, form_signal_from_summaries
from model_engine import fetch_competition_standings, build_match_signals, enriched_probabilities, probability_delta
from explainable_model import explain_probability_change, plain_delta, plain_summary
from source_consensus import provider_matrix
from coupon_loader import load_current_coupon, load_csv_coupon, load_demo_coupon, merge_external_odds
from readiness_diagnostics import build_readiness_diagnostics, diagnostics_rows, source_rows
from data_quality_history import build_quality_snapshot, append_quality_snapshot, load_quality_history, source_history_rows, competition_history_rows, competition_source_history_rows, failure_reason_history_rows

st.set_page_config(page_title="Streckverket", page_icon="🎯", layout="wide")
st.markdown("""
<style>
:root{--bg:#121713;--panel:#1b241d;--paper:#efe7d2;--ink:#20231f;--green:#334c39;--gold:#e2b84d;--line:#546155;}
html,body,[data-testid="stAppViewContainer"]{background:radial-gradient(circle at 20% 0%,rgba(226,184,77,.06),transparent 28%),linear-gradient(180deg,#111611 0%,#161c17 100%);}
[data-testid="stHeader"]{background:rgba(17,22,17,.88)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#172019,#101510);border-right:1px solid #364337}
[data-testid="stSidebar"] *{color:#e8e1d1}.block-container{max-width:1500px;padding-top:1rem;padding-bottom:3rem}
.retro-hero{border:1px solid #546155;background:linear-gradient(135deg,rgba(226,184,77,.08),transparent 32%),linear-gradient(180deg,#243126,#19221b);padding:22px 26px 18px;margin:2px 0 14px;box-shadow:0 8px 28px rgba(0,0,0,.24);position:relative;overflow:hidden}
.retro-hero:after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(255,255,255,.015) 0 1px,transparent 1px 4px);pointer-events:none}
.retro-kicker{color:#d9cba7;font:700 12px/1.2 "Courier New",monospace;letter-spacing:2px}.retro-title{color:#f3ead2;font:900 46px/1 Impact,"Arial Narrow",sans-serif;letter-spacing:1px;margin-top:5px;text-shadow:2px 2px 0 #0d120e}.retro-title span{display:inline-block;margin-left:8px;padding:3px 9px;background:#e2b84d;color:#1a1e19;border:2px solid #1a1e19;transform:rotate(-2deg);box-shadow:3px 3px 0 #101410}.retro-sub{margin-top:9px;color:#aab6ab;font:700 13px/1.3 "Courier New",monospace}
h1,h2,h3{font-family:Impact,"Arial Narrow",sans-serif!important;color:#f0e8d5!important}p,li,label,.stMarkdown{color:#e7e1d3}
[data-testid="stMetric"]{background:linear-gradient(180deg,#f1ead9,#e4dac3);border:2px solid #242b25;border-radius:2px!important;box-shadow:4px 4px 0 #0d110e;padding:10px 14px}[data-testid="stMetric"] *{color:#20231f!important}[data-testid="stMetricLabel"] p{font-family:"Courier New",monospace!important;text-transform:uppercase;font-weight:700!important;font-size:11px!important}
div[data-testid="stDataFrame"]{border:1px solid #59665a;background:#171e18;padding:4px;box-shadow:4px 4px 0 rgba(0,0,0,.24)}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#111711;padding:5px;border:1px solid #39463b;overflow-x:auto}.stTabs [data-baseweb="tab"]{background:#242f26;border:1px solid #445247;border-radius:1px;color:#ddd4bf;font-family:"Courier New",monospace;font-weight:700;font-size:12px;padding:8px 12px}.stTabs [aria-selected="true"]{background:#e2b84d!important;color:#171a16!important;border-color:#e2b84d!important}
.stButton>button{border-radius:1px!important;border:2px solid #171b17!important;background:#e2b84d!important;color:#171a16!important;font-weight:900!important;box-shadow:3px 3px 0 #0b0f0c!important}.stButton>button:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #0b0f0c!important}
div[data-testid="stAlert"]{border-radius:1px!important;border:1px solid #5a665b!important;background:#202920!important}div[data-baseweb="select"]>div,input,textarea{border-radius:1px!important;background:#202920!important;border-color:#526052!important;color:#eee6d4!important}hr{border-color:#475448!important}
.retro-ticket{background:#eee5cf;color:#20231f;border:2px solid #1f261f;padding:14px 16px;margin:7px 0;box-shadow:4px 4px 0 #0f130f;position:relative}.retro-ticket:before,.retro-ticket:after{content:"";position:absolute;width:10px;height:10px;border-radius:50%;background:#161c17;top:50%;transform:translateY(-50%)}.retro-ticket:before{left:-7px}.retro-ticket:after{right:-7px}.retro-nr{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;background:#334c39;color:#fff;border:2px solid #1d251e;font:900 16px Impact,sans-serif;margin-right:10px}.retro-match{font:900 18px Impact,"Arial Narrow",sans-serif;color:#1d211d}.retro-meta{font:700 11px "Courier New",monospace;color:#5a6259;margin-top:7px}.retro-sign{display:inline-block;padding:3px 7px;margin-left:5px;background:#e2b84d;color:#1b1e1a;border:1px solid #20251f;font:900 15px Impact,sans-serif}.retro-section{font:900 15px "Courier New",monospace;color:#e2b84d;letter-spacing:1px;text-transform:uppercase;border-bottom:1px dashed #566357;padding-bottom:5px;margin:10px 0 12px}
@media(max-width:700px){.block-container{padding-left:.65rem;padding-right:.65rem}.retro-title{font-size:34px}.retro-hero{padding:17px 16px 14px}.stTabs [data-baseweb="tab"]{padding:9px 10px;min-height:42px}.stButton>button{min-height:46px;width:100%}[data-testid="stMetric"]{padding:8px 10px}}

.retro-callout-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:10px 0 18px}
.retro-callout{padding:13px 14px;border:2px solid #20261f;box-shadow:4px 4px 0 #0b0f0c;background:#eee5cf;color:#20231f}
.retro-callout.spik{border-top:7px solid #45634d}.retro-callout.falla{border-top:7px solid #b85143}.retro-callout.skrall{border-top:7px solid #e2b84d}
.retro-callout b{font:900 17px "Arial Narrow",Impact,sans-serif}.retro-callout small{display:block;margin-top:5px;font:700 11px "Courier New",monospace;color:#586058}
.retro-board{background:#172019;border:1px solid #4d5b4f;padding:12px;margin:10px 0}
.retro-board-row{display:grid;grid-template-columns:42px minmax(170px,1fr) 72px 72px 72px 92px;gap:6px;align-items:center;padding:7px 4px;border-bottom:1px dashed #465248}
.retro-board-row:last-child{border-bottom:0}.retro-board-row.head{color:#d9cba7;font:700 10px "Courier New",monospace;text-transform:uppercase}
.rb-nr{background:#e2b84d;color:#1b1e1a;text-align:center;font:900 15px Impact,sans-serif;padding:7px 2px}
.rb-team{color:#eee6d4;font-weight:800}.rb-sign{text-align:center;border:1px solid #536153;padding:6px 2px;color:#eee6d4;font:900 15px Impact,sans-serif}
.rb-sign.on{background:#eee5cf;color:#1d211d;border-color:#eee5cf}.rb-tag{text-align:right;color:#d6cba9;font:700 10px "Courier New",monospace}
@media(max-width:700px){.retro-callout-grid{grid-template-columns:1fr}.retro-board-row{grid-template-columns:34px minmax(120px,1fr) 42px 42px 42px}.rb-tag{grid-column:2/6;text-align:left;padding-bottom:4px}}

</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="retro-hero">
  <div class="retro-kicker">13 MATCHER · ANALYS · VÄRDE · SYSTEM</div>
  <div class="retro-title">STRECK<span>VERKET</span></div>
  <div class="retro-sub">Vi jagar inte favoriter. Vi jagar felstreck.</div>
</div>
""", unsafe_allow_html=True)
st.caption("v3.21.0 · Streckverket · Verifierade supporterkällor")

ensure_coupon_state(st.session_state, load_demo_coupon())

def _configured_secrets():
    values = {}
    for _key in SOURCE_SECRET_KEYS.values():
        try:
            values[_key] = st.secrets.get(_key, "")
        except Exception:
            values[_key] = ""
    return values

with st.sidebar:
    st.header("Kom igång")
    expert_mode = st.toggle("Expertläge", value=False, help="Visar alla analysverktyg. Normalläget visar bara det du behöver för att välja ett system.")
    if not expert_mode:
        for _step in beginner_flow():
            st.caption(_step)
    st.divider()
    st.subheader("1. Kupong")
    mode = st.radio("Kupongkälla", ["Svenska Spel", "CSV-import", "Demo"], index=["Svenska Spel","CSV-import","Demo"].index(st.session_state.data_mode) if st.session_state.data_mode in ["Svenska Spel","CSV-import","Demo"] else 0)

    if mode == "Svenska Spel":
        st.caption("Hämtar aktuell 13-matcherskupong, Svenska folkets streck och Svenska Spels 1X2-odds när de finns.")
        if st.button("Hämta aktuell kupong", type="primary"):
            coupon, status = load_current_coupon()
            if status.ok and coupon:
                set_coupon_state(st.session_state, coupon, data_mode="Svenska Spel", source_message=status.message)
                st.success(status.message)
                st.rerun()
            else:
                st.error(status.message)
                st.info("CSV-import och demo finns kvar som reserv. Appen använder aldrig en ofullständig kupong.")

    elif mode == "CSV-import":
        st.caption("Kräver: nr, hemma, borta, streck1, streckx, streck2. Odds1/oddsX/odds2 är valfria.")
        upload = st.file_uploader("Ladda upp kupong-CSV", type=["csv"])
        if upload is not None:
            try:
                df_upload = pd.read_csv(upload)
                coupon = load_csv_coupon(df_upload)
                set_coupon_state(
                    st.session_state, coupon, data_mode="CSV-import",
                    source_message="Kupong importerad från användarens CSV.",
                )
                st.success("13 matcher importerade.")
            except Exception as exc:
                st.error(str(exc))

    else:
        if st.button("Ladda demokupong"):
            set_coupon_state(
                st.session_state, load_demo_coupon(), data_mode="Demo",
                source_message="Demodata används.",
            )
            st.rerun()

    st.divider()
    with st.expander("⚙️ Odds & datakällor", expanded=False):
        st.caption("Avancerat. Behövs bara när du vill komplettera kupongen med externa bookmakerodds.")
        odds_key = st.text_input("The Odds API-nyckel", type="password", help="Lämna tomt för att inte hämta externa odds.")
        default_sports = "soccer_epl,soccer_efl_champ,soccer_england_league1,soccer_england_league2"
        sports_text = st.text_area("Ligor (sport keys)", value=default_sports, height=80)
        regions = st.text_input("Bookmakerregioner", value="uk,eu")
        if st.button("Hämta & matcha odds"):
            _odds_result = merge_external_odds(
                st.session_state.coupon, odds_key,
                [x.strip() for x in sports_text.split(",") if x.strip()], regions,
            )
            if not _odds_result.status.ok:
                st.error(_odds_result.status.message)
            else:
                set_coupon_state(
                    st.session_state, _odds_result.coupon, data_mode=st.session_state.data_mode,
                    source_message=_odds_result.message,
                )
                if _odds_result.matched_count:
                    st.success(st.session_state.source_message)
                else:
                    st.warning(st.session_state.source_message)

    st.divider()
    st.subheader("2. Budget")
    budget = st.select_slider("Hur mycket vill du högst spela för?", options=[16,32,64,128,256,512,1024,2048], value=128, help="Maximalt antal kronor/rader som systemet får använda i denna version.")
    strategy = st.radio("Hur ska systemet prioritera?", ["MAX 13", "VÄRDE"], horizontal=True, help="MAX 13 prioriterar högsta beräknade chans att täcka 13 matcher. VÄRDE tar större hänsyn till hur andra spelare har streckat.")

matches = st.session_state.coupon
if st.session_state.pop("analysis_stale_notice", None):
    st.warning("Kupongen har ändrats sedan senaste analysen. Den gamla analysen har därför tagits bort.")
_market_missing = [m for m in matches if not getattr(m, "market_available", True)]
if _market_missing and st.session_state.data_mode != "Demo":
    st.error(
        f"MARKNADSODDS SAKNAS för {len(_market_missing)}/13 matcher. Streckverket kan visa en preliminär struktur, "
        "men kupongen ska inte betraktas som spelklar förrän riktiga odds har hämtats. Appen använder inte 3,00–3,00–3,00 som om det vore verkliga marknadsodds."
    )

if st.session_state.data_mode == "Demo":
    st.warning("DEMO-LÄGE: Matcherna och siffrorna är testdata – inte aktuell Stryktipskupong.")
else:
    st.info(st.session_state.source_message)

with st.expander("Datatillförlitlighet", expanded=False):
    st.write(f"**Kupongkälla:** {st.session_state.data_mode}")
    st.write(f"**Status:** {st.session_state.source_message}")
    _dur = st.session_state.get("one_click_duration_seconds")
    if _dur is not None:
        st.caption(f"Senaste fulla analys tog {_dur:.1f} sekunder. Detta mäts för att hitta verkliga prestandaproblem innan vi optimerar.")
    st.caption("Appen vägrar göra fuzzy namnmatchning av lag mot oddskällan. Omatchade matcher lämnas orörda i stället för att gissas.")

with st.sidebar:
    locks = {}
    with st.expander("🔒 Egna låsningar", expanded=False):
        st.caption("Valfritt. Lås tecken bara när du själv vill styra systemet.")
        for m in matches:
            choice = st.multiselect(f"{m.number}. {m.home}–{m.away}", SIGNS, default=[], key=f"lock_{m.number}_{m.home}_{m.away}", placeholder="Ingen låsning")
            if choice:
                locks[m.number] = tuple(choice)

system = optimize_system(matches, budget, strategy, locks)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Systemkostnad", f"{system['rows']} kr")
c2.metric("Modellens 13-rättstäckning", f"{100*system['coverage']:.2f} %")
c3.metric("Slumpmässig täckning", f"{100*system['random_coverage']:.4f} %")
uplift = system["coverage"]/system["random_coverage"] if system["random_coverage"] else 0
c4.metric("Relativ mot slump", f"{uplift:.1f}×")

st.caption("Täckningen är en modelluppskattning och antar i denna version oberoende matchutfall. Den är inte en vinstgaranti.")



# Retro Tipcentral: three distinct decisions with sign logic tailored to each role.
_spik_rows = []
_falla_rows = []
_skrall_rows = []
_all_spikes = []
_all_traps = []
_all_upsets = []
for _m in matches:
    _cls = classify_match(_m.model, _m.public)
    _model_fav = max(range(3), key=lambda i: _m.model[i])
    _public_fav = max(range(3), key=lambda i: _m.public[i])
    _spike_edge = (_m.model[_model_fav] - _m.public[_model_fav]) * 100
    _trap_edge = (_m.model[_public_fav] - _m.public[_public_fav]) * 100
    _underdogs = [i for i in range(3) if i != _public_fav]
    _upset_sign = max(_underdogs, key=lambda i: _m.model[i] - _m.public[i])
    _upset_edge = (_m.model[_upset_sign] - _m.public[_upset_sign]) * 100

    _spike_row = (_m, _model_fav, _spike_edge, _cls)
    _trap_row = (_m, _public_fav, _trap_edge, _cls)
    _upset_row = (_m, _upset_sign, _upset_edge, _cls)
    _all_spikes.append(_spike_row)
    _all_traps.append(_trap_row)
    _all_upsets.append(_upset_row)
    if "spik" in _cls.lower():
        _spik_rows.append(_spike_row)
    if "fäll" in _cls.lower():
        _falla_rows.append(_trap_row)
    if "skräll" in _cls.lower():
        _skrall_rows.append(_upset_row)

def _pick_distinct(primary, fallback, used, score, reverse=True):
    candidates = sorted(primary or fallback, key=score, reverse=reverse)
    for row in candidates:
        if row[0].number not in used:
            used.add(row[0].number)
            return row
    return candidates[0]

_used_matches = set()
_best_spik = _pick_distinct(
    _spik_rows, _all_spikes, _used_matches,
    score=lambda x: (x[0].model[x[1]], x[2]), reverse=True
)
_best_falla = _pick_distinct(
    _falla_rows, _all_traps, _used_matches,
    score=lambda x: x[2], reverse=False
)
_best_skrall = _pick_distinct(
    _skrall_rows, _all_upsets, _used_matches,
    score=lambda x: x[2], reverse=True
)

def _callout(row, kind, title):
    _m, _sign_idx, _edge, _cls = row
    _sign = ("1", "X", "2")[_sign_idx]
    if kind == "falla":
        detail = f"ÖVERSTRECKAD {_sign} · {_cls.upper()} · AVVIKELSE {_edge:+.1f} p.e."
    elif kind == "skrall":
        detail = f"VÄRDETECKEN {_sign} · {_cls.upper()} · EDGE {_edge:+.1f} p.e."
    else:
        detail = f"SPIKTECKEN {_sign} · {_cls.upper()} · EDGE {_edge:+.1f} p.e."
    return f'<div class="retro-callout {kind}"><b>{title}: {_m.number}. {_m.home}–{_m.away}</b><small>{detail}</small></div>'


st.markdown("""
<div style="display:flex;gap:8px;flex-wrap:wrap;margin:2px 0 14px">
  <span style="font:700 11px 'Courier New',monospace;border:1px solid #657266;padding:5px 8px;color:#d9cba7">MARKNAD SOM BAS</span>
  <span style="font:700 11px 'Courier New',monospace;border:1px solid #657266;padding:5px 8px;color:#d9cba7">STRECK SOM MOTSTÅNDARE</span>
  <span style="font:700 11px 'Courier New',monospace;border:1px solid #657266;padding:5px 8px;color:#d9cba7">DATA FÖRE MAGKÄNSLA</span>
  <span style="font:700 11px 'Courier New',monospace;border:1px solid #657266;padding:5px 8px;color:#d9cba7">13 RÄTT SOM MÅL</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="retro-section">Tipcentral · dagens beslut</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="retro-callout-grid">'+
    _callout(_best_spik,"spik","SPIK")+
    _callout(_best_falla,"falla","FÄLLA")+
    _callout(_best_skrall,"skrall","SKRÄLL")+
    '</div>',
    unsafe_allow_html=True
)

_board=['<div class="retro-board"><div class="retro-board-row head"><div>#</div><div>Match</div><div>1</div><div>X</div><div>2</div><div>Strategi</div></div>']
for _m,_sel in zip(matches,system["selections"]):
    _cls=classify_match(_m.model,_m.public)
    _cells=[]
    for _s in ("1","X","2"):
        _cells.append(f'<div class="rb-sign {"on" if _s in _sel else ""}">{_s}</div>')
    _board.append(f'<div class="retro-board-row"><div class="rb-nr">{_m.number}</div><div class="rb-team">{_m.home} – {_m.away}</div>{"".join(_cells)}<div class="rb-tag">{_cls.upper()}</div></div>')
_board.append('</div>')
st.markdown("".join(_board),unsafe_allow_html=True)


st.markdown('<div class="retro-section">Kupongen · rekommenderade tecken</div>', unsafe_allow_html=True)
ticket_cols = st.columns(2)
for idx, (m, selection) in enumerate(zip(matches, system["selections"])):
    with ticket_cols[idx % 2]:
        fav = max(range(3), key=lambda i: m.model[i])
        gap = (m.model[fav] - m.public[fav]) * 100
        cls = classify_match(m.model, m.public)
        signs_html = "".join(f'<span class="retro-sign">{s}</span>' for s in selection)
        card_html = f"""<div class="retro-ticket">
            <span class="retro-nr">{m.number}</span>
            <span class="retro-match">{m.home} – {m.away}</span>
            <div class="retro-meta">MODELL {m.model[0]*100:.0f}/{m.model[1]*100:.0f}/{m.model[2]*100:.0f} &nbsp;·&nbsp; STRECK {m.public[0]*100:.0f}/{m.public[1]*100:.0f}/{m.public[2]*100:.0f} &nbsp;·&nbsp; {cls} &nbsp;·&nbsp; EDGE {gap:+.0f} p.e. &nbsp;&nbsp; {signs_html}</div>
        </div>"""
        st.markdown(card_html, unsafe_allow_html=True)


rows = []
for m, selection in zip(matches, system["selections"]):
    market = m.market
    sp_sign, sp_score = spike_score(m.model, m.public, market)
    rows.append({
        "Nr": m.number,
        "Match": f"{m.home} – {m.away}",
        "Modell 1": f"{m.model[0]*100:.0f}%",
        "Modell X": f"{m.model[1]*100:.0f}%",
        "Modell 2": f"{m.model[2]*100:.0f}%",
        "Streck 1": f"{m.public[0]*100:.0f}%",
        "Streck X": f"{m.public[1]*100:.0f}%",
        "Streck 2": f"{m.public[2]*100:.0f}%",
        "Rek": "".join(selection),
        "Klass": classify_match(m.model, m.public),
        "Spikbetyg": f"{sp_sign} · {sp_score}",
    })

st.subheader("Kupongöversikt")
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown(hidden_tabs_css(expert_mode), unsafe_allow_html=True)
if not expert_mode:
    st.info("Normalläge: fem steg räcker. Slå på Expertläge i sidpanelen om du vill se datagranskning, modeller, historik och övriga specialistverktyg.")
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15, tab16, tab17, tab18 = st.tabs(ALL_TABS)


with tab0:
    from decision_page import summarize_decisions
    st.markdown("### 3. Analysera och få ett system")
    _secret_values = _configured_secrets()
    _availability = source_availability(_secret_values)
    st.caption(source_status_text(_availability))
    _previous_result = st.session_state.get("one_click_result")
    if _previous_result is not None and hasattr(_previous_result, "api_stats"):
        _api_stats = _previous_result.api_stats
        st.caption(f"Senaste analys: {_api_stats.network_calls} externa hämtningar · {_api_stats.cache_hits} återanvända svar")
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
    if not all(_availability.values()):
        st.info("Du kan använda grundanalysen även utan alla API-källor. För fullare underlag läggs nycklarna i Streamlit Secrets; Expertläge behövs inte för normal användning.")

    from match_intelligence import build_match_card
    from beginner_ux import (
        coupon_readiness, confidence_words, edge_explanation, glossary,
        plain_classification, selection_explanation, selection_name, sign_meaning,
    )

    st.markdown("### Vad ska jag spela?")
    st.write(
        "Du behöver inte kunna Stryktipset för att använda den här sidan. "
        "Streckverket föreslår ett system, förklarar varför och säger om underlaget är tillräckligt bra för att spela nu."
    )

    with st.expander("📘 Jag är ny – förklara 1, X, 2 och vanliga spelord", expanded=False):
        st.write("**1** betyder att hemmalaget vinner. **X** betyder oavgjort. **2** betyder att bortalaget vinner.")
        for term, text in glossary().items():
            st.markdown(f"**{term}:** {text}")

    dc1, dc2 = st.columns([1,1])
    with dc1:
        play_budget = st.number_input(
            "Hur mycket vill du högst spela för?",
            min_value=1, max_value=100000,
            value=int(st.session_state.get("decision_budget", 192)),
            step=1, key="decision_budget",
            help="Streckverket bygger det bästa system det kan inom den här gränsen. Systemet kan ibland kosta lite mindre eftersom antalet rader ökar i fasta steg."
        )
    with dc2:
        strategy_label = st.radio(
            "Vad är viktigast?",
            ["Störst möjlig chans till 13 rätt", "Jaga undervärderade resultat"],
            horizontal=False, key="decision_strategy_plain",
            help="Första valet prioriterar ren sannolikhet. Det andra vågar oftare gå emot populära tecken när modellen ser spelvärde."
        )
        play_strategy = "MAX 13" if strategy_label.startswith("Störst") else "VÄRDE"

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
    if readiness.status == "SPELKlar".upper():
        st.success(f"🟢 **{readiness.status} · {readiness.score}/100** — {readiness.short_reason}")
    elif readiness.status == "NÄSTAN SPELKLAR":
        st.warning(f"🟡 **{readiness.status} · {readiness.score}/100** — {readiness.short_reason}")
    else:
        st.error(f"🔴 **{readiness.status} · {readiness.score}/100** — {readiness.short_reason}")

    st.caption(
        f"{confidence_words(readiness.score)}. {readiness.ready_matches} av {readiness.total_matches} matcher har minst 50/100 i datakvalitet. "
        "Poängen handlar om hur bra underlaget är – inte om hur säker en fotbollsmatch är."
    )
    if readiness.blockers:
        with st.expander("Vad saknas innan Streckverket känner sig tryggare?", expanded=(readiness.score < 50)):
            for blocker in readiness.blockers:
                st.write(f"• {blocker}")
            if st.session_state.data_mode == "Demo":
                st.write("Börja med **Data → Svenska Spel → Hämta aktuell kupong** i vänsterspalten.")
            else:
                st.write("Tryck **Analysera kupongen** högst upp på denna sida för att hämta och verifiera de informationslager som är konfigurerade.")

    if one_click_result and st.session_state.data_mode != "Demo":
        readiness_diag = build_readiness_diagnostics(
            readiness_cards, getattr(one_click_result, "stages", ()), market_missing_count=_missing_market_count
        )
        with st.expander("Vilken data bromsar kupongen?", expanded=(readiness.status != "SPELKlar".upper())):
            st.write(readiness_diag.priority_text)
            st.dataframe(pd.DataFrame(diagnostics_rows(readiness_diag)), use_container_width=True, hide_index=True)
            st.caption("Täckningsgrad beskriver om informationslagret finns för matcherna. Den säger inte att informationen automatiskt är korrekt eller viktig nog att flytta modellen.")

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


with tab1:
    st.subheader(f"{strategy} · {system['rows']} rader")
    sys_rows = []
    for m, sel, cov in zip(matches, system["selections"], system["per_match_coverage"]):
        sys_rows.append({"Nr":m.number,"Match":f"{m.home} – {m.away}","Tecken":"".join(sel),"Täckt modellsannolikhet":f"{100*cov:.1f}%"})
    st.dataframe(pd.DataFrame(sys_rows), use_container_width=True, hide_index=True)
    cur,nxt,changes,rel = best_upgrades(matches,budget,strategy,locks)
    st.markdown("#### Vad får jag för nästa fördubbling?")
    st.write(f"{cur['rows']} → {nxt['rows']} rader ger enligt modellen {rel*100:.1f}% relativ förbättring av 13-rättstäckningen.")
    for nr,a,b in changes:
        st.write(f"• Match {nr}: {''.join(a)} → {''.join(b)}")

with tab2:
    ranking=[]
    for m in matches:
        sign,score=spike_score(m.model,m.public,m.market)
        i=SIGNS.index(sign)
        ranking.append((score,m.number,m,sign,i))
    ranking.sort(reverse=True,key=lambda x:x[0])
    for score,nr,m,sign,i in ranking[:6]:
        st.markdown(f"**{nr}. {m.home} – {m.away}: {sign} — spikbetyg {score}/100**")
        st.caption(f"Modell {m.model[i]*100:.0f}% · streck {m.public[i]*100:.0f}% · skillnad {(m.model[i]-m.public[i])*100:+.0f} p.e.")

with tab3:
    surprises=[]; traps=[]
    for m in matches:
        vi=value_index(m.model,m.public)
        for i,sign in enumerate(SIGNS):
            if m.public[i] <= .25 and m.model[i] >= .18:
                surprises.append((vi[i],m.model[i]-m.public[i],m.number,sign,m,i))
        fav=max(range(3),key=lambda i:m.public[i]); traps.append((m.public[fav]-m.model[fav],m.number,SIGNS[fav],m,fav))
    surprises.sort(reverse=True,key=lambda x:(x[0],x[1])); traps.sort(reverse=True,key=lambda x:x[0])
    left,right=st.columns(2)
    with left:
        st.markdown("#### Bästa skrällvärden")
        for vi,gap,nr,sign,m,i in surprises[:5]:
            st.write(f"**Match {nr} · {sign}** — modell {m.model[i]*100:.0f}% / streck {m.public[i]*100:.0f}% · värdeindex {vi:.2f}")
    with right:
        st.markdown("#### Största fällorna")
        for gap,nr,sign,m,i in traps[:5]:
            st.write(f"**Match {nr} · {sign}** — streck {m.public[i]*100:.0f}% / modell {m.model[i]*100:.0f}% · överstreckning {gap*100:+.0f} p.e.")

with tab4:
    number=st.selectbox("Välj match",[m.number for m in matches])
    m=next(x for x in matches if x.number==number)
    vi=value_index(m.model,m.public)
    st.markdown(f"### {m.home} – {m.away}")
    st.dataframe(pd.DataFrame({
        "Tecken":SIGNS,"Odds":m.odds,
        "Marknad":[f"{x*100:.1f}%" for x in m.market],
        "Modell":[f"{x*100:.1f}%" for x in m.model],
        "Streck":[f"{x*100:.1f}%" for x in m.public],
        "Värdeindex":[f"{x:.2f}" for x in vi],
    }),use_container_width=True,hide_index=True)
    st.info("v0.8.0 håller marknadsoddsen som ankare. Verifierad lagstyrka, venue-form och frånvaro kan nu användas som konservativa, spårbara korrigeringar.")

with tab5:
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

with tab5:
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


with tab6:
    st.subheader("Modell-labb v0.5")
    st.write("Här separeras signaler som ska **förutsäga matchen** från signaler som främst ska **förklara streckfel**. Det minskar risken att samma information räknas två gånger.")
    st.dataframe(pd.DataFrame([
        ("Marknadsodds", "Prognos", "Ankare", "Bred kollektiv information; bookmaker-marginal tas bort"),
        ("Lagstyrka", "Prognos", "Hög", "Elo/xG eller motståndsjusterad prestationsstyrka"),
        ("Hemma-/bortaform", "Prognos", "Medel", "Venue-specifik, krymps kraftigt vid små urval"),
        ("Skador/avstängningar", "Prognos", "Medel–hög", "Spelarvärde och ersättare, inte antal frånvarande"),
        ("Bekräftad startelva", "Prognos", "Hög nära start", "Skillnaden mot förväntad elva"),
        ("Supporterforum", "Informationsradar", "Mycket låg", "Påverkar inte utan extern verifiering"),
        ("Storklubbs-/favoritbias", "Streckmodell", "Testas separat", "Förklarar folkets streck, inte matchutfallet"),
        ("Odds-/streckrörelse", "Båda", "Hög", "Tidsserie används för late-information och felstreckning"),
    ], columns=["Signal","Roll","Initial vikt","Varför"]), use_container_width=True, hide_index=True)
    st.markdown("#### Viktig metodändring")
    st.write("Form räknas inte som '5 senaste'. Modellen ska separera hemma/borta, justera för motstånd och regressa små urval. Historiska snapshots sparas före spelstopp så att Brier score och log loss kan jämföras mot marknaden. En ny signal behålls bara om den förbättrar out-of-sample-resultat.")
    st.markdown("#### Nästa datakoppling")
    st.write("football-data.org-adaptern i v0.5 kan hämta avslutade lagmatcher med HOME/AWAY-filter. API-Football-adaptern för injuries från v0.4 finns kvar. Nästa steg är säker lag-ID-matchning mellan Svenska Spel-kupongen och dessa datakällor.")


with tab7:
    from competition_discovery import fetch_competitions, build_catalog, discover_coupon, TeamMappingCache

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
                        except Exception:
                            by_comp[cid]={}
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


with tab8:
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
            except Exception:
                _kickoff_ts = None
            for _team, _opp in ((_m.home, _m.away), (_m.away, _m.home)):
                _c = collect_team_pulse(team=_team, opponent=_opp, sources=_supporter_sources, history=_history, kickoff_ts=_kickoff_ts)
                _collections.append(_c)
                if _c.available and st.session_state.data_mode != "Demo":
                    try:
                        _snapshots.append(make_pulse_snapshot(coupon_fingerprint=coupon_fingerprint(matches), match=_m, team=_team, pulse=_c.pulse, data_mode=st.session_state.data_mode))
                    except ValueError:
                        pass
        st.dataframe(pd.DataFrame(collection_rows(_collections)), use_container_width=True, hide_index=True)
        if _snapshots:
            append_pulse_snapshots(_history_path, _snapshots)
            st.success(f"{len(_snapshots)} riktiga Supporter Pulse-observationer sparades före match.")
        elif st.session_state.data_mode == "Demo":
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


with tab9:
    from match_intelligence import build_match_card, card_summary
    st.subheader("Match Intelligence v1.0")
    st.write("Varje match får en readiness-score. Marknaden är ankare; endast verifierade evidenssignaler får flytta 1/X/2. Saknade eller konfliktande källor visas öppet.")
    cards=[]
    for mm in matches:
        cards.append(build_match_card(match_number=mm.number, home=mm.home, away=mm.away, base_market=mm.market))
    frame=[]
    for card in cards:
        r=card_summary(card)
        r["Δ1"] = f"{100*r['Δ1']:+.1f} p.e."
        r["ΔX"] = f"{100*r['ΔX']:+.1f} p.e."
        r["Δ2"] = f"{100*r['Δ2']:+.1f} p.e."
        frame.append(r)
    st.dataframe(pd.DataFrame(frame), use_container_width=True, hide_index=True)
    st.caption("I denna tabell är readiness avsiktligt låg tills externa datapipelines faktiskt har levererat verifierad data. Det är inte ett fel: v1.0 skiljer på att en adapter finns och att matchens data verkligen är hämtad och bekräftad.")
    selected=st.selectbox("Inspektera intelligence-kort", [c.match_number for c in cards], key="intel_match")
    card=next(c for c in cards if c.match_number==selected)
    a,b,c=st.columns(3)
    a.metric("Readiness", f"{card.readiness_score}/100", card.readiness_label)
    b.metric("Verifierade modellsignaler", len(card.used_signals))
    c.metric("Källkonflikter", len(card.conflicts))
    st.write("**Saknade huvudlager:**", ", ".join(card.missing) if card.missing else "Inga")
    st.markdown("#### Pipeline")
    st.dataframe(pd.DataFrame([
        ("1", "Kupong/streck", "Svenska Spel", "Primärdata"),
        ("2", "Marknadsbas", "The Odds API + Svenska Spel", "Robust bookmakerkonsensus"),
        ("3", "Lagstyrka/form", "football-data.org + API-Football", "Korsverifiering där möjligt"),
        ("4", "Frånvaro/startelva", "Officiell klubb/liga + API-Football", "Konfliktkontroll före modellpåverkan"),
        ("5", "Väder/domare/vila", "Open-Meteo + officiell/statistikkälla", "Låg initial vikt; kräver historiskt stöd"),
        ("6", "Forum/socialt", "Flera oberoende communities", "Early warning; ingen direkt påverkan utan verifiering"),
        ("7", "Sannolikhetsjustering", "Evidensmotor", "14 p.e. max flyttad sannolikhetsmassa"),
        ("8", "Systemoptimering", "MAX 13 / VÄRDE", "Global budgetoptimering"),
    ], columns=["Steg","Lager","Källor","Regel"]), use_container_width=True, hide_index=True)


with tab10:
    from datetime import datetime, timezone, timedelta
    from refresh_policy import build_refresh_plan
    from pipeline import run_coupon_pipeline
    from run_history import serialize_run, append_run, load_runs, compare_latest

    st.subheader("Sista kontrollen inför spelstopp")
    st.write("Den här vyn skiljer på **vad modellen tror** och **om datan är tillräckligt färsk för att systemet bör låsas**.")
    deadline = st.datetime_input("Spelstopp", value=datetime.now()+timedelta(hours=12))
    if getattr(deadline, "tzinfo", None) is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    plan=build_refresh_plan(deadline, datetime.now(timezone.utc))
    c1,c2=st.columns(2)
    c1.metric("Läge", plan.urgency)
    c2.metric("Tid till spelstopp", f"{plan.hours_to_deadline:.1f} h")
    st.dataframe(pd.DataFrame([{"Källa":k,"Kontrollintervall":f"{v} min"} for k,v in plan.intervals_minutes.items()]),use_container_width=True,hide_index=True)

    st.markdown("#### Snapshot och ändringslogg")
    st.caption("Snapshoten sparar nuvarande modellstatus. Den hämtar inte dold data och skapar inga påhittade signaler.")
    # En tom provider-lista innebär att vi sparar marknadsbasen/readiness utan att låtsas att externa källor körts.
    current_results=run_coupon_pipeline(matches, [])
    snapshot_path="data/pipeline_runs.json"
    if st.button("Spara kontrollsnapshot"):
        run=serialize_run(datetime.now(timezone.utc).strftime("%Y-%m-%d"), current_results, source=st.session_state.data_mode)
        append_run(snapshot_path, run)
        st.success("Snapshot sparad.")
    runs=load_runs(snapshot_path)
    changes=compare_latest(runs)
    if changes:
        st.warning("ÄNDRAD REKOMMENDATION / MATERIAL FÖRÄNDRING")
        st.dataframe(pd.DataFrame([{**x,"delta_pp":" / ".join(f"{d:+.1f}" for d in x["delta_pp"])} for x in changes]),use_container_width=True,hide_index=True)
    else:
        st.info("Ingen materiell förändring kan visas förrän minst två snapshots finns med förändrade modellvärden.")

    st.markdown("#### Readiness just nu")
    readiness_rows=[]
    for r in current_results:
        readiness_rows.append({"Nr":r.match.number,"Match":f"{r.match.home} – {r.match.away}","Readiness":f"{r.card.readiness_score}/100", "Saknas":", ".join(r.card.missing) or "–", "Källfel":", ".join(r.failed_sources) or "–"})
    st.dataframe(pd.DataFrame(readiness_rows),use_container_width=True,hide_index=True)
    st.warning("Låg readiness betyder inte att marknadsoddsen är värdelösa. Det betyder att de extra informationslagren ännu inte är tillräckligt verifierade för att få stort inflytande.")


with tab11:
    st.subheader("Analysera aktuell kupong · v1.2")
    st.write("Ett knapptryck kör kupong → bookmakerodds → lag/form → fixture → skador/startelva → readiness → modell. Varje extern källa är frivillig och felisoleras.")
    st.info("API-nycklar sparas inte av appen. För en publicerad installation bör de läggas i Streamlit Secrets i stället för att hårdkodas i koden.")
    c1,c2,c3=st.columns(3)
    with c1:
        oc_odds=st.text_input("The Odds API",type="password",key="oc_odds")
    with c2:
        oc_fd=st.text_input("football-data.org",type="password",key="oc_fd")
    with c3:
        oc_af=st.text_input("API-Football",type="password",key="oc_af")
    oc_sports=st.text_area("Odds sport keys",value="soccer_epl,soccer_efl_champ,soccer_england_league1,soccer_england_league2",height=70,key="oc_sports")
    oc_regions=st.text_input("Oddsregioner",value="uk,eu",key="oc_regions")
    oc_max=st.slider("Max tävlingar att skanna",5,50,25,5,key="oc_max")
    use_current=st.checkbox("Hämta om aktuell kupong från Svenska Spel",value=(st.session_state.data_mode!="Demo"),key="oc_fetch_coupon")
    if st.button("Analysera aktuell kupong",type="primary",key="oc_run"):
        cfg=build_one_click_config(
            odds_api_key=oc_odds, football_data_key=oc_fd, api_football_key=oc_af,
            odds_sport_keys=oc_sports.split(","), odds_regions=oc_regions, max_competitions=oc_max,
        )
        try:
            _expert_started_from_demo = (st.session_state.data_mode == "Demo")
            execution=execute_one_click(cfg,coupon=st.session_state.coupon,fetch_coupon=use_current)
            result=execution.result
            commit_analysis_state(
                st.session_state, enriched_coupon=result.enriched, result=result,
                coupon_fingerprint_value=execution.coupon_fingerprint,
                duration_seconds=execution.duration_seconds,
                data_mode="Multi-source", source_message="Multi-source-analys genomförd",
            )
            if (not _expert_started_from_demo) or use_current:
                _quality_snapshot = build_quality_snapshot(
                    coupon_fingerprint=execution.coupon_fingerprint, matches=result.enriched, cards=result.cards,
                    stages=result.stages, data_mode="Multi-source", duration_seconds=execution.duration_seconds, match_provenance=result.match_provenance,
                )
                append_quality_snapshot("data/data_quality_history.json", _quality_snapshot)
            else:
                st.info("Demokupongen analyserades, men sparades inte i historiken över verklig datakvalitet.")
            st.success("Analysen slutfördes. Kupongen i sessionen har uppdaterats med de verifierade signaler som gick att hämta.")
        except Exception as exc:
            st.error(f"Analysen stoppades: {type(exc).__name__}: {exc}")
    result=st.session_state.get("one_click_result")
    if result:
        st.markdown("#### Källstatus")
        _expert_missing_market = sum(not getattr(m, "market_available", True) for m in result.enriched)
        _expert_diag = build_readiness_diagnostics(result.cards, result.stages, market_missing_count=_expert_missing_market)
        st.dataframe(pd.DataFrame(source_rows(_expert_diag)),use_container_width=True,hide_index=True)
        st.info(_expert_diag.priority_text)
        st.markdown("#### Datatäckning per informationslager")
        st.dataframe(pd.DataFrame(diagnostics_rows(_expert_diag)),use_container_width=True,hide_index=True)
        st.caption("En källa som svarar OK men matchar få lag/matcher markeras som låg eller delvis täckning. API-svar och faktisk datatäckning är inte samma sak.")
        _quality_history = load_quality_history("data/data_quality_history.json")
        st.markdown("#### Historisk datakvalitet")
        if _quality_history:
            st.dataframe(pd.DataFrame(source_history_rows(_quality_history)), use_container_width=True, hide_index=True)
            st.caption("Historiska källomdömen visas först efter minst tre riktiga kuponger. En enstaka lyckad eller misslyckad körning räcker inte för slutsatser.")
            st.markdown("##### Liga/tävling")
            st.dataframe(pd.DataFrame(competition_history_rows(_quality_history)), use_container_width=True, hide_index=True)
            st.markdown("##### Exakt källmatchning per liga")
            _competition_source_rows = competition_source_history_rows(_quality_history)
            if _competition_source_rows:
                st.dataframe(pd.DataFrame(_competition_source_rows), use_container_width=True, hide_index=True)
                st.caption("Den här tabellen bygger bara på matchnivådata från v3.17 och framåt. Äldre kuponger räknas inte om i efterhand.")
                st.markdown("##### Varför datakällor misslyckas")
                _failure_rows = failure_reason_history_rows(_quality_history)
                if _failure_rows:
                    st.dataframe(pd.DataFrame(_failure_rows), use_container_width=True, hide_index=True)
                    st.caption("Felorsaker kategoriseras maskinellt från v3.18. Äldre fritextstatusar räknas inte om i efterhand. 'Återkommande problem' kräver minst tre observerade missar.")
                else:
                    st.info("Ingen kategoriserad felhistorik finns ännu. Riktiga analyser från v3.18 börjar bygga underlaget.")
            else:
                st.info("Ingen matchnivåhistorik finns ännu. Nya riktiga analyser från v3.17 börjar bygga detta underlag.")
        else:
            st.info("Ingen riktig datakvalitetshistorik finns ännu. Kör analys på verkliga kuponger för att börja bygga underlag.")
        st.markdown("#### Match readiness")
        st.dataframe(pd.DataFrame([{
            "Nr":c.match_number,"Match":f"{c.home} – {c.away}","Readiness":f"{c.readiness_score}/100 · {c.readiness_label}",
            "Saknas":", ".join(c.missing) if c.missing else "–","Konflikter":len(c.conflicts),"Signaler":len(c.used_signals),
            "Modell 1":f"{c.final_model[0]*100:.1f}%","X":f"{c.final_model[1]*100:.1f}%","2":f"{c.final_model[2]*100:.1f}%",
        } for c in result.cards]),use_container_width=True,hide_index=True)
        st.metric("Matcher med readiness ≥ 50",f"{result.ready_count}/13")
        st.caption("Låg readiness betyder inte att marknadsbasen saknas; det betyder att kompletterande matchinformation ännu inte är tillräckligt verifierad.")


with tab12:
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


with tab13:
    from interactive_system import evaluate_interactive_system, rank_next_upgrades

    st.markdown("### Kupongverkstad")
    st.write(
        "Överstyr Streckverkets system direkt. Varje match måste ha minst ett tecken. "
        "Radantal, kostnad och modellens uppskattade 13-rättstäckning räknas om direkt."
    )

    if "manual_coupon" not in st.session_state or len(st.session_state.manual_coupon) != len(matches):
        st.session_state.manual_coupon = [tuple(x) for x in system["selections"]]

    top_a, top_b = st.columns(2)
    with top_a:
        if st.button("Återställ till Streckverkets system", key="manual_reset"):
            st.session_state.manual_coupon = [tuple(x) for x in system["selections"]]
            st.rerun()
    with top_b:
        st.caption("Kostnadsmodellen följer nuvarande appprincip: 1 rad = 1 kr.")

    manual = []
    for i, m in enumerate(matches):
        defaults = list(st.session_state.manual_coupon[i])
        chosen = st.multiselect(
            f"{m.number}. {m.home} – {m.away}",
            SIGNS,
            default=defaults,
            key=f"manual_coupon_{m.number}_{m.home}_{m.away}",
            help=f"Modell: {m.model[0]*100:.0f}/{m.model[1]*100:.0f}/{m.model[2]*100:.0f} · Streck: {m.public[0]*100:.0f}/{m.public[1]*100:.0f}/{m.public[2]*100:.0f}"
        )
        if not chosen:
            chosen = defaults or [SIGNS[max(range(3), key=lambda j: m.model[j])]]
            st.warning(f"Match {m.number} måste ha minst ett tecken. Föregående val behålls.")
        manual.append(tuple(chosen))

    st.session_state.manual_coupon = manual
    manual_eval = evaluate_interactive_system(matches, manual)

    ma, mb, mc = st.columns(3)
    ma.metric("Rader", manual_eval.rows)
    mb.metric("Kostnad", f"{manual_eval.cost:.0f} kr")
    mc.metric("13-rättstäckning", f"{manual_eval.coverage*100:.2f} %")

    st.markdown("#### Bästa nästa gardering")
    upgrades = rank_next_upgrades(matches, manual)
    if upgrades:
        best = upgrades[0]
        st.success(
            f"Match {best.match_number}: {best.home} – {best.away} · lägg till **{best.add_sign}**. "
            f"{best.rows_before} → {best.rows_after} rader (+{best.extra_cost:.0f} kr). "
            f"Modelltäckningen ökar med cirka {best.coverage_gain_pp:.3f} procentenheter."
        )
        rows_upgrade = [{
            "Rang": i+1,
            "Match": f"{u.match_number}. {u.home} – {u.away}",
            "Lägg till": u.add_sign,
            "Ny gardering": "".join(u.new_selection),
            "Extra kr": round(u.extra_cost, 0),
            "Täckningsökning p.e.": round(u.coverage_gain_pp, 4),
            "Marginalnytta / kr": round(u.gain_per_kr, 6),
        } for i,u in enumerate(upgrades[:10])]
        st.dataframe(pd.DataFrame(rows_upgrade), use_container_width=True, hide_index=True)
        st.caption(
            "Rangordningen testar varje möjligt extra tecken mot din nuvarande kupong. "
            "Marginalnytta per krona = ökning av modellens systemtäckning / extra systemkostnad."
        )
    else:
        st.info("Kupongen är redan helgarderad.")

    st.markdown("#### Din kupong")
    manual_rows=[]
    for m, sel in zip(matches, manual_eval.selections):
        manual_rows.append({
            "Nr": m.number,
            "Match": f"{m.home} – {m.away}",
            "Tecken": "".join(sel),
            "Modell 1/X/2": f"{m.model[0]*100:.0f}/{m.model[1]*100:.0f}/{m.model[2]*100:.0f}",
            "Streck 1/X/2": f"{m.public[0]*100:.0f}/{m.public[1]*100:.0f}/{m.public[2]*100:.0f}",
            "Klass": classify_match(m.model, m.public),
        })
    st.dataframe(pd.DataFrame(manual_rows), use_container_width=True, hide_index=True)


with tab14:
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


with tab15:
    from datetime import datetime, timezone
    from facit import (
        aggregate_performance, calibration_rows, dumps_facit, evaluate_coupon,
        loads_facit, make_coupon_snapshot, with_results,
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

    csave1, csave2 = st.columns([1,1])
    with csave1:
        can_save = st.session_state.data_mode != "Demo"
        if st.button(
            "📌 Spara prognosen före spelstopp",
            disabled=not can_save,
            help="Sparar exakt vad modellen och systemet säger just nu. Demodata får inte sparas i riktig historik.",
        ):
            coupon_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            from factor_learning import factor_map_from_cards
            factor_snapshots = {}
            oc_result = st.session_state.get("one_click_result")
            if oc_result and len(getattr(oc_result, "cards", [])) == 13:
                factor_snapshots = factor_map_from_cards(oc_result.cards)
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
            )
            st.session_state.facit_coupons.append(snap)
            try:
                _save_to_history(snap)
                if facit_store is not None and facit_store.persistent_cloud:
                    st.success("Prognosen är sparad i molnhistoriken.")
                else:
                    st.success("Prognosen är sparad. Ladda gärna ner facitfilen som extra säkerhetskopia.")
            except Exception as exc:
                st.warning(f"Prognosen finns i sessionen men databassparningen misslyckades: {type(exc).__name__}: {exc}")
        if not can_save:
            st.caption("Demoläget kan inte sparas som riktigt facit. Hämta en riktig kupong först.")

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
        e4.metric("Marknadens förstaval rätt", f"{latest_eval['market_pick_hits']}/{latest_eval['completed'] or 0}")
        st.write(latest_eval["plain_summary"])

        st.markdown("### Vad har modellen lärt sig hittills?")
        perf = aggregate_performance(st.session_state.facit_coupons)
        p1,p2,p3,p4 = st.columns(4)
        p1.metric("Matcher med facit", perf["matches"])
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
        st.write(f"**Streckverkets försiktiga slutsats:** {perf['lesson']}")

        from verification_engine import benchmark_against_market
        bench = benchmark_against_market(st.session_state.facit_coupons, min_sample=100)
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
        if bench.matches and bench.matches < 100:
            st.warning("Streckverket kräver minst 100 verifierade matcher innan jämförelsen ens får etiketten lovande. Fler matcher är bättre; små historikprov kan lura oss.")

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


with tab16:
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


with tab17:
    st.subheader("Streckverkets modellcoach")
    st.write("Här granskar Streckverket sina egna historiska svagheter. Coachen föreslår vad som bör undersökas – den ändrar aldrig modellen automatiskt.")
    from model_coach import build_model_coach
    coach = build_model_coach(list(st.session_state.get("facit_coupons", [])))
    c1,c2,c3 = st.columns(3)
    c1.metric("Matcher med facit", coach["completed_matches"])
    c2.metric("Mogna faktorer", coach["mature_factors"])
    c3.metric("Granskningspunkter", len(coach["findings"]))
    st.write(f"**Samlad lärdom:** {coach['summary']}")
    st.info(coach["recommended_action"])
    if not coach["findings"]:
        st.warning("Ännu för lite historik för säkra coachråd. Streckverket fortsätter samla facit i stället för att dra slutsatser för tidigt.")
    else:
        import pandas as pd
        st.dataframe(pd.DataFrame([{"Prioritet":x.priority,"Område":x.area,"Status":x.status,"Underlag":x.evidence,"Nästa steg":x.action} for x in coach["findings"]]), use_container_width=True, hide_index=True)
    if coach["weight_actions"]:
        with st.expander("Viktförslag som är mogna nog att TESTAS – inte införas automatiskt"):
            st.dataframe(pd.DataFrame(coach["weight_actions"]), use_container_width=True, hide_index=True)
    st.caption("Coachen skiljer på historisk signal och bevis. Förslag ska valideras på ny, separat data innan modellvikter ändras.")


with tab18:
    st.markdown("### Poolvärdesmotorn")
    st.caption("Här väger Streckverket in hur svenska folket har streckat. Det är en poolvärdesanalys – inte en prognos för exakt utdelning.")
    try:
        pv_system = optimize_system(matches, max_rows=max_rows, strategy="VÄRDE", locks=locks)
        pv = system_pool_value(matches, pv_system["selections"])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Beräknad 13-rättstäckning", f"{pv.model_coverage:.1%}", help="Modellens uppskattning av hur stor sannolikhetsmassa systemet täcker.")
        c2.metric("Folkets kvarvarande massa", f"{pv.public_survival_mass:.1%}", help="Grov proxy för hur stor del av folkets enkelrader som passar systemets val. Lägre kan innebära större unikhet om systemet sitter.")
        c3.metric("Poolhävstång", f"{pv.leverage:.2f}×", help="Modelltäckning delat med folkets kvarvarande massa. Över 1 betyder att systemet täcker mer av vår sannolikhet än av folkets streckmassa.")
        c4.metric("Unikhetsindex", f"{pv.uniqueness_index:.0f}/100", help="Pedagogiskt index byggt på poolhävstång. Det är inte en uppskattad vinstsumma.")
        st.info("Viktigt: Streckverket kan ännu inte räkna ut den verkliga förväntade utdelningen. Jackpot, insatsfördelning, reducerade system och hur spelare kombinerar sina tecken saknas. Måtten här är därför strategiska proxyer, inte kronor i förväntad vinst.")
        st.markdown("#### Kupongrensare med sannolikhetsstöd")
        cleaners = top_coupon_cleaners(matches, 6)
        if cleaners:
            for x in cleaners:
                st.write(f"**Match {x['match']} · {x['sign']} · {x['home']}–{x['away']}** — modellen {x['model']:.0%}, folket {x['public']:.0%}. Tecknet är mindre populärt men har fortfarande tydligt sannolikhetsstöd.")
        else:
            st.write("Inga tydliga kupongrensare hittades med nuvarande krav.")
    except Exception as exc:
        st.warning(f"Poolvärdet kunde inte beräknas: {exc}")
