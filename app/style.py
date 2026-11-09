"""Shared look for every page: league names, chart colours and table column formats."""
import streamlit as st

LEAGUES = {"E0": "Premier League", "E1": "Championship"}

# One colour per series, used in every chart so the same thing always looks the same
COLOURS = {
    "Model": "#2563eb",
    "Market pre-match": "#f59e0b",
    "Market closing": "#16a34a",
    "Premier League": "#7c3aed",
    "Championship": "#0891b2",
}


def league_filter(key):
    """League selector. Returns the league codes to show."""
    choice = st.segmented_control("League", ["All", *LEAGUES.values()], default="All",
                                  key=key, label_visibility="collapsed")
    if choice in (None, "All"):
        return list(LEAGUES)
    return [code for code, name in LEAGUES.items() if name == choice]


def percent(label, help=None):
    """A table column that shows a 0–100 value as a filled bar with a percentage."""
    return st.column_config.ProgressColumn(label, min_value=0, max_value=100,
                                           format="%.0f%%", help=help)


def odds(label):
    """A table column for decimal odds."""
    return st.column_config.NumberColumn(label, format="%.2f")
