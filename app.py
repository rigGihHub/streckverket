import pandas as pd
import streamlit as st

from core import (
    SIGNS, classify_match, optimize_system,
    spike_score, value_index, best_upgrades, market_probabilities
)
from demo_data import get_demo_matches
from evidence import DEFAULT_CATEGORY_WEIGHTS
from team_matching import TeamCandidate, match_coupon_teams
from enrichment import fetch_football_data_teams, fetch_team_finished_matches, summarize_team_form, form_signal_from_summaries
from model_engine import fetch_competition_standings, build_match_signals, enriched_probabilities, probability_delta
from source_consensus import provider_matrix
from data_sources import (
    parse_coupon_csv, fetch_the_odds_api, match_odds_to_coupon,
    fetch_svenskaspel_current, DataSourceError
)

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
st.caption("v2.1.0 · Streckverket · Så spelar vi idag")
st.info("v1.6 mäter när korrekt information kom i förhållande till marknad och streck, samtidigt som gränssnittet fått en tydligare retrokupong-känsla.")

if "coupon" not in st.session_state:
    st.session_state.coupon = get_demo_matches()
    st.session_state.data_mode = "Demo"
    st.session_state.source_message = "Demodata används. Inga siffror ska tolkas som aktuell kupong."

with st.sidebar:
    st.header("Data")
    mode = st.radio("Kupongkälla", ["Svenska Spel", "CSV-import", "Demo"], index=["Svenska Spel","CSV-import","Demo"].index(st.session_state.data_mode) if st.session_state.data_mode in ["Svenska Spel","CSV-import","Demo"] else 0)

    if mode == "Svenska Spel":
        st.caption("Hämtar aktuell 13-matcherskupong, Svenska folkets streck och Svenska Spels 1X2-odds när de finns.")
        if st.button("Hämta aktuell kupong", type="primary"):
            coupon, status = fetch_svenskaspel_current()
            if status.ok and coupon:
                st.session_state.coupon = coupon
                st.session_state.data_mode = "Svenska Spel"
                st.session_state.source_message = status.message
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
                coupon = parse_coupon_csv(df_upload)
                st.session_state.coupon = coupon
                st.session_state.data_mode = "CSV-import"
                st.session_state.source_message = "Kupong importerad från användarens CSV."
                st.success("13 matcher importerade.")
            except Exception as exc:
                st.error(str(exc))

    else:
        if st.button("Ladda demokupong"):
            st.session_state.coupon = get_demo_matches()
            st.session_state.data_mode = "Demo"
            st.session_state.source_message = "Demodata används."
            st.rerun()

    st.divider()
    st.header("Odds")
    odds_key = st.text_input("The Odds API-nyckel", type="password", help="Lämna tomt för att inte hämta externa odds.")
    default_sports = "soccer_epl,soccer_efl_champ,soccer_england_league1,soccer_england_league2"
    sports_text = st.text_area("Ligor (sport keys)", value=default_sports, height=90)
    regions = st.text_input("Bookmakerregioner", value="uk,eu")
    if st.button("Hämta & matcha odds"):
        events, status = fetch_the_odds_api(odds_key, [x.strip() for x in sports_text.split(",") if x.strip()], regions)
        if not status.ok:
            st.error(status.message)
        else:
            matched = match_odds_to_coupon(st.session_state.coupon, events)
            updated = []
            for m in st.session_state.coupon:
                if m.number in matched:
                    e = matched[m.number]
                    new_odds = tuple(e["odds"])
                    updated.append(type(m)(m.number,m.home,m.away,new_odds,m.public,market_probabilities(new_odds)))
                else:
                    updated.append(m)
            st.session_state.coupon = updated
            st.session_state.source_message = f"{status.message} Matchade {len(matched)}/13 kupongmatcher utan fuzzy-gissning."
            if matched:
                st.success(st.session_state.source_message)
            else:
                st.warning(st.session_state.source_message)

    st.divider()
    st.header("System")
    budget = st.select_slider("Budget (kr = rader)", options=[16,32,64,128,256,512,1024,2048], value=128)
    strategy = st.radio("Strategi", ["MAX 13", "VÄRDE"], horizontal=True)

matches = st.session_state.coupon

if st.session_state.data_mode == "Demo":
    st.warning("DEMO-LÄGE: Matcherna och siffrorna är testdata – inte aktuell Stryktipskupong.")
else:
    st.info(st.session_state.source_message)

with st.expander("Datatillförlitlighet", expanded=False):
    st.write(f"**Kupongkälla:** {st.session_state.data_mode}")
    st.write(f"**Status:** {st.session_state.source_message}")
    st.caption("Appen vägrar göra fuzzy namnmatchning av lag mot oddskällan. Omatchade matcher lämnas orörda i stället för att gissas.")

with st.sidebar:
    st.subheader("Egna låsningar")
    locks = {}
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



# Retro Tipcentral: make the most important betting decisions visible before the full coupon.
_spik_rows = []
_falla_rows = []
_skrall_rows = []
for _m in matches:
    _fav = max(range(3), key=lambda i: _m.model[i])
    _edge = (_m.model[_fav] - _m.public[_fav]) * 100
    _cls = classify_match(_m.model, _m.public)
    _row = (_m, _fav, _edge, _cls)
    if "spik" in _cls.lower():
        _spik_rows.append(_row)
    if "fäll" in _cls.lower():
        _falla_rows.append(_row)
    if "skräll" in _cls.lower():
        _skrall_rows.append(_row)

def _retro_pick(rows, fallback):
    if rows:
        return max(rows, key=lambda x: abs(x[2]))
    return fallback

_all_rows=[]
for _m in matches:
    _fav=max(range(3), key=lambda i:_m.model[i])
    _all_rows.append((_m,_fav,(_m.model[_fav]-_m.public[_fav])*100,classify_match(_m.model,_m.public)))
_best_spik=_retro_pick(_spik_rows,max(_all_rows,key=lambda x:x[0].model[x[1]]))
_best_falla=_retro_pick(_falla_rows,min(_all_rows,key=lambda x:x[2]))
_best_skrall=_retro_pick(_skrall_rows,max(_all_rows,key=lambda x:max((x[0].model[i]-x[0].public[i]) for i in range(3))))

def _callout(row, kind, title):
    _m,_fav,_edge,_cls=row
    _sign=("1","X","2")[_fav]
    return f'<div class="retro-callout {kind}"><b>{title}: {_m.number}. {_m.home}–{_m.away}</b><small>TECKEN {_sign} · {_cls.upper()} · EDGE {_edge:+.1f} p.e.</small></div>'


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

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs(["Så spelar vi idag", "System", "Spikar", "Skrällar & fällor", "Matchanalys", "Datagranskning", "Modell-labb", "Databerikning", "Källor", "Match Intelligence", "Sista kontrollen", "Analysera aktuell kupong", "Information Edge", "Kupongverkstad", "Budgetverkstad"])


with tab0:
    from decision_page import summarize_decisions

    st.markdown("### Så spelar Streckverket idag")
    st.caption("En beslutsvy: vad vi hade gjort, varför och hur systemet ser ut inom din budget.")

    dc1, dc2 = st.columns([1,1])
    with dc1:
        play_budget = st.number_input(
            "Budget för dagens system",
            min_value=1, max_value=100000,
            value=int(st.session_state.get("decision_budget", 192)),
            step=1, key="decision_budget"
        )
    with dc2:
        play_strategy = st.radio(
            "Spelstrategi", ["MAX 13","VÄRDE"],
            horizontal=True, key="decision_strategy"
        )

    summary = summarize_decisions(matches, int(play_budget), play_strategy, locks)
    ds = summary["system"]

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Rader", ds["rows"])
    k2.metric("Kostnad", f"{ds['cost']:.0f} kr")
    k3.metric("13-rättstäckning", f"{ds['coverage']*100:.2f} %")
    k4.metric("Oanvänd budget", f"{ds['unused_budget']:.0f} kr")

    st.markdown("#### Streckverkets beslut")
    c1,c2,c3,c4 = st.columns(4)

    with c1:
        st.markdown("**SPIKAR**")
        if summary["spikes"]:
            for d in summary["spikes"][:3]:
                st.write(f"{d.number}. {d.home} – {d.away}: **{d.recommended}**")
                st.caption(f"{d.classification} · modell {d.confidence*100:.0f}%")
        else:
            st.caption("Ingen tydlig spik enligt nuvarande modell.")

    with c2:
        st.markdown("**MÅSTE GARDERAS**")
        if summary["must_guard"]:
            for d in summary["must_guard"][:3]:
                st.write(f"{d.number}. {d.home} – {d.away}")
                st.caption(d.classification)
        else:
            st.caption("Ingen match sticker ut som måstegardering.")

    with c3:
        st.markdown("**FÄLLOR**")
        if summary["traps"]:
            for d in summary["traps"][:3]:
                st.write(f"{d.number}. {d.home} – {d.away}")
                st.caption(f"Folket: {d.public_favorite} {d.public_favorite_share*100:.0f}%")
        else:
            st.caption("Ingen tydlig överstreckad favorit.")

    with c4:
        st.markdown("**SKRÄLLAR**")
        if summary["upsets"]:
            for d in summary["upsets"][:3]:
                st.write(f"{d.number}. {d.home} – {d.away}: **{d.recommended}**")
                st.caption(f"Edge {d.edge*100:+.1f} p.e.")
        else:
            st.caption("Ingen tydlig skrällsignal.")

    st.markdown("#### Rekommenderat system")
    system_rows=[]
    for m, sel in zip(matches, ds["selections"]):
        system_rows.append({
            "Nr":m.number,
            "Match":f"{m.home} – {m.away}",
            "Tecken":"".join(sel),
            "Klass":classify_match(m.model,m.public),
            "Modell":f"{m.model[0]*100:.0f}/{m.model[1]*100:.0f}/{m.model[2]*100:.0f}",
            "Streck":f"{m.public[0]*100:.0f}/{m.public[1]*100:.0f}/{m.public[2]*100:.0f}",
        })
    st.dataframe(pd.DataFrame(system_rows),use_container_width=True,hide_index=True)

    if st.button("Skicka systemet till Kupongverkstaden", key="decision_to_coupon"):
        st.session_state.manual_coupon=[tuple(x) for x in ds["selections"]]
        for m,sel in zip(matches,ds["selections"]):
            st.session_state[f"manual_coupon_{m.number}_{m.home}_{m.away}"]=list(sel)
        st.success("Systemet är överfört till Kupongverkstaden.")

    st.info(
        "Beslutssidan sammanfattar modellens nuvarande läge. Den ska inte tolkas som en garanti; "
        "saknad eller gammal data sänker kvaliteten och bör granskas i Match Intelligence/Sista kontrollen."
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
                    delta=probability_delta(match.market,final)
                    out_rows.append({
                        "Nr":match.number,"Match":f"{match.home} – {match.away}",
                        "Marknad":f"{match.market[0]*100:.1f}/{match.market[1]*100:.1f}/{match.market[2]*100:.1f}",
                        "v0.8":f"{final[0]*100:.1f}/{final[1]*100:.1f}/{final[2]*100:.1f}",
                        "Δ1":f"{delta[0]*100:+.1f} p.e.","ΔX":f"{delta[1]*100:+.1f} p.e.","Δ2":f"{delta[2]*100:+.1f} p.e.",
                        "Styrka H/B":f"{hs.strength:.2f}/{aws.strength:.2f}" if hs and aws else "saknas",
                    })
                    for ar in audit:
                        audit_rows.append({"Nr":match.number,"Signal":ar["label"],"Källa":ar["source"],"Styrka":round(float(ar["strength"]),3),"Förklaring":ar["explanation"]})
                if out_rows:
                    st.dataframe(pd.DataFrame(out_rows),use_container_width=True,hide_index=True)
                    with st.expander("Visa faktor-för-faktor audit"):
                        st.dataframe(pd.DataFrame(audit_rows),use_container_width=True,hide_index=True)
                    st.warning("Detta är fortfarande en kandidatmodell. Den ska backtestas mot marknaden innan vikterna höjs eller används som facit.")
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
    from one_click import OneClickConfig, run_one_click
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
        cfg=OneClickConfig(
            odds_api_key=oc_odds.strip(), football_data_key=oc_fd.strip(), api_football_key=oc_af.strip(),
            odds_sport_keys=tuple(x.strip() for x in oc_sports.split(",") if x.strip()), odds_regions=oc_regions.strip() or "uk,eu", max_competitions=oc_max,
        )
        try:
            result=run_one_click(cfg,coupon=st.session_state.coupon,fetch_coupon=use_current)
            st.session_state["one_click_result"]=result
            st.session_state.coupon=result.enriched
            st.session_state.data_mode="Multi-source"
            st.session_state.source_message="v1.2 multi-source-analys genomförd"
            st.success("Analysen slutfördes. Kupongen i sessionen har uppdaterats med de verifierade signaler som gick att hämta.")
        except Exception as exc:
            st.error(f"Analysen stoppades: {type(exc).__name__}: {exc}")
    result=st.session_state.get("one_click_result")
    if result:
        st.markdown("#### Källstatus")
        st.dataframe(pd.DataFrame([{"Källa":x.name,"Status":"OK" if x.ok else "Saknas/fel","Matchat":f"{x.matched}/{x.attempted}","Meddelande":x.message} for x in result.stages]),use_container_width=True,hide_index=True)
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
