from datetime import datetime, timezone
from pool_value import system_pool_value, top_coupon_cleaners
from game_theory import strategic_coupon_rows
from ui_navigation import ALL_TABS, beginner_flow, expert_flow, hidden_tabs_css, should_render_tab
from analysis_entry import SOURCE_SECRET_KEYS, source_availability, source_status_text
from analysis_controller import build_one_click_config, execute_one_click
from coupon_state import commit_analysis_state, ensure_coupon_state, set_coupon_state
from first_time_player_ux import resolve_strategy, strategy_labels
from novice_system_board import build_novice_rows, render_novice_system_board
from beginner_ux import CouponReadiness, coupon_readiness, readiness_guidance
from analysis_timing import analysis_timing_advice
from analysis_refresh import choose_refresh_coupon
from analysis_change_report import make_analysis_snapshot, compare_analysis_snapshots
from decision_highlights import build_decision_highlights
from release_info import APP_VERSION, RELEASE_NAME
from data_sources import DataSourceError
import pandas as pd
import streamlit as st

from core import (
    SIGNS, classify_match, optimize_system,
    spike_score, value_index, best_upgrades
)
from demo_data import get_demo_matches
from evidence import DEFAULT_CATEGORY_WEIGHTS
from team_matching import TeamCandidate, match_coupon_teams
from enrichment import fetch_football_data_teams
from source_consensus import provider_matrix
from coupon_loader import load_current_coupon, load_csv_coupon, load_demo_coupon, merge_external_odds
from readiness_diagnostics import build_readiness_diagnostics, diagnostics_rows, source_rows
from data_quality_history import build_quality_snapshot, append_quality_snapshot, load_quality_history, source_history_rows, competition_history_rows, competition_source_history_rows, failure_reason_history_rows

st.set_page_config(page_title="Streckverket", page_icon="🎯", layout="wide")
st.markdown("""<style>
.texttv-market{background:#000;color:#fff;border:2px solid #00f;padding:8px 10px;margin:8px 0;font-family:monospace;border-radius:0}
.texttv-market b{display:block;background:#001a8d;color:#ff0;padding:3px 6px;margin:-8px -10px 6px -10px}
.texttv-market pre{color:#0ff;background:#000;white-space:pre-wrap;font-family:monospace;margin:0;font-size:.86rem;line-height:1.28}
</style>""", unsafe_allow_html=True)

st.markdown("""
<style>
 :root{--bg:#000;--panel:#001b55;--paper:#000;--ink:#fff;--green:#00ff66;--gold:#ffff00;--line:#00ffff;}
html,body,[data-testid="stAppViewContainer"]{background:#000!important;}
[data-testid="stHeader"]{background:#000}
[data-testid="stSidebar"]{background:#000;border-right:4px solid #0044cc}
[data-testid="stSidebar"] *{color:#fff}.block-container{max-width:1500px;padding-top:1rem;padding-bottom:3rem}
.retro-hero{border:0;background:#001b7a;padding:14px 18px;margin:2px 0 14px;box-shadow:none;position:relative;overflow:hidden}
.retro-hero:after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(255,255,255,.015) 0 1px,transparent 1px 4px);pointer-events:none}
.retro-kicker{color:#00ffff;font:700 14px/1.2 "Courier New",monospace;letter-spacing:1px}.retro-title{color:#ffff00;font:900 42px/1 "Courier New",monospace;letter-spacing:0;margin-top:5px;text-shadow:none}.retro-title span{display:inline-block;margin-left:8px;padding:3px 9px;background:#00ffff;color:#000;border:0;transform:none;box-shadow:none}.retro-sub{margin-top:9px;color:#fff;font:700 14px/1.3 "Courier New",monospace}
h1,h2,h3{font-family:"Courier New",monospace!important;color:#ffff00!important;font-weight:900!important}p,li,label,.stMarkdown{color:#fff;font-family:"Courier New",monospace}
[data-testid="stMetric"]{background:#001b7a;border:0;border-radius:0!important;box-shadow:none;padding:10px 14px}[data-testid="stMetric"] *{color:#fff!important}[data-testid="stMetricLabel"] p{font-family:"Courier New",monospace!important;text-transform:uppercase;font-weight:700!important;font-size:11px!important}
div[data-testid="stDataFrame"]{border:1px solid #59665a;background:#171e18;padding:4px;box-shadow:4px 4px 0 rgba(0,0,0,.24)}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#000;padding:5px;border:0;overflow-x:auto}.stTabs [data-baseweb="tab"]{background:#001b7a;border:0;border-radius:0;color:#fff;font-family:"Courier New",monospace;font-weight:700;font-size:12px;padding:8px 12px}.stTabs [aria-selected="true"]{background:#ffff00!important;color:#000!important;border-color:#ffff00!important}
.stButton>button{border-radius:0!important;border:0!important;background:#00ffff!important;color:#000!important;font-weight:900!important;box-shadow:none!important;font-family:"Courier New",monospace!important}.stButton>button:hover{filter:brightness(1.15);box-shadow:none!important}
div[data-testid="stAlert"]{border-radius:1px!important;border:1px solid #5a665b!important;background:#001b55!important}div[data-baseweb="select"]>div,input,textarea{border-radius:1px!important;background:#001b55!important;border-color:#00ffff!important;color:#fff!important}hr{border-color:#475448!important}
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

.texttv-board{background:#000;border:4px solid #0044cc;padding:0;margin:10px 0 18px;font-family:"Courier New",monospace;color:#fff;overflow:hidden}
.texttv-pagebar{display:flex;justify-content:space-between;background:#001b7a;color:#ffff00;padding:7px 10px;font-weight:900;letter-spacing:.5px}
.texttv-row{display:grid;grid-template-columns:minmax(250px,1fr) 46px 46px 46px 86px;gap:2px;align-items:center;min-height:34px;border-bottom:1px solid #001b55;padding:0 6px}
.texttv-row:last-child{border-bottom:0}.texttv-head{color:#00ffff;font-weight:900;font-size:12px}.texttv-match{color:#fff;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.texttv-sign{display:inline-flex;align-items:center;justify-content:center;height:26px;color:#0044cc;font-weight:900}.texttv-sign.on{background:#ffff00;color:#000}.texttv-tag{color:#00ff66;text-align:right;font-size:11px;font-weight:900}
@media(max-width:700px){.texttv-row{grid-template-columns:minmax(145px,1fr) 34px 34px 34px 62px;padding:0 3px;font-size:11px}.texttv-tag{font-size:9px}.texttv-pagebar{font-size:12px}}
.texttv-footer{background:#001b7a;color:#00ffff;padding:6px 10px;font-size:10px;font-weight:900;letter-spacing:.3px}
.texttv-index{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:8px;background:#000}.texttv-index>div{display:grid;grid-template-columns:44px 1fr;background:#001b55;padding:8px}.texttv-index b{color:#ffff00}.texttv-index span{color:#fff;font-weight:900}
.texttv-summary{display:flex;gap:4px;flex-wrap:wrap;padding:4px 8px 10px}.texttv-summary span{background:#0000aa;color:#fff;padding:4px 7px;font-size:10px;font-weight:900}.texttv-summary span:last-child{background:#00ff66;color:#000}
.texttv-list{padding:3px 8px}.texttv-list-row{display:grid;grid-template-columns:36px minmax(180px,1fr) 110px minmax(180px,auto);gap:8px;align-items:center;border-bottom:1px solid #001b55;padding:7px 2px}.texttv-list-row b{color:#ffff00}.texttv-list-row span{color:#fff;font-weight:900}.texttv-list-row strong{color:#00ff66}.texttv-list-row em{color:#00ffff;font-style:normal;font-size:10px;text-align:right}.texttv-empty{padding:22px 10px;color:#00ffff;font-weight:900;text-align:center}.texttv-status-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:8px}.texttv-status-grid>div{background:#001b55;padding:10px}.texttv-status-grid b{display:block;color:#00ffff;font-size:10px}.texttv-status-grid span{display:block;color:#ffff00;font-size:17px;font-weight:900;margin-top:3px}.texttv-blockers{padding:0 10px 10px;color:#fff;font-size:11px}
.texttv-decision-top{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:8px}.texttv-decision-top>div{background:#001b55;padding:10px}.texttv-decision-top b{display:block;color:#00ffff;font-size:10px}.texttv-decision-top span{display:block;color:#ffff00;font-size:16px;font-weight:900;margin-top:3px}.texttv-decision-top .ok span{color:#00ff66}.texttv-decision-top .warn span{color:#ffff00}.texttv-decision-top .stop span{color:#ff4040}.texttv-actions{padding:2px 8px 8px}.texttv-action{display:grid;grid-template-columns:85px 150px 1fr;gap:8px;border-top:1px solid #001b55;padding:8px 2px;align-items:center}.texttv-action b{color:#ffff00}.texttv-action strong{color:#00ff66}.texttv-action span{color:#fff;font-size:10px}@media(max-width:700px){.texttv-decision-top{grid-template-columns:1fr}.texttv-action{grid-template-columns:72px 1fr}.texttv-action span{grid-column:2/3}}
@media(max-width:700px){.texttv-index{grid-template-columns:repeat(2,1fr)}.texttv-list-row{grid-template-columns:28px 1fr 82px;gap:5px;font-size:10px}.texttv-list-row em{grid-column:2/4;text-align:left;padding-bottom:3px}.texttv-status-grid{grid-template-columns:repeat(2,1fr)}}


.novice-system-board{border:3px solid #0044cc;background:#000;margin:8px 0 6px;font-family:"Courier New",monospace}
.novice-system-head,.novice-system-row{display:grid;grid-template-columns:minmax(230px,1fr) 48px 48px 48px 72px;gap:3px;align-items:center}
.novice-system-head{background:#001b7a;color:#00ffff;padding:7px 7px;font-size:11px;font-weight:900}.novice-system-head span:not(:first-child){text-align:center}
.novice-system-row{min-height:44px;padding:4px 7px;border-top:1px solid #001b55}.novice-match{min-width:0;color:#fff;font-weight:800}.novice-match b{color:#ffff00}.novice-match span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:inline}
.novice-sign{display:flex;align-items:center;justify-content:center;min-height:34px;border:2px solid #003399;color:#7788aa;font-size:18px;font-weight:900}.novice-sign.on{background:#ffff00;color:#000;border-color:#ffff00}
.novice-kind{text-align:center;font-size:10px;font-weight:900;padding:5px 2px}.novice-kind.spik{color:#00ff66}.novice-kind.halv{color:#00ffff}.novice-kind.hel{color:#ffff00}
.novice-system-legend{display:flex;gap:12px;flex-wrap:wrap;color:#fff;font:700 10px "Courier New",monospace;margin:4px 0 14px}.novice-system-legend b{color:#00ffff}
@media(max-width:700px){.novice-system-head,.novice-system-row{grid-template-columns:minmax(118px,1fr) 38px 38px 38px 52px;gap:2px}.novice-system-row{padding:4px 3px}.novice-system-head{padding:6px 3px}.novice-match{font-size:11px}.novice-sign{min-height:36px;font-size:16px}.novice-kind{font-size:8px}.novice-system-legend{gap:8px;font-size:9px}}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="retro-hero">
  <div class="retro-kicker">100  STRECKVERKET     TEXT-TV</div>
  <div class="retro-title">STRECK<span>VERKET</span> 100</div>
  <div class="retro-sub">13 MATCHER  •  ANALYS  •  VÄRDE  •  SYSTEM<br>Ett tydligt systemförslag för din budget. Analysen gör jobbet bakom kulisserna.</div>
</div>
""", unsafe_allow_html=True)
st.caption(f"v{APP_VERSION} · {RELEASE_NAME.upper()} · STRECKVERKET TEXT-TV")

ensure_coupon_state(st.session_state, load_demo_coupon())

# v3.88: quieter novice hierarchy. Keep the Text-TV identity but stop every element
# from competing for attention at the same visual weight.
st.markdown("""
<style>
.novice-landing{border:4px solid #0044cc;background:#000;padding:28px 30px;margin:18px 0 12px;max-width:980px}
.novice-landing-kicker{color:#00ffff;font:900 13px/1.2 "Courier New",monospace;letter-spacing:1px}
.novice-landing h2{color:#ffff00!important;font:900 30px/1.12 "Courier New",monospace!important;margin:10px 0 12px}
.novice-landing p{font:700 15px/1.55 "Courier New",monospace;color:#fff;margin:0}
.novice-summary{background:#001b7a;border-left:8px solid #ffff00;padding:16px 18px;margin:12px 0 14px;font-family:"Courier New",monospace}
.novice-summary .play{color:#ffff00;font-size:28px;font-weight:900;line-height:1.05}
.novice-summary .meta{color:#fff;font-size:13px;font-weight:900;margin-top:8px}
.novice-summary .status{color:#00ff66;font-size:12px;font-weight:900;margin-top:6px}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{line-height:1.35}
@media(max-width:700px){.novice-landing{padding:20px 16px}.novice-landing h2{font-size:24px}.novice-summary .play{font-size:23px}}
</style>
""", unsafe_allow_html=True)

def _configured_secrets():
    values = {}
    for _key in SOURCE_SECRET_KEYS.values():
        try:
            values[_key] = st.secrets.get(_key, "")
        except Exception:
            values[_key] = ""
    return values

def _render_csv_import(label, key):
    upload = st.file_uploader(label, type=["csv"], key=key)
    if upload is not None and st.button("Öppna CSV-kupongen", key=f"{key}_open"):
        try:
            coupon = load_csv_coupon(pd.read_csv(upload))
            set_coupon_state(st.session_state, coupon, data_mode="CSV-import", source_message="Kupong importerad från CSV.")
            st.session_state.pop("show_demo_preview", None)
        except (DataSourceError, ValueError, KeyError, TypeError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            st.error(f"CSV-kupongen kunde inte öppnas: {exc}")
        else:
            st.rerun()

from budget_controls import play_budget, render_budget_input

with st.sidebar:
    st.markdown("### Streckverket")
    expert_mode = st.toggle(
        "Expertläge", value=False,
        help="Visar datagranskning, evidens, modell-labb och övriga tekniska verktyg.",
    )
    specialist_mode = False

    if not expert_mode:
        # Normalanvändaren ska inte behöva läsa en permanent instruktion i tre steg.
        # Startskärmen leder användaren när ingen riktig kupong är öppen.
        if st.session_state.data_mode == "Demo":
            st.caption("Ingen riktig kupong är öppen ännu.")
            budget = play_budget()
            if st.session_state.get("show_demo_preview", False):
                budget = render_budget_input("Maxbudget (kr)", "sidebar_budget")
            _first_time_strategy = resolve_strategy(strategy_labels()[0])
            strategy = _first_time_strategy.engine_strategy
        else:
            st.caption("Spelinställning")
            budget = render_budget_input("Maxbudget (kr)", "sidebar_budget")
            _strategy_label = st.radio(
                "Spelsätt", strategy_labels(), index=0,
                help="Är du osäker, behåll Streckverkets rekommendation.",
            )
            _first_time_strategy = resolve_strategy(_strategy_label)
            strategy = _first_time_strategy.engine_strategy

            with st.expander("Byt eller öppna kupong", expanded=False):
                if st.button("Hämta aktuell Stryktipskupong", type="primary", key="beginner_fetch_coupon_sidebar"):
                    coupon, status = load_current_coupon()
                    if status.ok and coupon:
                        set_coupon_state(st.session_state, coupon, data_mode="Svenska Spel", source_message=status.message)
                        st.rerun()
                    else:
                        st.error("Kupongen kunde inte hämtas komplett just nu.")
                        st.caption(status.message)
                _render_csv_import("CSV-kupong", "beginner_csv")
                if st.button("Visa testkupong", key="beginner_demo"):
                    set_coupon_state(st.session_state, load_demo_coupon(), data_mode="Demo", source_message="Demodata används.")
                    st.session_state["show_demo_preview"] = True
                    st.rerun()
    else:
        st.caption("Expertläget visar hela analysapparaten.")
        for _step in expert_flow():
            st.caption(_step)
        specialist_mode = st.toggle(
            "Visa specialistverktyg", value=False,
            help="Visar modell-labb, databerikning, källverktyg och andra lågfrekventa expertverktyg.",
        )
        st.divider()
        st.subheader("Kupong")
        mode = st.radio(
            "Kupongkälla", ["Svenska Spel", "CSV-import", "Demo"],
            index=["Svenska Spel","CSV-import","Demo"].index(st.session_state.data_mode)
            if st.session_state.data_mode in ["Svenska Spel","CSV-import","Demo"] else 0,
        )
        if mode == "Svenska Spel":
            if st.button("Hämta aktuell kupong", type="primary"):
                coupon, status = load_current_coupon()
                if status.ok and coupon:
                    set_coupon_state(st.session_state, coupon, data_mode="Svenska Spel", source_message=status.message)
                    st.rerun()
                else:
                    st.error(status.message)
        elif mode == "CSV-import":
            _render_csv_import("Ladda upp kupong-CSV", "expert_csv")
        else:
            if st.button("Ladda demokupong", key="expert_demo"):
                set_coupon_state(st.session_state, load_demo_coupon(), data_mode="Demo", source_message="Demodata används.")
                st.rerun()

        with st.expander("Odds & datakällor", expanded=False):
            odds_key = st.text_input("The Odds API-nyckel", type="password")
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
                    st.rerun()

        st.divider()
        budget = render_budget_input("Maxbudget (kr)", "sidebar_budget")
        strategy = st.radio(
            "Systemstrategi", ["MAX 13", "VÄRDE"], horizontal=True,
            help="MAX 13 prioriterar modellens täckning. VÄRDE väger in streckfördelningen mer.",
        )

matches = st.session_state.coupon


# v3.88: demo is no longer presented as if it were a playable recommendation.
# The default novice state is a single clear next action.
if not expert_mode and st.session_state.data_mode == "Demo" and not st.session_state.get("show_demo_preview", False):
    st.markdown(
        """
        <div class="novice-landing">
          <div class="novice-landing-kicker">STRYKTIPSET · 13 MATCHER</div>
          <h2>INGEN AKTUELL KUPONG HÄMTAD</h2>
          <p>Hämta kupongen, välj budget och tryck på Analysera kupongen.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("HÄMTA AKTUELL STRYKTIPSKUPONG", type="primary", key="landing_fetch_coupon", use_container_width=True):
        with st.spinner("Hämtar aktuell Stryktipskupong…"):
            coupon, status = load_current_coupon()
        if status.ok and coupon:
            set_coupon_state(st.session_state, coupon, data_mode="Svenska Spel", source_message=status.message)
            st.session_state.pop("show_demo_preview", None)
            st.rerun()
        else:
            st.error("Kupongen kunde inte hämtas komplett just nu.")
            st.caption(status.message)
    with st.expander("Öppna en egen kupong från CSV", expanded=False):
        st.caption("Reservväg om den aktuella kupongen inte kan hämtas. Filen ska innehålla 13 matcher.")
        _render_csv_import("CSV-kupong", "landing_csv")
    with st.expander("Jag vill bara prova med testdata", expanded=False):
        st.caption("Testkupongen är bara till för att prova gränssnittet. Den är inte ett spelråd.")
        if st.button("Visa testkupongen", key="landing_demo_preview"):
            st.session_state["show_demo_preview"] = True
            st.rerun()
    st.stop()

# v3.65: automatic pre-kickoff market capture must not depend on opening an
# expert/decision tab. The novice one-screen flow therefore preserves the same
# prospective market-history behavior introduced in v3.62.
if not expert_mode:
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
    try:
        from automatic_market_capture import automatic_market_capture
        automatic_market_capture(
            st.session_state.get("facit_store"), matches, data_mode=st.session_state.data_mode
        )
    except Exception:
        # Passive history capture must never block the user's primary decision flow.
        pass

if st.session_state.pop("analysis_stale_notice", None):
    st.warning("Kupongen har ändrats sedan senaste analysen. Den gamla analysen har därför tagits bort.")
_market_missing = [m for m in matches if not getattr(m, "market_available", True)]
if _market_missing and st.session_state.data_mode != "Demo":
    st.error(
        f"MARKNADSODDS SAKNAS för {len(_market_missing)}/13 matcher. Streckverket kan visa en preliminär struktur, "
        "men kupongen ska inte betraktas som spelklar förrän riktiga odds har hämtats. Appen använder inte 3,00–3,00–3,00 som om det vore verkliga marknadsodds."
    )

if st.session_state.data_mode == "Demo":
    st.info("TESTLÄGE · Detta är en demokupong och inget spelråd. Hämta aktuell kupong när du vill spela på riktigt.")
elif expert_mode:
    st.info(st.session_state.source_message)
else:
    st.success("Kupongen är hämtad." if not _market_missing else "Kupongen är hämtad, men underlaget är inte komplett ännu.")

if expert_mode:
    with st.expander("Datatillförlitlighet", expanded=False):
        st.write(f"**Kupongkälla:** {st.session_state.data_mode}")
        st.write(f"**Status:** {st.session_state.source_message}")
        _dur = st.session_state.get("one_click_duration_seconds")
        if _dur is not None:
            st.caption(f"Senaste fulla analys tog {_dur:.1f} sekunder.")
        st.caption("Streckverket gissar inte lagmatchningar. Omatchade matcher lämnas orörda.")

with st.sidebar:
    locks = {}
    with st.expander("🔒 Egna låsningar", expanded=False):
        st.caption("Valfritt. Lås tecken bara när du själv vill styra systemet.")
        for m in matches:
            choice = st.multiselect(f"{m.number}. {m.home}–{m.away}", SIGNS, default=[], key=f"lock_{m.number}_{m.home}_{m.away}", placeholder="Ingen låsning")
            if choice:
                locks[m.number] = tuple(choice)

system = optimize_system(matches, budget, strategy, locks)

if expert_mode:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Systemkostnad", f"{system['rows']} kr")
    c2.metric("Modellens 13-rättstäckning", f"{100*system['coverage']:.2f} %")
    c3.metric("Slumpmässig täckning", f"{100*system['random_coverage']:.4f} %")
    uplift = system["coverage"]/system["random_coverage"] if system["random_coverage"] else 0
    c4.metric("Relativ mot slump", f"{uplift:.1f}×")
    st.caption("Täckningen är en modelluppskattning och inte en vinstgaranti.")
else:
    _spikes_n = sum(1 for _sel in system["selections"] if len(_sel) == 1)
    _guards_n = sum(1 for _sel in system["selections"] if len(_sel) == 2)
    _fulls_n = sum(1 for _sel in system["selections"] if len(_sel) == 3)
    _analysis_result = st.session_state.get("one_click_result")
    if _analysis_result is not None and getattr(_analysis_result, "cards", None):
        _coupon_readiness = coupon_readiness(
            _analysis_result.cards, system["selections"], demo=(st.session_state.data_mode == "Demo")
        )
    elif st.session_state.data_mode == "Demo":
        _coupon_readiness = CouponReadiness(0, "DEMO – INTE SPELKLAR", "Testdata.", ("hämta den riktiga kupongen först",), 0, 13)
    elif _market_missing:
        _coupon_readiness = CouponReadiness(20, "VÄNTA", "Marknadsankare saknas.", (f"aktuella marknadsodds saknas för {len(_market_missing)} av 13 matcher",), 13-len(_market_missing), 13)
    else:
        _coupon_readiness = CouponReadiness(75, "SPELKlar".upper(), "Marknadsunderlaget finns.", (), 13, 13)
    _guidance = readiness_guidance(
        _coupon_readiness, demo=(st.session_state.data_mode == "Demo"), market_missing_count=len(_market_missing)
    )
    _status_class = "status"
    st.markdown(
        f"""
        <div class="novice-summary">
          <div class="play">SPELA {system['rows']} KR</div>
          <div class="meta">{_spikes_n} SPIKAR · {_guards_n} HALVGARDERINGAR · {_fulls_n} HELGARDERINGAR</div>
          <div class="status">{_guidance.headline}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Maxbudget: {budget} kr · Systemkostnad: {system['rows']} kr. Radantalet ökar i fasta steg, så systemet kan kosta mindre än maxbudgeten.")
    getattr(st, _guidance.tone if _guidance.tone in {"success","warning","error","info"} else "info")(_guidance.message)

    # Timing and data-quality details remain secondary; analysis is a primary action.
    with st.expander("Analysstatus & uppdatering", expanded=False):
        st.markdown(f"**Gör detta nu:** {_guidance.next_step}")
        st.write(f"**Datakvalitet:** {_coupon_readiness.score}/100")
        st.caption("Datakvalitet beskriver hur komplett underlaget är — inte vinstchans.")
        if _coupon_readiness.blockers:
            for _blocker in _coupon_readiness.blockers:
                st.write(f"• {_blocker}")

        _timing = analysis_timing_advice(matches)
        st.markdown(f"**{_timing.headline}** — {_timing.message}")
        st.caption(f"Nästa kontroll: {_timing.next_step}")
        st.caption(_timing.basis)

    _refresh_running = bool(st.session_state.get("analysis_refresh_running", False))
    _refresh_label = "Hämta riktig kupong och analysera" if st.session_state.data_mode == "Demo" else ("Analysera kupongen" if _analysis_result is None else "Uppdatera analysen nu")
    if st.button(_refresh_label, type="primary", key="novice_refresh_analysis", use_container_width=True, disabled=_refresh_running):
        st.session_state["analysis_refresh_running"] = True
        _before_refresh_snapshot = make_analysis_snapshot(
            matches, system["selections"], _guidance.headline,
            getattr(_analysis_result, "cards", None) if _analysis_result is not None else None,
        )
        try:
            with st.spinner("Analyserar kupongen och hämtar tillgängligt underlag…"):
                _secret_values = _configured_secrets()
                _cfg = build_one_click_config(
                    odds_api_key=_secret_values.get(SOURCE_SECRET_KEYS["odds"], ""),
                    football_data_key=_secret_values.get(SOURCE_SECRET_KEYS["football_data"], ""),
                    api_football_key=_secret_values.get(SOURCE_SECRET_KEYS["api_football"], ""),
                    force_live_refresh=True,
                )
                _started_from_demo = (st.session_state.data_mode == "Demo")
                _base_coupon = list(st.session_state.coupon)
                _fresh_coupon, _fresh_status = load_current_coupon()
                _fresh_used = False
                _refresh_note = "Den öppna kupongen analyserades igen."
                if _fresh_status.ok and _fresh_coupon:
                    if _started_from_demo:
                        _base_coupon = list(_fresh_coupon)
                        _fresh_used = True
                        _refresh_note = "Testkupongen ersattes med aktuell Stryktipskupong före analysen."
                    else:
                        _choice = choose_refresh_coupon(_base_coupon, _fresh_coupon)
                        _base_coupon = _choice.coupon
                        _fresh_used = _choice.used_fresh_coupon
                        _refresh_note = _choice.message

                if _started_from_demo and not _fresh_used:
                    raise ValueError("Aktuell kupong kunde inte hämtas. Testkupongen är kvar i testläge; prova igen eller öppna en CSV-kupong.")

                _execution = execute_one_click(_cfg, coupon=_base_coupon, fetch_coupon=False)
                _result = _execution.result
                commit_analysis_state(
                    st.session_state, enriched_coupon=_result.enriched, result=_result,
                    coupon_fingerprint_value=_execution.coupon_fingerprint,
                    duration_seconds=_execution.duration_seconds,
                    data_mode="Multi-source",
                    source_message="Analysen uppdaterades med de datakällor som var tillgängliga och verifierbara.",
                )

                from market_timeline import coupon_market_key as _fact_coupon_key
                from signal_timeline import verified_facts_from_cards, deduplicate_signal_points
                _fact_capture_at = datetime.now(timezone.utc).isoformat()
                _new_fact_points = verified_facts_from_cards(
                    _result.cards, coupon_key=_fact_coupon_key(_result.enriched),
                    captured_at=_fact_capture_at, matches=_result.enriched,
                )
                _pending_facts = list(st.session_state.get("pending_verified_fact_points", []))
                st.session_state["pending_verified_fact_points"] = _pending_facts + deduplicate_signal_points(_pending_facts, _new_fact_points)

                if (not _started_from_demo) or _fresh_used:
                    _quality_snapshot = build_quality_snapshot(
                        coupon_fingerprint=_execution.coupon_fingerprint, matches=_result.enriched, cards=_result.cards,
                        stages=_result.stages, data_mode="Multi-source", duration_seconds=_execution.duration_seconds,
                        match_provenance=_result.match_provenance,
                    )
                    append_quality_snapshot("data/data_quality_history.json", _quality_snapshot)

                _after_system = optimize_system(_result.enriched, budget, strategy, locks)
                _after_readiness = coupon_readiness(
                    _result.cards, _after_system["selections"], demo=False
                )
                _after_guidance = readiness_guidance(
                    _after_readiness, demo=False,
                    market_missing_count=sum(1 for m in _result.enriched if not getattr(m, "market_available", True)),
                )
                _after_refresh_snapshot = make_analysis_snapshot(
                    _result.enriched, _after_system["selections"], _after_guidance.headline, _result.cards
                )
                st.session_state["analysis_change_report"] = compare_analysis_snapshots(
                    _before_refresh_snapshot, _after_refresh_snapshot
                )
                st.session_state["analysis_refresh_notice"] = f"Analysen är uppdaterad. {_refresh_note}"
        except Exception as exc:
            st.session_state["analysis_refresh_error"] = f"Analysen kunde inte uppdateras: {type(exc).__name__}: {exc}"
        finally:
            st.session_state["analysis_refresh_running"] = False
        st.rerun()

    _refresh_notice = st.session_state.pop("analysis_refresh_notice", None)
    if _refresh_notice:
        st.success(_refresh_notice)
    _refresh_error = st.session_state.pop("analysis_refresh_error", None)
    if _refresh_error:
        st.error(_refresh_error)

    _change_report = st.session_state.get("analysis_change_report")
    if _change_report is not None:
        st.markdown("### Vad ändrades sedan förra analysen?")
        if _change_report.system_changed:
            st.warning(f"**{_change_report.headline}** — {_change_report.summary}")
        else:
            st.success(f"**{_change_report.headline}** — {_change_report.summary}")
        if _change_report.system_changed and getattr(_change_report, "reasons", ()):
            st.markdown("**Varför ändrades systemet?**")
            for _reason in _change_report.reasons:
                st.write(f"• {_reason}")
        if _change_report.details:
            with st.expander("Se alla dataändringar", expanded=False):
                for _detail in _change_report.details:
                    st.write(f"• {_detail}")
        st.caption("Orsaksraderna visar vilka verifierbara förändringar som sammanföll med ett nytt systemval. De bevisar inte att en enskild faktor ensam orsakade ändringen.")


if not expert_mode:
    st.markdown("### Kryssa så här")
    st.caption("Gula rutor är tecknen som ingår i Streckverkets systemförslag.")
    st.markdown(
        render_novice_system_board(matches, system["selections"]),
        unsafe_allow_html=True,
    )

    _novice_rows = build_novice_rows(matches, system["selections"])
    _why_labels = [
        f"{row['number']}. {row['home']} – {row['away']} · {row['kind']} {row['instruction']}"
        for row in _novice_rows
    ]
    _why_choice = st.selectbox(
        "Varför dessa tecken?",
        options=range(len(_novice_rows)),
        format_func=lambda i: _why_labels[i],
        key="novice_match_explanation",
        help="Välj en match för en kort förklaring på vanlig svenska.",
    )
    _why_row = _novice_rows[int(_why_choice)]
    st.info(f"**Match {_why_row['number']} · {_why_row['kind']} {_why_row['instruction']}** — {_why_row['explanation']}")

    _highlights = build_decision_highlights(matches, system["selections"])
    if _highlights:
        st.markdown("### Kupongens nyckelbeslut")
        st.caption("De här matcherna är viktigast att förstå innan du lämnar in systemet.")
        for _item in _highlights:
            st.markdown(f"**{_item.role} · Match {_item.match_number} · {_item.selection}**")
            st.write(f"{_item.match_name} — {_item.explanation}")

    _spike_candidates = []
    _guard_candidates = []
    _trap_candidates = []
    for _m, _sel in zip(matches, system["selections"]):
        if len(_sel) == 1:
            _i = SIGNS.index(_sel[0])
            _spike_candidates.append((_m.model[_i], _m, _sel[0]))
        elif len(_sel) > 1:
            _guard_candidates.append((len(_sel), _m, "".join(_sel)))
        _fav = max(range(3), key=lambda i: _m.public[i])
        _trap_candidates.append((_m.public[_fav] - _m.model[_fav], _m))

    st.markdown("### Varför just detta?")
    _reasons = []
    if _spike_candidates:
        _, _m, _sign = max(_spike_candidates, key=lambda x: x[0])
        _reasons.append(f"**Match {_m.number}:** {_m.home}–{_m.away} är en av de tydligaste spikarna i systemet ({_sign}).")
    if _guard_candidates:
        _, _m, _signs = max(_guard_candidates, key=lambda x: (x[0], -x[1].number))
        _reasons.append(f"**Match {_m.number}:** {_m.home}–{_m.away} får extra skydd med {_signs}.")
    if _trap_candidates and max(_trap_candidates, key=lambda x: x[0])[0] > 0:
        _, _m = max(_trap_candidates, key=lambda x: x[0])
        _reasons.append(f"**Match {_m.number}:** folkets favorit ser starkare ut i strecken än i modellen, så systemet är försiktigt där.")
    for _reason in _reasons[:3]:
        st.write(_reason)
    st.caption("Det här är ett modellbaserat systemförslag, inte en garanti för vinst.")

    with st.expander("Fördjupad analys", expanded=False):
        st.write("Här finns modellprocent, streck, marknad, spikar, fällor och andra detaljer. Slå på Expertläge om du vill arbeta aktivt med dem.")
else:
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

if not expert_mode:
    # v3.65: the novice path already contains the complete answer above. Do not
    # repeat budget, strategy, system and explanation inside a second tabbed
    # decision surface. Expertläge retains the full navigation below.
    st.caption("Klart. Vill du granska modellen, datakällorna eller historiken kan du slå på Expertläge.")
else:
    st.markdown(hidden_tabs_css(expert_mode, specialist_mode), unsafe_allow_html=True)
    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15, tab16, tab17, tab18 = st.tabs(ALL_TABS)

    with tab0:
        if should_render_tab(ALL_TABS[0], expert_mode, specialist_mode):
            from ui_decision_page import render_decision_page
            render_decision_page(matches, locks, _configured_secrets)

    with tab1:
        if should_render_tab(ALL_TABS[1], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[2], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[3], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[4], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[5], expert_mode, specialist_mode):
            from ui_data_review import render_data_review
            render_data_review(matches, expert_mode)


    with tab6:
        if should_render_tab(ALL_TABS[6], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[7], expert_mode, specialist_mode):
            from ui_data_enrichment import render_data_enrichment
            render_data_enrichment(matches)

    with tab8:
        if should_render_tab(ALL_TABS[8], expert_mode, specialist_mode):
            from ui_sources import render_sources
            render_sources(matches, st.session_state.data_mode)

    with tab9:
        if should_render_tab(ALL_TABS[9], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[10], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[11], expert_mode, specialist_mode):
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
                    from market_timeline import coupon_market_key as _fact_coupon_key
                    from signal_timeline import verified_facts_from_cards, deduplicate_signal_points
                    _fact_capture_at = datetime.now(timezone.utc).isoformat()
                    _new_fact_points = verified_facts_from_cards(
                        result.cards, coupon_key=_fact_coupon_key(result.enriched), captured_at=_fact_capture_at, matches=result.enriched
                    )
                    _pending_facts = list(st.session_state.get("pending_verified_fact_points", []))
                    st.session_state["pending_verified_fact_points"] = _pending_facts + deduplicate_signal_points(_pending_facts, _new_fact_points)
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
        if should_render_tab(ALL_TABS[12], expert_mode, specialist_mode):
            from ui_information_edge import render_information_edge
            render_information_edge()


    with tab13:
        if should_render_tab(ALL_TABS[13], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[14], expert_mode, specialist_mode):
            from ui_budget_workshop import render_budget_workshop
            render_budget_workshop(matches, locks)

    with tab15:
        if should_render_tab(ALL_TABS[15], expert_mode, specialist_mode):
            from ui_facit import render_facit_learning
            render_facit_learning(matches, budget, strategy, system, locks)
    with tab16:
        if should_render_tab(ALL_TABS[16], expert_mode, specialist_mode):
            from ui_coupon_archive import render_coupon_archive
            render_coupon_archive()
    with tab17:
        if should_render_tab(ALL_TABS[17], expert_mode, specialist_mode):
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
        if should_render_tab(ALL_TABS[18], expert_mode, specialist_mode):
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
                st.markdown("#### Spelteori: var trängs motspelarna?")
                st.caption("Poolspel är strategiskt: utdelningen beror inte bara på vad som händer på planen utan också på hur andra spelar. Tabellen letar därför efter trängsel och relativt värde. Den påstår inte att ett motströmstecken är lönsamt.")
                gt_rows = strategic_coupon_rows(matches)
                st.dataframe(pd.DataFrame(gt_rows), use_container_width=True, hide_index=True)
                st.caption("Trängsel mäter hur koncentrerade folkets streck är. MOTSTRÖMS MED STÖD kräver både tydlig modellchans och att tecknet är mindre spelat; ren sällsynthet räcker inte.")
                st.markdown("#### Kupongrensare med sannolikhetsstöd")
                cleaners = top_coupon_cleaners(matches, 6)
                if cleaners:
                    for x in cleaners:
                        st.write(f"**Match {x['match']} · {x['sign']} · {x['home']}–{x['away']}** — modellen {x['model']:.0%}, folket {x['public']:.0%}. Tecknet är mindre populärt men har fortfarande tydligt sannolikhetsstöd.")
                else:
                    st.write("Inga tydliga kupongrensare hittades med nuvarande krav.")
            except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError) as exc:
                st.warning(f"Poolvärdet kunde inte beräknas på aktuellt underlag: {type(exc).__name__}: {exc}")
