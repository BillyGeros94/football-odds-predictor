"""Model performance: the one-time final test, calibration, tuning and some context."""
import altair as alt
import pandas as pd
import streamlit as st

import data
from style import COLOURS, LEAGUES

NAMES = {"market": "Bookmakers' closing odds", "logistic": "Logistic regression",
         "average": "Average of both (main model)", "boosting": "Gradient boosting",
         "baseline": "Baseline (historical rates)"}

st.title("Model performance")
st.caption("Tested walk-forward: each season is predicted using only the seasons before it. Every "
           "choice was made on 2019/20–2021/22; the final test was then run once on matches never "
           "used for any decision.")

metrics = data.final_metrics()
overall = pd.DataFrame(metrics["overall"]).set_index("model")
loss = overall["log_loss"]
gap_closed = (loss["baseline"] - loss["average"]) / (loss["baseline"] - loss["market"])

cols = st.columns(4)
cols[0].metric("Gap to the market closed", f"{gap_closed:.0%}",
               help="How far the model gets from the baseline towards the closing odds")
cols[1].metric("Log loss", f"{loss['average']:.4f}", help=f"Market: {loss['market']:.4f}")
cols[2].metric("Calibration error", f"{overall.loc['average', 'calibration_error']:.4f}",
               help=f"Market: {overall.loc['market', 'calibration_error']:.4f}")
cols[3].metric("Test matches", f"{metrics['matches']:,}")

# ---- Final test table ----
st.subheader("Final test, 2022/23 to 2026/27 so far")
table = overall.reset_index()
table["model"] = table["model"].map(NAMES)
table.loc[table["model"].str.startswith("Baseline"), "calibration_error"] = None
st.dataframe(
    table, hide_index=True, width="stretch",
    column_config={
        "model": "Model",
        "log_loss": st.column_config.NumberColumn("Log loss", format="%.4f"),
        "brier": st.column_config.NumberColumn("Brier score", format="%.4f"),
        "calibration_error": st.column_config.NumberColumn("Calibration error", format="%.4f"),
    },
)
st.caption("Lower is better for all three. Logistic regression alone did slightly better than the "
           "average on this test (1.0219 against 1.0229), but the average was chosen beforehand on "
           "the tuning seasons, and switching after seeing the test would defeat its purpose.")

# ---- By season ----
left, right = st.columns(2)
with left:
    st.subheader("Log loss by season")
    seasons = pd.DataFrame(metrics["log_loss_by_season"]).T.reset_index(names="season")
    seasons["season"] = seasons["season"].str[:2] + "/" + seasons["season"].str[2:]
    long = seasons.melt("season", ["average", "market"], var_name="source", value_name="log_loss")
    long["source"] = long["source"].map({"average": "Model", "market": "Market closing"})
    chart = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("season:N", title=None),
            xOffset="source:N",
            y=alt.Y("log_loss:Q", title="Log loss", scale=alt.Scale(domain=[0.94, 1.08])),
            color=alt.Color("source:N", title=None,
                            scale=alt.Scale(domain=["Model", "Market closing"],
                                            range=[COLOURS["Model"], COLOURS["Market closing"]])),
            tooltip=["season:N", "source:N", alt.Tooltip("log_loss:Q", format=".4f")],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, width="stretch")
    st.caption("2026/27 is only the matches played so far, so it is the noisiest bar.")

with right:
    st.subheader("Calibration")
    st.image(str(data.CALIBRATION_CHART), width="stretch")
    st.caption("Points on the diagonal mean that a 60% prediction happens about 60% of the time.")

# ---- Tuning ----
st.subheader("What improved the model")
steps = pd.DataFrame([
    ("Start", "Logistic regression on plain Elo", 1.0348),
    ("Elo", "Bigger wins move ratings more; ratings pulled back each summer", 1.0309),
    ("Features", "Added shots on target (recent goals made it worse)", 1.0293),
    ("Boosting", "Tuned to few, shallow trees learning slowly (from 1.0528)", 1.0292),
    ("Final", "Average of logistic regression and boosting", 1.0271),
], columns=["Step", "Change", "Log loss"])
st.dataframe(steps, hide_index=True, width="stretch",
             column_config={"Log loss": st.column_config.NumberColumn(format="%.4f")})
st.caption("Measured on the tuning seasons, 2019/20–2021/22.")

# ---- Home advantage ----
st.subheader("Home advantage by season")
home = data.home_win_rate()
home["league"] = home["league"].map(LEAGUES)
home["season"] = home["season"].str[:2] + "/" + home["season"].str[2:]
chart = (
    alt.Chart(home)
    .mark_line(point=True)
    .encode(
        x=alt.X("season:N", title=None),
        y=alt.Y("home_win_rate:Q", title="Home win rate", axis=alt.Axis(format="%"),
                scale=alt.Scale(zero=False)),
        color=alt.Color("league:N", title=None,
                        scale=alt.Scale(domain=list(LEAGUES.values()),
                                        range=[COLOURS["Premier League"], COLOURS["Championship"]])),
        tooltip=["season:N", "league:N", alt.Tooltip("home_win_rate:Q", format=".1%"), "matches:Q"],
    )
    .properties(height=300)
)
st.altair_chart(chart, width="stretch")
st.caption("The dip in 2020/21 is the season played without crowds.")

# ---- Limitations ----
with st.expander("Limitations"):
    st.markdown(
        "- The live comparison favours the market: a prediction can be made up to four days before "
        "kick-off, while closing odds include late team news. Pre-match odds are the fairer comparison.\n"
        "- Matches on the day of a run are not predicted.\n"
        "- No line-ups, injuries or xG: the model only knows results, shots on target and ratings.\n"
        "- Data from [football-data.co.uk](https://www.football-data.co.uk), not included in the "
        "repository. A personal, non-commercial project."
    )
