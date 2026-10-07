"""Navigation policy for Streckverket.

The normal user should see a very small task-oriented surface. Expertläge keeps
advanced capabilities, but v3.36 separates the primary expert workflow from
low-frequency specialist tools so the expert surface does not become a wall of tabs.
"""

CORE_TABS = [
    "Vad ska jag spela?",
    "Mitt system",
    "Spikar",
    "Fällor & skrällar",
    "Varför?",
]

# v3.65: the novice path is intentionally a single-screen workflow. The
# additional decision tabs remain available in Expertläge, where their detail
# is useful rather than duplicative.
NOVICE_TABS = ("Vad ska jag spela?",)

EXPERT_TABS = [
    "Datagranskning",
    "Modell-labb",
    "Databerikning",
    "Källor",
    "Match Intelligence",
    "Sista kontrollen",
    "Analysera aktuell kupong",
    "Information Edge",
    "Kupongverkstad",
    "Budgetverkstad",
    "Facit & lärande",
    "Kupongarkiv",
    "Modellcoach",
    "Poolvärde",
]

ALL_TABS = CORE_TABS + EXPERT_TABS

# Primary expert tabs follow the core decision path: data quality -> evidence ->
# learning/history. The rest remains available behind Specialistverktyg.
PRIMARY_EXPERT_TABS = (
    "Datagranskning",
    "Information Edge",
    "Facit & lärande",
    "Kupongarkiv",
    "Modellcoach",
)

SPECIALIST_EXPERT_TABS = tuple(tab for tab in EXPERT_TABS if tab not in PRIMARY_EXPERT_TABS)


def visible_tab_names(expert_mode: bool, specialist_mode: bool = False) -> tuple[str, ...]:
    if not expert_mode:
        return NOVICE_TABS
    if specialist_mode:
        return tuple(ALL_TABS)
    return tuple(CORE_TABS + [tab for tab in EXPERT_TABS if tab in PRIMARY_EXPERT_TABS])


def visible_tab_count(expert_mode: bool, specialist_mode: bool = False) -> int:
    """How many tab buttons should be visible in the current UI mode."""
    return len(visible_tab_names(expert_mode, specialist_mode))


def should_render_tab(tab_name: str, expert_mode: bool, specialist_mode: bool = False) -> bool:
    """Return whether a tab's body should execute in the current UI mode.

    CSS hiding alone does not stop Streamlit from evaluating tab content. This
    guard is therefore the performance/safety boundary for hidden expert tools.
    """
    return tab_name in visible_tab_names(expert_mode, specialist_mode)


def hidden_tabs_css(expert_mode: bool, specialist_mode: bool = False) -> str:
    """Hide non-relevant Streamlit tab buttons without deleting capabilities.

    Streamlit still creates all tab content. v3.36 hides specialist tabs in the
    default expert surface and reveals them only when the user explicitly asks.
    """
    if expert_mode and specialist_mode:
        return ""
    if not expert_mode:
        hidden_indices = [idx + 1 for idx, tab in enumerate(ALL_TABS) if tab not in NOVICE_TABS]
        selectors = ",\n".join(
            f'.stTabs [data-baseweb="tab-list"] button:nth-child({idx})' for idx in hidden_indices
        )
        return f"""
        <style>
        {selectors} {{display:none!important;}}
        </style>
        """

    visible = set(visible_tab_names(True, False))
    hidden_indices = [idx + 1 for idx, tab in enumerate(ALL_TABS) if tab not in visible]
    selectors = ",\n".join(
        f'.stTabs [data-baseweb="tab-list"] button:nth-child({idx})' for idx in hidden_indices
    )
    return f"""
    <style>
    {selectors} {{display:none!important;}}
    </style>
    """


def expert_flow() -> tuple[str, ...]:
    return (
        "1. Datagranskning – går underlaget att lita på?",
        "2. Information Edge – finns något som är värt att granska?",
        "3. Facit & lärande – håller mönstret över tid?",
    )


def beginner_flow() -> tuple[str, ...]:
    return (
        "1. Hämta kupongen",
        "2. Välj din maxbudget",
        "3. Spela systemet – eller läs varför",
    )
