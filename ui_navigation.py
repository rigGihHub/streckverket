"""Navigation policy for Streckverket.

The normal user should see a very small task-oriented surface. Advanced analysis
is still available in Expertläge, but it must not compete with the core task.
"""

CORE_TABS = [
    "Vad ska jag spela?",
    "Mitt system",
    "Spikar",
    "Fällor & skrällar",
    "Varför?",
]

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


def visible_tab_count(expert_mode: bool) -> int:
    """How many tabs should be visible in the current UI mode."""
    return len(ALL_TABS) if expert_mode else len(CORE_TABS)


def hidden_tabs_css(expert_mode: bool) -> str:
    """Hide advanced Streamlit tabs in normal mode without deleting capabilities.

    Streamlit still creates the tab content, so switching to Expertläge is instant.
    The CSS is deliberately narrow and only targets the navigation buttons.
    """
    if expert_mode:
        return ""
    first_hidden = len(CORE_TABS) + 1
    return f"""
    <style>
    .stTabs [data-baseweb=\"tab-list\"] button:nth-child(n+{first_hidden}) {{display:none!important;}}
    </style>
    """


def beginner_flow() -> tuple[str, ...]:
    return (
        "1. Hämta kupongen",
        "2. Välj högsta budget",
        "3. Läs Streckverkets förslag",
        "4. Öppna Varför? om du vill förstå analysen",
    )
