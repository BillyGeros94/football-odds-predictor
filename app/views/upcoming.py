"""Home page: predictions for the upcoming matches, and why the model made them."""
import altair as alt
import streamlit as st

import data
from style import COLOURS, LEAGUES, league_filter, odds, percent

st.title("Upcoming matches")
st.caption("Win, draw and loss probabilities from an average of logistic regression and "
           "gradient boosting. Fair odds are 1 / probability, with no bookmaker margin.")

matches = data.upcoming()
live = data.live()

# ---- Headline numbers ----
cols = st.columns(4)
cols[0].metric("Upcoming predictions", len(matches))
if isinstance(live, dict):
    scores = live["scores"].set_index("model")["log_loss"]
    cols[1].metric("Live log loss", f"{scores['average']:.4f}", help="Lower is better")
    gap = scores["average"] - scores["market pre-match"]
    cols[2].metric("Gap to pre-match odds", f"{gap:+.4f}", delta=f"{-gap:+.4f}",
                   help="Positive means the market was more accurate")
    cols[3].metric("Matches scored", len(live["matches"]))
else:
    cols[1].metric("Live log loss", "—", help="Appears once predicted matches are played")
    cols[2].metric("Gap to pre-match odds", "—")
    cols[3].metric("Matches scored", 0)

if matches.empty:
    st.info("No upcoming predictions right now. New ones are made every Monday and Thursday morning.")
    st.stop()

# ---- Predictions table ----
leagues = league_filter("upcoming_league")
shown = matches[matches["league"].isin(leagues)].copy()
shown["league"] = shown["league"].map(LEAGUES)
for outcome in ["home", "draw", "away"]:
    shown[f"odds_{outcome}"] = 1 / shown[f"prob_{outcome}"]
    shown[f"prob_{outcome}"] = shown[f"prob_{outcome}"] * 100

st.dataframe(
    shown[["match_date", "league", "home", "away", "prob_home", "prob_draw", "prob_away",
           "odds_home", "odds_draw", "odds_away"]],
    hide_index=True,
    width="stretch",
    column_config={
        "match_date": st.column_config.DateColumn("Date", format="ddd D MMM"),
        "league": "League",
        "home": "Home",
        "away": "Away",
        "prob_home": percent("Home win"),
        "prob_draw": percent("Draw"),
        "prob_away": percent("Away win"),
        "odds_home": odds("Odds home"),
        "odds_draw": odds("Odds draw"),
        "odds_away": odds("Odds away"),
    },
)
made = matches["created_at"].max()
st.caption(f"Predictions made {made:%d %b %Y, %H:%M} UTC, before kick-off. "
           "Every run is also committed to the repository's predictions/ folder.")

# ---- Why this prediction ----
st.subheader("Why this prediction?")
labels = [f"{r.home} v {r.away} ({r.match_date:%a %d %b})" for r in shown.itertuples()]
choice = st.selectbox("Match", labels, label_visibility="collapsed")
match = shown.iloc[labels.index(choice)]

drivers = data.explain(match["home"], match["away"])
if drivers is None:
    st.warning("No current form found for one of these teams.")
    st.stop()

drivers["direction"] = drivers["push"].map(lambda v: match["home"] if v > 0 else match["away"])
chart = (
    alt.Chart(drivers)
    .mark_bar()
    .encode(
        x=alt.X("push:Q", title=f"← favours {match['away']}   ·   favours {match['home']} →"),
        y=alt.Y("input:N", sort=None, title=None),
        color=alt.Color("direction:N", legend=None,
                        scale=alt.Scale(range=[COLOURS["Model"], COLOURS["Market pre-match"]])),
        tooltip=[alt.Tooltip("input:N", title="Input"), alt.Tooltip("value:N", title="Value"),
                 alt.Tooltip("push:Q", title="Push", format="+.2f")],
    )
    .properties(height=240)
)
st.altair_chart(chart, width="stretch")

main = drivers.loc[drivers["push"].abs().idxmax()]
side = match["home"] if main["push"] > 0 else match["away"]
st.caption(f"The biggest factor is **{main['input'].lower()}**, which favours **{side}**. "
           "Bars show each input's push on the odds of a home win against an away win, from the "
           "logistic regression half of the model; the gradient boosting half is not shown.")
