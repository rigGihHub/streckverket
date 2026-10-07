"""Keep every system view on the same budget across Streamlit reruns."""
import streamlit as st


def play_budget():
    if "play_budget" not in st.session_state:
        st.session_state["play_budget"] = int(st.session_state.get("decision_budget", 128))
    return int(st.session_state["play_budget"])


def _budget_changed(widget_key):
    st.session_state["play_budget"] = int(st.session_state[widget_key])


def render_budget_input(label, key):
    # The durable value is separate from widget keys, which Streamlit removes
    # when a control disappears (for example when switching expert mode).
    st.session_state[key] = play_budget()
    return int(st.number_input(
        label, min_value=1, max_value=100000, step=1, key=key,
        on_change=_budget_changed, args=(key,),
        help="Systemet räknas om när du trycker Enter eller lämnar fältet. Beloppet är en maxgräns; radantalet ökar i fasta steg.",
    ))
