"""Season predictions: each team's chances, from simulating the rest of the season."""
import altair as alt
import streamlit as st

import data
from style import LEAGUES, percent
from src.simulate import N_SIMS

st.title("Season predictions")
st.caption(f"The remaining fixtures are played out {N_SIMS:,} times with the model's match "
           "probabilities, and each team's finishing positions are counted.")

try:
    latest = data.simulation_latest()
except Exception:   # the table does not exist until the first simulation run
    latest = None
if latest is None or latest.empty:
    st.info("No simulation yet. It runs with every Monday and Thursday update.")
    st.stop()

run_at = latest["run_at"].max()
tabs = st.tabs(list(LEAGUES.values()))

# Columns per league: the Premier League has a top 4, the Championship promotion and play-offs
COLUMNS = {
    "E0": {"p_title": percent("Title"), "p_top4": percent("Top 4"),
           "p_relegation": percent("Relegated")},
    "E1": {"p_title": percent("Champions"), "p_promotion": percent("Promoted (top 2)"),
           "p_playoffs": percent("Play-offs (3rd–6th)"), "p_relegation": percent("Relegated")},
}

for tab, (code, name) in zip(tabs, LEAGUES.items()):
    with tab:
        table = latest[latest["league"] == code].sort_values("expected_points", ascending=False)
        if table.empty:
            st.info(f"{name} not simulated in this run, usually because not every team has played yet.")
            continue
        table = table.copy()
        for column in COLUMNS[code]:
            table[column] = table[column] * 100
        st.dataframe(
            table[["team", "played", "points", "expected_points", *COLUMNS[code]]],
            hide_index=True, width="stretch", height=35 * len(table) + 38,
            column_config={
                "team": "Team", "played": "Played", "points": "Points",
                "expected_points": st.column_config.NumberColumn("Expected points", format="%.1f"),
                **COLUMNS[code],
            },
        )

st.caption(f"Simulated {run_at:%d %b %Y, %H:%M} UTC. Assumptions: ratings and form stay as they are "
           "now; ties on points are broken by current goal difference, then at random; points "
           "deductions are not included; the play-off final is not simulated.")

# ---- How chances changed ----
history = data.simulation_history()
if history["run_at"].nunique() < 2:
    st.caption("A chart of how each team's chances change will appear after the next simulation run.")
    st.stop()

st.subheader("How a team's chances changed")
team = st.selectbox("Team", sorted(latest["team"]))
league = latest.loc[latest["team"] == team, "league"].iloc[0]
outcomes = {"p_title": "Title", "p_relegation": "Relegated"}
outcomes.update({"p_top4": "Top 4"} if league == "E0" else
                {"p_promotion": "Promoted", "p_playoffs": "Play-offs"})
trend = history[history["team"] == team].melt("run_at", list(outcomes), var_name="outcome",
                                                value_name="chance")
trend["outcome"] = trend["outcome"].map(outcomes)
chart = (
    alt.Chart(trend)
    .mark_line(point=True)
    .encode(
        x=alt.X("run_at:T", title=None),
        y=alt.Y("chance:Q", title="Chance", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("outcome:N", title=None),
        tooltip=["run_at:T", "outcome:N", alt.Tooltip("chance:Q", format=".0%")],
    )
    .properties(height=300)
)
st.altair_chart(chart, width="stretch")
