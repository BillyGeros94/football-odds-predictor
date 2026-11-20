"""Shared look for every page: league names, chart colours and table column formats."""
import streamlit as st

LEAGUES = {"E0": "Premier League", "E1": "Championship"}

# One colour per series, used in every chart so the same thing always looks the same: the model in ink, the
# rest in a fixed order of accents. set_theme() fills it for the viewer's light or dark theme on every run.
THEMES = {
    "light": {"Model": "#0b0b0b", "Market pre-match": "#eb6834", "Market closing": "#1baf7a",
              "Premier League": "#2a78d6", "Championship": "#eb6834", "Rule": "#c3c2b7", "Muted": "#a3a29c"},
    "dark": {"Model": "#ededea", "Market pre-match": "#d95926", "Market closing": "#199e70",
             "Premier League": "#3987e5", "Championship": "#d95926", "Rule": "#383835", "Muted": "#6b6a65"},
}
COLOURS = dict(THEMES["light"])


def set_theme(mode):
    COLOURS.update(THEMES[mode])


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
